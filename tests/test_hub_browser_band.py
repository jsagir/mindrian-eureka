"""Exercise the run reading band in Chromium and Firefox: text, colours, anchors, the gate."""

from __future__ import annotations

from pathlib import Path

import pytest
from hub_browser_support import file_url, require_browser, run_scenario
from hub_support import build_run_folder_with_potential_eureka
from mindrian_eureka.hub.deck import DECK, fill
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run
from test_hub_browser_core import CHECKS, built_hub, scenario
from test_hub_browser_gate import PASS, gated_hub, submit

BAND = str(CHECKS / "band-state.js")


def band(name: str, **args):
    return {"kind": "eval", "file": BAND, "as": name, "args": args}


def reading_text(payload) -> str:
    lines = payload["pattern"]["lines"]
    return " ".join(fill(DECK[line["key"]], **line["values"]) for line in lines[:-1])


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_band_text_matches_the_server_text(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path)
    payload = build_payload(load_run(tmp_path / "run"))
    state = scenario(out, browser, steps=[band("state")])["state"]
    assert state["started"] and state["present"] and not state["hidden"]
    assert state["reading"] == reading_text(payload)
    assert state["label"] == DECK["G17.label"]
    assert state["limit"] == DECK["G16"]
    assert state["linkHref"] == "#hub-data-check" and state["linkText"] == DECK["G17.link"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_band_colours_and_marker(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    state = scenario(built_hub(tmp_path), browser, steps=[band("state")])["state"]
    assert state["bandBackground"] == "rgb(17, 17, 17)"
    assert state["bandColor"] == "rgb(247, 245, 238)"
    assert state["readingColor"] == "rgb(247, 245, 238)"
    assert state["markBackground"] == "rgb(242, 194, 0)"
    assert state["markText"] == ""
    assert state["limitColor"] == "rgb(199, 198, 191)"


def test_widths(tmp_path: Path) -> None:
    require_browser()
    steps = []
    for width in (320, 390, 768, 1280, 1600):
        steps.extend([{"kind": "setViewport", "width": width, "height": 900}, band(str(width))])
    result = scenario(built_hub(tmp_path), steps=steps)
    for width, measured in result.items():
        assert measured["scrollWidth"] <= measured["innerWidth"], width
        assert measured["columns"] == (1 if int(width) < 768 else 3), (width, measured)
        assert measured["minimum"] >= 13, width
        assert measured["linkBox"]["width"] >= 44 and measured["linkBox"]["height"] >= 44, width


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_anchor_links_raise_no_notice(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    steps = [
        {"kind": "click", "selector": ".hub-band-link"},
        band("band", settle=100),
        {"kind": "press", "key": "Tab"},
        {"kind": "press", "selector": ".hub-skip", "key": "Enter"},
        band("skip", settle=100),
        {"kind": "click", "selector": '#hub-nav a[href="#graph"]'},
        band("graph", settle=100),
    ]
    result = scenario(built_hub(tmp_path), browser, steps=steps)
    assert result["band"]["notice"] == "" and result["band"]["selection"] is None
    assert result["band"]["hash"] == "#hub-data-check"
    assert result["skip"]["notice"] == "" and result["skip"]["selection"] is None
    assert result["skip"]["hash"] == "#hub-results"
    assert result["graph"]["active"] == ["graph"] and result["graph"]["hash"] == "#graph"


def test_grouped_band_in_the_browser(tmp_path: Path) -> None:
    require_browser()
    import io

    from mindrian_eureka.hub.writer import HubRequest, build_hub
    from mindrian_eureka.run.console import Console

    run = build_run_folder_with_potential_eureka(tmp_path)
    out = tmp_path / "hub"
    build_hub(HubRequest(run, out), Console(stderr=io.StringIO()))
    payload = build_payload(load_run(run))
    state = scenario(out, steps=[band("state")])["state"]
    lines = {line["key"]: line["values"] for line in payload["pattern"]["lines"]}
    assert fill(DECK["G17.hoods"], **lines["G17.hoods"]) in state["reading"]
    assert fill(DECK["G17.bridges"], **lines["G17.bridges"]) in state["reading"]


def test_none_band_in_the_browser(tmp_path: Path) -> None:
    require_browser()
    state = scenario(built_hub(tmp_path, zero_pairs=True), steps=[band("state")])["state"]
    assert state["reading"] == DECK["G17.none"]
    assert DECK["G17.single"] not in state["text"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_gated_band_appears_only_after_unlock(tmp_path: Path, browser: str) -> None:
    pytest.importorskip("cryptography")
    require_browser(browser)
    out = gated_hub(tmp_path)
    payload = build_payload(load_run(tmp_path / "run"))
    result = scenario(out, browser, steps=[band("locked"), *submit(PASS),
                                           band("open", wait="unlocked")])
    assert result["locked"]["present"] and result["locked"]["text"] == ""
    assert result["locked"]["hidden"] is True
    assert result["open"]["reading"] == reading_text(payload)
    assert result["open"]["hidden"] is False


def test_locked_band_has_no_box(tmp_path: Path) -> None:
    pytest.importorskip("cryptography")
    require_browser()
    state = scenario(gated_hub(tmp_path), steps=[band("state")])["state"]
    assert state["present"] and state["rects"] == 0


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_reduced_motion_and_no_network(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path)
    result = run_scenario({"browser": browser, "url": file_url(out / "hub.html"),
                           "steps": [band("state")], "reducedMotion": True})
    assert result["ok"], result["stepErrors"]
    assert result["blockedRequests"] == [] and result["cspViolations"] == []
    assert result["results"]["state"]["animations"] == 0
    assert result["results"]["state"]["present"]
