"""Prove graph routes using synthetic test fixtures, not findings, and real empty copy."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from hub_browser_support import require_browser
from hub_support import build_run_folder_with_potential_eureka
from mindrian_eureka.hub.deck import DECK, fill
from mindrian_eureka.hub.writer import HubRequest, build_hub
from mindrian_eureka.run.console import Console
from mindrian_eureka.run.contracts import LABEL
from test_hub_browser_core import CHECKS, METRICS, built_hub, scenario

GRAPH = str(CHECKS / "graph-state.js")
ROOT = Path(__file__).resolve().parents[1]


def check(name: str, **args):
    return {"kind": "eval", "file": GRAPH, "as": name, "args": args}


def positive_hub(tmp_path: Path) -> Path:
    """Build the owner's synthetic test fixture, not a finding."""
    run = build_run_folder_with_potential_eureka(tmp_path)
    out = tmp_path / "hub"
    build_hub(HubRequest(run, out), Console(stderr=io.StringIO()))
    return out


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_fallback_legend_and_all_pair_provenance(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    state = scenario(positive_hub(tmp_path), browser, webgl=False,
                     steps=[check("state", allPairs=True, negative=True)])["state"]
    assert state["mode"] == "fallback" and state["instance"] and state["fly"] is False
    assert len(state["bridges"]) == 2
    assert state["fallback"] == {"visible": True, "text": DECK["Gr12"]}
    assert state["listInStage"] and state["buttonsHidden"] and state["stageTab"] is None
    assert state["legend"] == [DECK["Gr03." + key] for key in
        ("record", "eureka", "unusual_pairs", "wording_and_meaning", "crossing", "selected")]
    assert len(state["swatches"]) == 6
    assert len(state["rows"]) == state["pairCount"] > 25
    for row in state["rows"]:
        assert row["labelCount"] == 1 and row["proposed"] == "Proposed"
        assert [a["href"] for a in row["anchors"]] == row["expected"]
        assert len(row["anchors"]) == 2 and all(a["text"] for a in row["anchors"])
    assert state["negative"] is True
    assert state["pairStatus"] == fill(DECK["B09.status"],
                                       a=state["pairCount"], b=state["pairCount"])


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_small_diagram_selection_and_sources(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path, n_records=12, pairs_per_engine=6, clusters=3)
    states = scenario(out, browser, webgl=False, viewport={"width": 320, "height": 900},
                      steps=[check("initial"), check("selected", circle=True),
                             check("pair", pair=True), check("clear", clear=True)])
    state = states["selected"]
    assert state["mode"] == "diagram" and state["small"]["text"] == DECK["Gr10"]
    assert state["circleCount"] > 0 and state["buttonsHidden"]
    assert all(r["width"] >= 44 and r["height"] >= 44 for r in state["circleButtons"])
    assert state["chords"] and all(c["dash"] == "7 8" for c in state["chords"])
    assert any(c["crosses"] for c in state["chords"])
    assert all(c["width"] == ("4px" if c["crosses"] else "2px") for c in state["chords"])
    assert min(state["effectiveFonts"]) >= 13
    assert sum(c["selected"] for c in state["circleData"]) == 1
    assert any(c["dimmed"] for c in state["circleData"])
    assert all(c["fill"] == "rgb(216, 212, 200)" for c in state["circleData"] if c["dimmed"])
    assert next(c for c in state["circleData"] if c["selected"])["stroke"] == "3px"
    assert state["scrollWidth"] <= 320
    assert states["pair"]["selection"]["type"] == "pair"
    assert sum(row["selected"] for row in states["pair"]["rows"]) == 1
    assert not any(row["selected"] for row in states["clear"]["rows"])


def test_empty(tmp_path: Path) -> None:
    require_browser()
    state = scenario(built_hub(tmp_path, zero_pairs=True), webgl=False,
                     steps=[check("state")])["state"]
    assert state["mode"] == "empty" and not state["rows"]
    assert state["emptyTitle"] == {"visible": True, "text": DECK["Gr17"]}
    assert state["emptyBody"] == {"visible": True, "text": DECK["Gr18"]}
    assert state["buttonsHidden"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_find_and_tour_positive_synthetic(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    result = scenario(positive_hub(tmp_path), browser, webgl=False, steps=[
        check("initial"), check("find", find="synthetic"), check("choose", chooseFind=True),
        check("tour", tour=3), check("none", find="zzzznotfound"),
        {"kind": "fill", "selector": "#graph-find", "value": "synthetic-z-connector"},
        {"kind": "press", "selector": "#graph-find", "key": "Enter"}, check("enter"),
        {"kind": "press", "selector": "#graph-find", "key": "Escape"}, check("escape")])
    assert result["initial"]["tourText"] == DECK["Gr05.tour"]
    assert not result["initial"]["tourHidden"] and not result["initial"]["tourEmpty"]["visible"]
    assert len(result["find"]["matches"]) == 8 and result["find"]["findCount"] == "8 matches."
    assert result["choose"]["selection"]["type"] == "record"
    ids = result["tour"]["bridges"]
    assert ids == ["synthetic-b-000", "synthetic-z-connector"]
    for i, state in enumerate(result["tour"]["tourStates"]):
        assert state["selection"]["id"] == ids[i % 2]
        assert state["text"] == fill(DECK["Gr05.next"], i=i % 2 + 1, n=2)
        assert DECK["P03.why"] in state["panel"] and LABEL in state["panel"]
        assert "synthetic test fixture" in state["panel"].lower()
    assert result["none"]["findCount"] == DECK["Gr04.none"]
    assert len(result["enter"]["matches"]) == 1 and not result["escape"]["matches"]
    assert not result["enter"]["datalist"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_real_public_example_honest_none(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    run = ROOT / "tests/fixtures/hub_public/run"
    out = tmp_path / "hub"
    build_hub(HubRequest(run, out), Console(stderr=io.StringIO()))
    state = scenario(out, browser, webgl=False, steps=[check("state", guide=True)])["state"]
    assert state["bridges"] == [] and state["tourHidden"]
    assert state["tourEmpty"] == {"visible": True, "text": DECK["Gr09"]}
    assert fill(DECK["B05.one.unusual_pairs"], floor="0.90") in state["text"]
    assert DECK["B06"] in state["text"]


def test_widths_and_nonpointer_controls(tmp_path: Path) -> None:
    require_browser()
    steps = []
    for width in (320, 390, 768, 1280, 1600):
        steps += [{"kind": "setViewport", "width": width, "height": 900}, check(str(width)),
                  {"kind": "eval", "file": METRICS, "as": f"metrics-{width}"}]
    result = scenario(positive_hub(tmp_path), webgl=False, steps=steps)
    for width in (320, 390, 768, 1280, 1600):
        state = result[str(width)]
        assert state["guide"]["expanded"] == str(width >= 768).lower()
        assert state["stageTab"] is None and state["buttonsHidden"]
        assert all(state["names"]) and all(c["size"] >= 13 for c in state["chips"])
        metrics = result[f"metrics-{width}"]
        assert metrics["minimum"] >= 13 and metrics["targets"] == []
        assert metrics["scrollWidth"] <= width


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_keyboard_find_tour_and_escape(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    result = scenario(positive_hub(tmp_path), browser, webgl=False, steps=[
        check("find", focusFind=True), {"kind": "press", "key": "Tab"}, check("button"),
        {"kind": "press", "key": "Tab"}, check("tour"),
        {"kind": "press", "key": "Enter"}, check("selected"),
        {"kind": "press", "key": "Escape"}, check("closed")])
    assert result["button"]["focusText"] == DECK["Gr04.button"]
    assert result["tour"]["focus"] == "graph-tour"
    assert result["selected"]["selection"]["id"] == "synthetic-b-000"
    assert result["closed"]["focus"] == "graph-tour"
    assert result["closed"]["selection"] is None


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
@pytest.mark.parametrize("size", [12, 40])
def test_hostile_text(tmp_path: Path, browser: str, size: int) -> None:
    require_browser(browser)
    out = built_hub(tmp_path, n_records=size, pairs_per_engine=6 if size == 12 else 40,
                    clusters=3, hostile=True)
    state = scenario(out, browser, webgl=False, steps=[check("state", find="script")])["state"]
    assert not state["injected"]
    assert "<script>" in state["text"] and any("<script>" in value for value in state["matches"])


def test_deviation_record() -> None:
    authored = ROOT / "src/mindrian_eureka/hub/assets/authored"
    for name in ("hub-graph.js", "hub-graph.css"):
        text = (authored / name).read_text()
        assert text.count("Deviation from the book graph guide") == 1
        assert "no particles" in text
    assert "Deviations from the book guide" in (ROOT / "docs/brand/hub-model-rules.md").read_text()
