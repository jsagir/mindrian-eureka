"""Exercise the shell of the new look in Chromium and Firefox (plan 02.3.1-03, D-01).

The sticky header, the title band, the counts strip, the body type, links, the primary button,
the locked shell, the overflow floor and the safe figure helper. Public fixture data only.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from hub_browser_support import file_url, require_browser, run_scenario
from mindrian_eureka.hub.deck import DECK
from test_hub_browser_core import CHECKS, METRICS, built_hub, scenario
from test_hub_browser_gate import PASS, gated_hub, submit
from test_hub_browser_review import public_hub

ROOT = Path(__file__).resolve().parents[1]
SHELL = str(CHECKS / "shell-state.js")
FIGURE = str(CHECKS / "figure-helper.js")
CORE_JS = ROOT / "src/mindrian_eureka/hub/assets/authored/hub-core.js"
WIDTHS = (320, 390, 768, 1280, 1600)
INK = "rgb(17, 17, 17)"
PAPER = "rgb(247, 245, 238)"
LINE = "rgb(199, 198, 191)"
COBALT = "rgb(31, 63, 191)"
RED = "rgb(214, 40, 31)"
SOFT = "rgb(75, 73, 67)"
WHITE = "rgb(255, 255, 255)"

FIGURE_TAGS = ("svg", "title", "desc", "rect", "line", "circle", "text")
FIGURE_ATTRS = (
    "xmlns", "viewBox", "role", "class", "x", "y", "width", "height", "x1", "y1", "x2", "y2",
    "cx", "cy", "r", "fill", "stroke", "stroke-width", "stroke-dasharray", "opacity",
    "aria-hidden",
)
NS = "http://www.w3.org/2000/svg"
GOOD_FIGURE = (
    f'<svg xmlns="{NS}" viewBox="0 0 1400 934" role="img" class="hub-figure" width="1400" '
    'height="934"><title>A pair and its two records</title><desc>Two squares, one dashed line '
    'and one word.</desc><rect x="3" y="3" width="1394" height="928" fill="#F7F5EE" '
    'stroke="#111111" stroke-width="6" class="f-frame"/><line x1="226" y1="185" x2="394" '
    'y2="185" stroke="#111111" stroke-width="8" stroke-dasharray="28 32" opacity="0.55" '
    'class="f-link"/><circle cx="700" cy="467" r="40" fill="#1F3FBF" aria-hidden="true" '
    'class="f-blue"/><text x="70" y="900" fill="#111111" class="f-mono">word</text></svg>'
)
BAD_FIGURES = [
    f'<svg xmlns="{NS}"><script>window.__pwned=1</script></svg>',
    f'<svg xmlns="{NS}" onload="window.__pwned=1"><rect x="0" y="0" width="1" height="1"/></svg>',
    f'<svg xmlns="{NS}"><image href="https://example.test/x.png" width="1" height="1"/></svg>',
    f'<svg xmlns="{NS}"><foreignObject width="1" height="1"><p>x</p></foreignObject></svg>',
    f'<svg xmlns="{NS}"><rect x="0" y="0" width="1" height="1" style="fill:url(x)"/></svg>',
    f'<svg xmlns="{NS}"><a><text x="0" y="0">x</text></a></svg>',
    f'<svg xmlns="{NS}"><rect id="hub-title" x="0" y="0" width="1" height="1"/></svg>',
    f'<!DOCTYPE svg><svg xmlns="{NS}"><rect x="0" y="0" width="1" height="1"/></svg>',
    f'<svg xmlns="{NS}"><rect x="0" y="0" width="1" height="1"></svg>',
    "",
    f'<svg xmlns="{NS}"><text x="0" y="0" fill="url(#x)">x</text></svg>',
    f'<svg xmlns="{NS}"><rect x="0" y="0" width="1" height="1"><!-- note --></rect></svg>',
    '<p>not svg</p>',
]
OTHER_VALUES = [None, 12, {"svg": True}, [GOOD_FIGURE], True]


def shell(name: str, **args):
    return {"kind": "eval", "file": SHELL, "as": name, "args": args}


def viewport(width: int, height: int = 900):
    return {"kind": "setViewport", "width": width, "height": height}


def by_width(out: Path, browser: str = "chromium", widths=WIDTHS, **args):
    steps = []
    for width in widths:
        steps.extend([viewport(width), shell(str(width), **args)])
    return scenario(out, browser, steps=steps)


def family(value: str) -> str:
    return value.split(",")[0].strip("'\" ")


def px(value: str) -> float:
    return float(value.removesuffix("px"))


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_header_is_sticky_and_measured(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = public_hub(tmp_path)
    result = scenario(out, browser, steps=[viewport(1280), shell("top", scroll=0),
                                           shell("scrolled", scroll=600)])
    top = result["top"]
    header = top["header"]
    assert header["position"] == "sticky" and header["top"] == "0px" and header["zIndex"] == "20"
    assert header["backgroundColor"] == PAPER and header["backdropFilter"] == "none"
    assert header["borderBottomWidth"] == "1px" and header["borderBottomColor"] == LINE
    assert top["variable"] == f"{header['offsetHeight']}px"
    assert px(top["scrollPaddingTop"]) == pytest.approx(header["offsetHeight"] + 12, abs=0.5)
    scrolled = result["scrolled"]
    assert scrolled["scrollY"] > 0
    assert abs(scrolled["header"]["box"]["top"]) < 1


def test_header_layout_by_width(tmp_path: Path) -> None:
    require_browser()
    result = by_width(public_hub(tmp_path))
    for width in (1280, 1600):
        measured = result[str(width)]
        tops = [measured["lockup"]["top"], measured["context"]["top"], measured["links"]["top"]]
        assert max(tops) - min(tops) < 30, (width, tops)
        assert measured["header"]["offsetHeight"] <= 80, width
        assert measured["header"]["offsetHeight"] >= 76, width
    for width in (390, 768):
        measured = result[str(width)]
        assert measured["links"]["top"] >= measured["lockup"]["bottom"] - 1, width
    for width in WIDTHS:
        measured = result[str(width)]
        assert measured["scrollWidth"] <= measured["innerWidth"], width
        expected = 116 if width < 768 else 156
        assert measured["lockup"]["width"] == pytest.approx(expected, abs=0.5), width


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_nav_and_action(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = public_hub(tmp_path)
    steps = [viewport(1280), shell("start"),
             {"kind": "click", "selector": '#hub-nav a[href="#graph"]'}, shell("graph", settle=100),
             {"kind": "click", "selector": "#hub-header-action"}, shell("action", settle=200)]
    result = scenario(out, browser, steps=steps)
    start = result["start"]
    assert len(start["navLinks"]) == 3
    for link in [*start["navLinks"], start["action"]]:
        assert link["width"] >= 44 and link["height"] >= 44, link
    active = [link for link in start["navLinks"] if link["current"] == "page"]
    assert [link["href"] for link in active] == ["#bank"]
    assert active[0]["fontWeight"] == "700" and active[0]["borderBottomWidth"] == "2px"
    assert active[0]["borderBottomColor"] == INK
    others = [link for link in start["navLinks"] if link["current"] != "page"]
    for link in others:
        assert link["fontWeight"] == "600" and link["textDecorationLine"] == "none", link
    assert all(link["fontSize"] == "13px" and link["color"] == INK for link in start["navLinks"])
    assert start["action"]["href"] == "#hub-data-check" and start["action"]["text"] == DECK["D01"]
    assert start["action"]["borderWidth"] == "1px" and start["action"]["borderColor"] == INK
    graph = result["graph"]
    assert [link["href"] for link in graph["navLinks"] if link["current"] == "page"] == ["#graph"]
    action = result["action"]
    assert action["hash"] == "#hub-data-check" and action["notice"] == ""
    assert action["scrollY"] > 0
    assert action["dataCheck"]["box"]["top"] >= action["header"]["offsetHeight"] - 1


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_title_band_look(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    result = by_width(public_hub(tmp_path), browser)
    for width in WIDTHS:
        measured = result[str(width)]
        eyebrow = measured["eyebrow"]
        assert eyebrow["color"] == COBALT and eyebrow["fontSize"] == "13px", width
        assert family(eyebrow["fontFamily"]) == "JetBrains Mono", width
        dot = measured["dot"]
        assert dot["width"] == pytest.approx(8) and dot["height"] == pytest.approx(8), width
        assert dot["backgroundColor"] == RED and dot["borderRadius"] == "0px", width
        heading = measured["heading"]
        assert family(heading["fontFamily"]) == "Figtree" and heading["fontWeight"] == "700"
        size = 52 if width >= 1280 else 34 if width < 768 else px(heading["fontSize"])
        assert px(heading["fontSize"]) == pytest.approx(size, abs=0.01), width
        assert px(heading["letterSpacing"]) == pytest.approx(-0.04 * size, abs=0.05), width
        row = measured["titleRow"]
        assert row == {"borderBottomWidth": "1px", "borderBottomStyle": "solid",
                       "borderBottomColor": INK}, width
        assert measured["face"]["width"] == pytest.approx(64 if width >= 768 else 48), width


def test_counts_strip(tmp_path: Path) -> None:
    require_browser()
    result = by_width(public_hub(tmp_path))
    for width in WIDTHS:
        counts = result[str(width)]["counts"]
        assert counts["columns"] == (4 if width >= 768 else 2), width
        assert counts["borderTopWidth"] == "1px" and counts["borderTopColor"] == INK, width
        assert counts["borderBottomWidth"] == "1px" and counts["borderBottomColor"] == INK, width
        numeral = counts["numeral"]
        assert family(numeral["fontFamily"]) == "Figtree" and numeral["fontWeight"] == "700"
        assert numeral["fontSize"] == ("42px" if width >= 768 else "32px"), width
        caption = counts["caption"]
        assert caption["fontSize"] == "13px" and caption["color"] == SOFT, width


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_body_and_links(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    result = by_width(built_hub(tmp_path), browser, go="catalogue")
    for width in WIDTHS:
        measured = result[str(width)]
        body = measured["body"]
        size = 17 if width >= 768 else 16
        assert px(body["fontSize"]) == size, width
        assert px(body["lineHeight"]) == pytest.approx(1.58 * size, abs=0.01), width
        link = measured["link"]
        assert link is not None, width
        assert link["color"] == COBALT and link["textDecorationLine"] == "underline", width
        assert link["textDecorationThickness"] == "1px", width


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_primary_button_hover(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path)
    steps = [viewport(1280), shell("rest"), {"kind": "hover", "selector": ".hub-bank-read"},
             shell("hover", settle=400)]
    result = scenario(out, browser, steps=steps)
    rest = result["rest"]["button"]
    assert rest["backgroundColor"] == INK and rest["color"] == PAPER
    hover = result["hover"]["button"]
    assert hover["backgroundColor"] == COBALT and hover["color"] == WHITE
    assert hover["transform"] == "none"
    reduced = run_scenario({"browser": browser, "url": file_url(out / "hub.html"),
                            "steps": [viewport(1280), shell("state")], "reducedMotion": True})
    assert reduced["ok"], reduced["stepErrors"]
    assert reduced["results"]["state"]["button"]["transitionDuration"] == "0s"


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_locked_page_shell_in_the_browser(tmp_path: Path, browser: str) -> None:
    pytest.importorskip("cryptography")
    require_browser(browser)
    out = gated_hub(tmp_path)
    result = scenario(out, browser, steps=[viewport(1280), shell("locked"), *submit(PASS),
                                           shell("open", wait="unlocked", settle=100)])
    locked = result["locked"]
    assert locked["header"]["position"] == "sticky"
    assert locked["variable"] == f"{locked['header']['offsetHeight']}px"
    assert locked["nav"]["rects"] == 0 and locked["action"]["rects"] == 0
    assert locked["band"]["rects"] == 0
    assert locked["heading"]["text"] == DECK["L01"]
    assert locked["eyebrow"]["color"] == COBALT and locked["dot"]["backgroundColor"] == RED
    opened = result["open"]
    assert opened["started"]
    assert opened["nav"]["rects"] > 0 and opened["action"]["rects"] > 0
    assert opened["band"]["rects"] > 0
    assert opened["heading"]["text"] == DECK["B01"]


def test_no_horizontal_overflow_and_metrics(tmp_path: Path) -> None:
    require_browser()
    steps = []
    for width in WIDTHS:
        steps.extend([viewport(width), {"kind": "eval", "file": METRICS, "as": str(width)}])
    result = scenario(public_hub(tmp_path), steps=steps)
    for width, measured in result.items():
        assert measured["small"] == [], (width, measured)
        assert measured["minimum"] >= 13
        assert measured["targets"] == [], (width, measured)
        assert measured["scrollWidth"] <= measured["innerWidth"]


def test_panel_open_keeps_the_header_links_in_one_row(tmp_path: Path) -> None:
    require_browser()
    result = scenario(built_hub(tmp_path), steps=[viewport(1280), shell("open", panel="pair",
                                                                           settle=200)])
    measured = result["open"]
    assert measured["panelOpen"]
    tops = [child["top"] for child in measured["linkChildren"]]
    assert len(tops) == 2 and max(tops) - min(tops) < 1
    assert measured["links"]["top"] - measured["lockup"]["top"] < 30
    assert measured["scrollWidth"] <= measured["innerWidth"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_figure_helper(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    step = {"kind": "eval", "file": FIGURE, "as": "figure",
            "args": {"good": GOOD_FIGURE, "bad": BAD_FIGURES, "other": OTHER_VALUES}}
    result = scenario(built_hub(tmp_path), browser, steps=[step])["figure"]
    assert result["hasFunction"] and not result["threw"]
    assert result["returned"]
    assert result["tag"] == "svg" and result["namespace"] == NS and result["role"] == "img"
    assert result["className"] == "hub-figure"
    assert result["children"][:2] == ["title", "desc"]
    assert set(result["tags"]) == set(FIGURE_TAGS)
    assert set(result["attrs"]) == set(FIGURE_ATTRS)
    assert result["ids"] == 0
    assert result["inserted"] and result["scriptsAdded"] == 0
    assert not result["pwned"] and not result["pwnedAfter"]
    assert result["serialised"] == result["inputSerialised"]
    assert result["bad"] == [True] * len(BAD_FIGURES), result["bad"]
    assert result["other"] == [True] * (len(OTHER_VALUES) + 1), result["other"]


def _js_array(name: str) -> list[str]:
    text = CORE_JS.read_text(encoding="utf-8")
    match = re.search(r"const " + name + r"\s*=\s*\[([^\]]*)\]", text)
    assert match, f"{name} is not declared as an array"
    return re.findall(r'"([^"]+)"', match.group(1))


def test_figure_lists_are_the_agreed_ones() -> None:
    assert _js_array("figureTags") == list(FIGURE_TAGS)
    assert _js_array("figureAttrs") == list(FIGURE_ATTRS)
