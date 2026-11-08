"""Exercise the light and dark theme in Chromium and Firefox (plan 02.3.1-05, HUB-10).

The toggle, aria-pressed, the saved choice, the system default, no flash, no storage, the
target size and the keys, the lockup and the Theo tile, the figures, the contrast sweep, the
locked page, the theme event, reduced motion and a hostile stored value. Public fixture only.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hub_browser_support import file_url, require_browser, run_scenario
from mindrian_eureka.hub.deck import DECK
from test_hub_browser_core import CHECKS, built_hub, scenario
from test_hub_browser_gate import PASS, gated_hub, submit
from test_hub_browser_review import CONTRAST, public_hub
from test_hub_browser_review import evaluate as review_evaluate
from test_hub_browser_review import state as review_state

THEME = str(CHECKS / "theme-state.js")
WIDTHS = (320, 390, 768, 1280, 1600)
LIGHT_PAPER = "rgb(247, 245, 238)"
LIGHT_INK = "rgb(17, 17, 17)"
LIGHT_COBALT = "rgb(31, 63, 191)"
DARK_PAPER = "rgb(18, 18, 16)"
DARK_INK = "rgb(244, 242, 234)"
DARK_COBALT = "rgb(143, 162, 255)"
YELLOW = "rgb(242, 194, 0)"
NONE_RING = ("none", "rgba(0, 0, 0, 0) 0px 0px 0px 3px")
PAPER_LOCKUP = "mos-lockup-paper-v2.svg"
REVERSE_LOCKUP = "mos-lockup-reverse-v2.svg"
NS = "http://www.w3.org/2000/svg"
FIGURE_CLASSES = (
    "f-paper", "f-frame", "f-rule", "f-panel", "f-ink", "f-blue", "f-red", "f-yellow", "f-tick",
    "f-fan", "f-link", "f-track", "f-band", "f-chip", "f-chip-on", "f-mono", "f-title", "f-body",
    "f-num", "f-soft", "f-blue-t", "f-red-t", "f-band-t", "f-chip-t",
)
SAVE_DARK = 'try { localStorage.setItem("hub-theme", "dark"); } catch (error) { }\n'
SAVE_LIGHT = 'try { localStorage.setItem("hub-theme", "light"); } catch (error) { }\n'
SAVE_HOSTILE = (
    'try { localStorage.setItem("hub-theme", "dark\\" onload=\\"window.__pwned=1"); } '
    "catch (error) { }\n"
)
PAINT_PROBE = """
window.__paint = [];
const record = (label) => {
  const root = document.documentElement;
  window.__paint.push({label: label, theme: root.getAttribute('data-theme'),
    background: getComputedStyle(root).backgroundColor, state: document.readyState});
};
document.addEventListener('readystatechange', () => {
  if (document.readyState === 'interactive') record('interactive');
});
document.addEventListener('DOMContentLoaded', () => record('DOMContentLoaded'));
"""
NO_STORAGE = """
Storage.prototype.getItem = function () { throw new Error('storage is blocked'); };
Storage.prototype.setItem = function () { throw new Error('storage is blocked'); };
"""


def figure_markup() -> str:
    shapes = []
    for index, name in enumerate(FIGURE_CLASSES):
        if name.endswith("-t") or name in {"f-mono", "f-title", "f-body", "f-num"}:
            shapes.append(f'<text x="70" y="{100 + 30 * index}" class="{name}">word</text>')
        elif name in {"f-rule", "f-tick", "f-fan", "f-link"}:
            shapes.append(f'<line x1="0" y1="{index}" x2="100" y2="{index}" class="{name}"/>')
        else:
            shapes.append(f'<rect x="{index}" y="{index}" width="40" height="40" class="{name}"/>')
    return (
        f'<svg xmlns="{NS}" viewBox="0 0 1400 934" role="img" class="hub-figure">'
        "<title>Every figure class</title><desc>A test picture.</desc>" + "".join(shapes) + "</svg>"
    )


def theme(name: str, **args):
    return {"kind": "eval", "file": THEME, "as": name, "args": args}


def click():
    return {"kind": "click", "selector": "#hub-theme"}


def viewport(width: int, height: int = 900):
    return {"kind": "setViewport", "width": width, "height": height}


def init_script(folder: Path, name: str, body: str) -> str:
    path = folder / f"{name}.js"
    path.write_text(body, encoding="utf-8")
    return str(path)


def assert_dark(state: dict, label: str = "Dark") -> None:
    assert state["bodyBackground"] == DARK_PAPER and state["bodyColor"] == DARK_INK, state
    assert state["toggle"]["pressed"] == "true" and state["toggle"]["label"] == label


def assert_light(state: dict, label: str = "Light") -> None:
    assert state["bodyBackground"] == LIGHT_PAPER and state["bodyColor"] == LIGHT_INK, state
    assert state["toggle"]["pressed"] == "false" and state["toggle"]["label"] == label


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_toggle_switches_and_sets_aria_pressed(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    result = scenario(public_hub(tmp_path), browser, steps=[
        viewport(1280), theme("start"), click(), theme("dark", settle=50), click(),
        theme("back", settle=50)])
    start = result["start"]
    assert_light(start)
    assert start["theme"] is None and start["toggle"]["name"] == DECK["G03.theme.name"]
    assert start["toggle"]["type"] == "button" and start["toggle"]["display"] != "none"
    assert start["colorScheme"] == "light"
    assert start["toggle"]["label"] == DECK["G03.theme.light"]
    dark = result["dark"]
    assert_dark(dark)
    assert dark["theme"] == "dark" and dark["colorScheme"] == "dark"
    assert dark["toggle"]["name"] == "Dark mode"
    assert dark["toggle"]["label"] == DECK["G03.theme.dark"]
    assert dark["link"] == DARK_COBALT
    back = result["back"]
    assert_light(back)
    assert back["theme"] == "light" and back["toggle"]["name"] == "Dark mode"
    assert back["link"] == LIGHT_COBALT


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_choice_persists_after_reload(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    result = scenario(public_hub(tmp_path), browser, steps=[
        viewport(1280), theme("start"), click(), theme("clicked", settle=50),
        {"kind": "reload"}, theme("after", settle=50)])
    assert_light(result["start"])
    assert_dark(result["clicked"])
    after = result["after"]
    if browser == "firefox" and after["saved"] != "dark":
        # Firefox may give a file page no storage. The rule: no error, the toggle still works.
        print(f"firefox storage on file URL: saved={after['saved']!r}; persistence not available")
        assert after["saved"] in (None, "unavailable")
        return
    assert after["saved"] == "dark" and after["theme"] == "dark"
    assert_dark(after)


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_system_preference_is_respected(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = public_hub(tmp_path)
    dark = scenario(out, browser, colorScheme="dark", steps=[viewport(1280), theme("state")])
    assert_dark(dark["state"])
    assert dark["state"]["theme"] is None and dark["state"]["colorScheme"] == "dark"
    assert dark["state"]["visibleLockup"].endswith(REVERSE_LOCKUP)
    light = scenario(out, browser, colorScheme="light", steps=[viewport(1280), theme("state")])
    assert_light(light["state"])
    assert light["state"]["theme"] is None
    saved_light = scenario(out, browser, colorScheme="dark",
                           initScripts=[init_script(tmp_path, "save-light", SAVE_LIGHT)],
                           steps=[viewport(1280), theme("state")])
    assert_light(saved_light["state"])
    assert saved_light["state"]["theme"] == "light"
    assert saved_light["state"]["colorScheme"] == "light"


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_no_flash(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = public_hub(tmp_path)
    probe = init_script(tmp_path, "paint", PAINT_PROBE)
    saved = scenario(out, browser, initScripts=[init_script(tmp_path, "save-dark", SAVE_DARK),
                                                probe], steps=[theme("state")])["state"]
    if saved["saved"] == "dark":
        labels = [item["label"] for item in saved["paint"]]
        assert "interactive" in labels and "DOMContentLoaded" in labels, labels
        for item in saved["paint"]:
            assert item["theme"] == "dark" and item["background"] == DARK_PAPER, item
        assert_dark(saved)
    else:
        print(f"{browser}: storage unavailable on the file URL; saved={saved['saved']!r}")
        assert browser == "firefox"
    system = scenario(out, browser, colorScheme="dark", initScripts=[probe],
                      steps=[theme("state")])["state"]
    labels = [item["label"] for item in system["paint"]]
    assert "interactive" in labels and "DOMContentLoaded" in labels, labels
    for item in system["paint"]:
        assert item["background"] == DARK_PAPER and item["theme"] is None, item
    assert_dark(system)


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_works_without_storage(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    result = scenario(public_hub(tmp_path), browser,
                      initScripts=[init_script(tmp_path, "no-storage", NO_STORAGE)],
                      steps=[viewport(1280), theme("start"), click(), theme("dark", settle=50),
                             click(), theme("back", settle=50)])
    assert result["start"]["saved"] == "unavailable"
    assert_light(result["start"])
    assert_dark(result["dark"])
    assert result["dark"]["theme"] == "dark"
    assert_light(result["back"])


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_toggle_target_and_keyboard(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    steps = []
    for width in WIDTHS:
        steps.extend([viewport(width), theme(str(width))])
    steps.extend([
        {"kind": "press", "selector": "#hub-header-action", "key": "Tab"}, theme("tabbed"),
        {"kind": "press", "selector": "#hub-theme", "key": "Enter"}, theme("enter", settle=50),
        {"kind": "press", "selector": "#hub-theme", "key": "Space"}, theme("space", settle=50),
    ])
    result = scenario(public_hub(tmp_path), browser, steps=steps)
    for width in WIDTHS:
        box = result[str(width)]["toggle"]["box"]
        assert box["width"] >= 44 and box["height"] >= 44, (width, box)
        assert result[str(width)]["scrollWidth"] <= result[str(width)]["innerWidth"], width
        assert result[str(width)]["toggle"]["fontSize"] == "13px"
    tabbed = result["tabbed"]
    assert tabbed["active"]["id"] == "hub-theme"
    assert tabbed["active"]["outlineWidth"] == "3px" and tabbed["active"]["outlineStyle"] == "solid"
    assert_dark(result["enter"])
    assert_light(result["space"])


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_lockup_and_face_follow_the_theme(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    result = scenario(built_hub(tmp_path), browser, steps=[
        viewport(1280), theme("light"), click(), theme("dark", settle=50)])
    light, dark = result["light"], result["dark"]
    assert [item["src"] for item in light["lockups"]] == [
        f"assets/brand/{PAPER_LOCKUP}", f"assets/brand/{REVERSE_LOCKUP}"]
    assert light["visibleLockup"].endswith(PAPER_LOCKUP)
    assert light["lockups"][1]["rects"] == 0 and light["lockups"][1]["display"] == "none"
    assert light["lockups"][0]["width"] == pytest.approx(156, abs=0.5)
    assert dark["visibleLockup"].endswith(REVERSE_LOCKUP)
    assert dark["lockups"][0]["rects"] == 0 and dark["lockups"][1]["rects"] == 1
    assert dark["lockups"][1]["width"] == pytest.approx(156, abs=0.5)
    for state in (light, dark):
        assert all(item["filter"] == "none" for item in state["lockups"]), state["lockups"]
        assert state["face"]["filter"] == "none" and state["face"]["rects"] == 1
        assert state["panelImage"]["filter"] == "none"
    assert light["face"]["boxShadow"] in NONE_RING, light["face"]
    assert dark["face"]["boxShadow"] == f"{DARK_INK} 0px 0px 0px 3px", dark["face"]
    assert dark["panelImage"]["boxShadow"] == f"{DARK_INK} 0px 0px 0px 3px", dark["panelImage"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_figures_follow_the_theme(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    markup = figure_markup()
    result = scenario(built_hub(tmp_path), browser, steps=[
        viewport(1280), theme("light", figure=markup), click(),
        theme("dark", figure=markup, settle=50)])
    light, dark = result["light"]["figure"], result["dark"]["figure"]
    assert light["inserted"] and dark["inserted"]
    assert set(light["classes"]) == set(FIGURE_CLASSES)
    assert light["paper"] == LIGHT_PAPER and dark["paper"] == DARK_PAPER
    assert light["blue"] == LIGHT_COBALT and dark["blue"] == DARK_COBALT
    assert light["yellow"] == YELLOW and dark["yellow"] == YELLOW
    assert light["ink"] == LIGHT_INK and dark["ink"] == DARK_INK
    assert light["frame"] == LIGHT_INK and dark["frame"] == DARK_INK
    # The band of a figure maps to the ink token, so it inverts with the page (plan 04 note).
    assert light["band"] == LIGHT_INK and light["bandText"] == LIGHT_PAPER
    assert dark["band"] == DARK_INK and dark["bandText"] == DARK_PAPER


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_contrast_sweep_in_both_themes(tmp_path: Path, scheme: str) -> None:
    require_browser()
    out = public_hub(tmp_path)
    for width in (390, 1280):
        steps = [theme("theme")]
        for view in ("bank", "graph", "catalogue"):
            steps += [review_state(view, view=view, clear=True),
                      review_evaluate(CONTRAST, view + "-contrast")]
        steps += [review_state("panel", view="bank", panel="pair"),
                  review_evaluate(CONTRAST, "panel-contrast")]
        result = scenario(out, colorScheme=scheme, viewport={"width": width, "height": 900},
                          steps=steps)
        expected = DARK_PAPER if scheme == "dark" else LIGHT_PAPER
        assert result["theme"]["bodyBackground"] == expected, (scheme, width)
        for name, measured in result.items():
            if not name.endswith("-contrast"):
                continue
            assert measured["checked"] > 0, (scheme, width, name)
            assert measured["failures"] == [], (scheme, width, name, measured["failures"])
            assert measured["yellow"] == [], (scheme, width, name, measured["yellow"])


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_locked_page_has_a_working_toggle(tmp_path: Path, browser: str) -> None:
    pytest.importorskip("cryptography")
    require_browser(browser)
    result = scenario(gated_hub(tmp_path), browser, steps=[
        viewport(1280), theme("locked"), click(), theme("dark", settle=50), *submit(PASS),
        theme("open", wait="unlocked", settle=100)])
    locked = result["locked"]
    assert locked["toggle"]["box"]["rects"] == 1 and not locked["toggle"]["hidden"]
    assert not locked["started"]
    assert_light(locked)
    assert_dark(result["dark"])
    opened = result["open"]
    assert opened["started"]
    assert_dark(opened)
    assert opened["theme"] == "dark" and opened["visibleLockup"].endswith(REVERSE_LOCKUP)
    assert opened["band"]["rects"] > 0
    assert opened["band"]["background"] == DARK_INK and opened["band"]["color"] == DARK_PAPER


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_theme_event(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    result = scenario(public_hub(tmp_path), browser, steps=[
        theme("listen", listen=True), click(), theme("one", settle=50), click(),
        theme("two", settle=50)])
    assert result["listen"]["events"] == []
    assert result["one"]["events"] == ["dark"]
    assert result["two"]["events"] == ["dark", "light"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_no_network_and_reduced_motion(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = public_hub(tmp_path)
    raw = run_scenario({"browser": browser, "url": file_url(out / "hub.html"),
                        "reducedMotion": True,
                        "steps": [viewport(1280), theme("start"), click(), theme("dark")]})
    assert raw["ok"], raw["stepErrors"]
    assert raw["blockedRequests"] == [] and raw["pageErrors"] == [] and raw["cspViolations"] == []
    assert not [message for message in raw["console"] if message["type"] == "error"]
    start, dark = raw["results"]["start"], raw["results"]["dark"]
    assert start["bodyTransition"] == "0s" and start["toggle"]["transition"] == "0s"
    assert_dark(dark)


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_hostile_stored_value_is_ignored(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    result = scenario(public_hub(tmp_path), browser, colorScheme="light",
                      initScripts=[init_script(tmp_path, "hostile", SAVE_HOSTILE)],
                      steps=[viewport(1280), theme("start"), click(), theme("dark", settle=50)])
    start = result["start"]
    assert start["theme"] is None
    assert_light(start)
    if start["saved"] not in (None, "unavailable"):
        assert start["saved"].startswith('dark" onload=')
    assert_dark(result["dark"])
    assert result["dark"]["theme"] == "dark"
    if result["dark"]["saved"] not in (None, "unavailable"):
        assert result["dark"]["saved"] == "dark"
