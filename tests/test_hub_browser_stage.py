"""Verify the local settled 3D stage and synthetic test fixture, not a finding."""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from hub_browser_support import file_url, require_browser, run_scenario
from mindrian_eureka.hub.deck import DECK
from mindrian_eureka.run.contracts import LABEL
from test_hub_browser_core import CHECKS, METRICS, built_hub, scenario
from test_hub_browser_graph import positive_hub

STAGE = str(CHECKS / "stage-state.js")


def check(name: str, **args):
    return {"kind": "eval", "file": STAGE, "as": name, "args": args}


def distance(a, b):
    return math.sqrt(sum((a[key] - b[key]) ** 2 for key in ("x", "y", "z")))


def assert_selection_uncovered(state):
    point = state["selectedPoint"]
    x = state["stage"]["x"] + point["x"]
    y = state["stage"]["y"] + point["y"]
    panel = state["panelBounds"]
    assert not (panel["x"] <= x <= panel["x"] + panel["width"]
                and panel["y"] <= y <= panel["y"] + panel["height"])


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
@pytest.mark.parametrize("width", [320, 1280])
def test_earned_bridges_links_and_provenance(tmp_path: Path, browser: str, width: int) -> None:
    require_browser(browser)
    state = scenario(positive_hub(tmp_path), browser,
                     viewport={"width": width, "height": 900}, steps=[check("state")])["state"]
    assert state["mode"] == "3d" and state["canvas"]
    assert state["role"] == "img" and state["aria"] == DECK["Gr13"]
    assert state["tabindex"] is None and state["canvasTab"] is None
    assert state["vendor"] == ["vendor/3d-force-graph.min.js"]
    assert not state["stageButtonsHidden"] and len(state["buttons"]) == 3
    assert all(b["width"] >= 44 and b["height"] >= 44 for b in state["buttons"])
    assert len(state["nodes"]) == state["expectedNodes"] == 21
    assert len(state["links"]) == state["expectedLinks"] == 184
    assert state["readyCount"] == 1
    assert all(0 <= point["x"] <= state["stage"]["width"]
               and 0 <= point["y"] <= state["stage"]["height"] for point in state["projected"])
    bridge_nodes = [n for n in state["nodes"] if n["bridge"]]
    assert [n["id"] for n in bridge_nodes] == ["synthetic-b-000", "synthetic-z-connector"]
    assert len(state["chips"]) == len(bridge_nodes) == 2
    sources = {n["id"]: n["source"] for n in bridge_nodes}
    for node in bridge_nodes:
        assert node["color"].lower() == "#f2c200" and node["material"] == "f2c200"
        assert node["shell"] == {"color": "111111", "side": 1, "scale": 1.18,
                                  "position": [0, 0, 0]}
    for chip in state["chips"]:
        assert chip["text"] == f'Potential eureka {chip["id"]}'
        assert chip["status"] == LABEL and chip["source"] == sources[chip["id"]]
        assert chip["size"] >= 13 and not chip["hidden"]
    assert state["particles"] == 0 and any(link["crosses"] for link in state["links"])
    assert all(link["color"].lower() == "#1f3fbf" and link["width"] == link["expected"]
               and link["label"] == LABEL for link in state["links"])
    assert all(link["width"] == 1.6 for link in state["links"] if link["crosses"])
    assert not any(state["nodeLabels"]) and not any(state["linkLabels"])


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
@pytest.mark.parametrize("reduced", ["no-preference", "reduce"])
def test_at_rest_positions_and_pixels(tmp_path: Path, browser: str, reduced: str) -> None:
    require_browser(browser)
    first, second = tmp_path / "first.png", tmp_path / "second.png"
    result = scenario(positive_hub(tmp_path), browser, reducedMotion=reduced == "reduce", steps=[
        check("state", wait=700, scroll=True), {"kind": "screenshot", "path": str(first)},
        {"kind": "wait", "ms": 1500}, {"kind": "screenshot", "path": str(second)}])
    assert result["state"]["beforeCoords"] == result["state"]["afterCoords"]
    assert first.read_bytes() == second.read_bytes()


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
@pytest.mark.parametrize("reduced", ["no-preference", "reduce"])
def test_camera_selection_tour_find_zoom_reset(tmp_path: Path, browser: str, reduced: str) -> None:
    require_browser(browser)
    selected_id = "synthetic-a-009"
    result = scenario(positive_hub(tmp_path), browser, reducedMotion=reduced == "reduce", steps=[
        check("initial"), check("selected", action="select", id=selected_id, trackCamera=True),
        check("zoomIn", action="zoomIn", trackCamera=True),
        check("zoomOut", action="zoomOut", trackCamera=True),
        check("reset", action="reset", trackCamera=True),
        check("tour", action="tour", trackCamera=True),
        check("find", action="find", id=selected_id, trackCamera=True),
        {"kind": "click", "selector": "#graph-stage canvas", "position": {"x": 4, "y": 4}},
        check("background")])
    initial, selected = result["initial"], result["selected"]
    assert selected["selected"] == {"type": "record", "id": selected_id}
    assert_selection_uncovered(selected)
    assert selected["selectedChip"]["text"] == selected_id
    assert not selected["selectedChip"]["hidden"]
    assert selected["selectedChip"]["background"] == "rgb(255, 255, 255)"
    assert any(n["color"].lower() == "#d8d4c8" for n in selected["nodes"])
    assert all(chip["hidden"] for chip in selected["chips"])
    if reduced == "reduce":
        assert selected["duration"] == 0 and len(selected["moves"]) == 1
        assert selected["timeline"][0]["position"] == selected["position"]
    else:
        assert selected["duration"] == 760 and len(selected["moves"]) > 1
        assert selected["timeline"][0]["position"] != selected["position"]
        early = selected["timeline"][1]
        assert distance(early["position"], early["aim"]) > 100.01
    assert distance(selected["position"], selected["timeline"][-1]["aim"]) == pytest.approx(100)
    assert distance(result["zoomIn"]["position"], result["zoomIn"]["timeline"][-1]["aim"]) < 100
    zoomed_out = result["zoomOut"]
    assert distance(zoomed_out["position"], zoomed_out["timeline"][-1]["aim"]) == pytest.approx(100)
    assert distance(result["reset"]["position"], initial["position"]) < 1e-6
    assert result["tour"]["selected"]["id"] == "synthetic-b-000"
    assert DECK["P03.why"] in result["tour"]["panel"] and LABEL in result["tour"]["panel"]
    assert result["find"]["selected"]["id"] == selected_id
    assert result["background"]["selected"] is None and not result["background"]["panelOpen"]
    assert not any(n["color"].lower() == "#d8d4c8" for n in result["background"]["nodes"])
    assert not selected["unwantedControls"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
@pytest.mark.parametrize("failure", ["webgl", "missing", "throwing"])
def test_fallbacks(tmp_path: Path, browser: str, failure: str) -> None:
    require_browser(browser)
    out = positive_hub(tmp_path)
    vendor = out / "vendor/3d-force-graph.min.js"
    if failure == "missing":
        vendor.unlink()
    if failure == "throwing":
        vendor.write_text('window.ForceGraph3D=function(){throw new Error("Synthetic failure")};')
    result = run_scenario({"browser": browser, "url": file_url(out / "hub.html"),
                           "webgl": failure != "webgl", "steps": [check("state")]})
    assert result["ok"] and result["pageErrors"] == []
    assert result["blockedRequests"] == [] and result["cspViolations"] == []
    errors = [item for item in result["console"] if item["type"] == "error"]
    handled = [item for item in errors if item["text"] == "Graph stage unavailable"]
    assert len(handled) == (0 if failure == "webgl" else 1)
    state = result["results"]["state"]
    assert state["mode"] == "fallback" and state["fallback"] == DECK["Gr12"]
    assert state["listInStage"] and state["stageButtonsHidden"] and not state["canvas"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_tooltips_text_and_hostile_safety(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path, hostile=True, n_records=40, pairs_per_engine=200, clusters=3)
    result = scenario(out, browser,
                      steps=[check("node", nodeTip=True), check("link", linkTip=True)])
    assert "<script>" in result["node"]["tooltip"]
    assert "Neighborhood" in result["node"]["tooltip"]
    assert not result["node"]["injected"] and result["node"]["tooltipElements"] == 0
    assert LABEL in result["link"]["tooltip"] and "Proposed pair" in result["link"]["tooltip"]
    assert "engine" in result["link"]["tooltip"]


def test_widths_fonts_targets_and_reflow(tmp_path: Path) -> None:
    require_browser()
    steps = []
    for width in (320, 390, 768, 1280, 1600):
        steps += [{"kind": "setViewport", "width": width, "height": 900}, check(str(width)),
                  {"kind": "eval", "file": METRICS, "as": f"metrics-{width}"},
                  check(f"selected-{width}", action="select", id="synthetic-b-000"),
                  check(f"clear-{width}", action="clear", samples=[])]
    result = scenario(positive_hub(tmp_path), steps=steps)
    for width in (320, 390, 768, 1280, 1600):
        state = result[str(width)]
        assert_selection_uncovered(result[f"selected-{width}"])
        assert state["stage"]["height"] == 560
        assert state["scrollWidth"] <= width
        assert result[f"metrics-{width}"]["minimum"] >= 13
        assert result[f"metrics-{width}"]["targets"] == []
        for chip in state["chips"]:
            assert chip["size"] >= 13
            assert chip["x"] >= state["stage"]["x"]
            assert chip["x"] + chip["width"] <= state["stage"]["x"] + state["stage"]["width"] + 1


def test_scale_3000_graph_ready(tmp_path: Path) -> None:
    require_browser()
    out = built_hub(tmp_path, n_records=3000, pairs_per_engine=200, clusters=3)
    state = scenario(out, steps=[check("state")])["state"]
    assert state["mode"] == "3d" and 0 < state["readyMs"] <= 20000
    assert len(state["nodes"]) == state["expectedNodes"]
    assert len(state["links"]) == 400
    print(f'graph-ready: {state["readyMs"] / 1000:.4f} seconds; '
          f'{len(state["nodes"])} nodes, {len(state["links"])} links')
