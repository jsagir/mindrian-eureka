"""Measure the finished public surface without claiming human visual approval."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from hub_browser_support import require_browser
from mindrian_eureka.hub.writer import HubRequest, build_hub
from mindrian_eureka.run.console import Console
from test_hub_browser_core import CHECKS, METRICS, scenario
from test_hub_browser_graph import positive_hub

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "tests/fixtures/hub_public/run"
STATE = str(CHECKS / "review-state.js")
CONTRAST = str(CHECKS / "review-contrast.js")
SPACING = str(CHECKS / "review-spacing.js")


def state(name: str, **args):
    return {"kind": "eval", "file": STATE, "as": name, "args": args}


def evaluate(file: str, name: str):
    return {"kind": "eval", "file": file, "as": name}


def public_hub(tmp_path: Path, password=None) -> Path:
    out = tmp_path / "hub"
    build_hub(HubRequest(PUBLIC, out, password=password), Console(stderr=io.StringIO()))
    return out


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_text_contrast_and_reflow(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    steps = []
    for width in (320, 640):
        steps.append({"kind": "setViewport", "width": width, "height": 900})
        for view in ("bank", "graph", "catalogue"):
            name = f"{view}-{width}"
            steps += [state(name, view=view, clear=True), evaluate(CONTRAST, name + "-contrast")]
    steps += [state("panel", view="bank", panel="record", full=True),
              evaluate(CONTRAST, "panel-contrast")]
    result = scenario(public_hub(tmp_path), browser, steps=steps)
    print(json.dumps(result, sort_keys=True))
    for name, measured in result.items():
        if name.endswith("-contrast"):
            assert measured["checked"] > 0
            assert measured["failures"] == [] and measured["yellow"] == [], (name, measured)
        else:
            assert measured["scrollWidth"] <= measured["width"]
            assert measured["targets"] == [] and measured["hiddenFocusable"] == []
    assert result["panel"]["sourceJoined"] == result["panel"]["sourceText"]
    assert max(result["panel"]["paragraphWords"]) <= 100


@pytest.mark.parametrize("width", [390, 1280])
def test_text_spacing(tmp_path: Path, width: int) -> None:
    require_browser()
    steps = []
    for view in ("bank", "graph", "catalogue"):
        steps += [state(view, view=view, clear=True), evaluate(SPACING, view + "-spacing")]
    steps += [state("panel", view="bank", panel="record", full=True),
              evaluate(SPACING, "panel-spacing")]
    result = scenario(public_hub(tmp_path), viewport={"width": width, "height": 900}, steps=steps)
    print(json.dumps(result, sort_keys=True))
    for name, measured in result.items():
        if name.endswith("-spacing"):
            assert measured["scrollWidth"] <= width and measured["clipped"] == [], (name, measured)


def test_font_floor_and_targets_at_five_widths(tmp_path: Path) -> None:
    require_browser()
    steps = []
    for width in (320, 390, 768, 1280, 1600):
        steps.append({"kind": "setViewport", "width": width, "height": 900})
        for view in ("bank", "graph", "catalogue"):
            name = f"{view}-{width}"
            steps += [state(name, view=view), evaluate(METRICS, name + "-metrics")]
    result = scenario(public_hub(tmp_path), steps=steps)
    print(json.dumps({name: value for name, value in result.items() if name.endswith("-metrics")}))
    for name, measured in result.items():
        assert measured["targets"] == []
        if name.endswith("-metrics"):
            assert measured["minimum"] >= 13 and measured["small"] == []
            assert measured["scrollWidth"] <= measured["innerWidth"]


def test_forced_colors_controls_visible(tmp_path: Path) -> None:
    require_browser()
    result = scenario(public_hub(tmp_path), forcedColors="active", steps=[
        state(view, view=view) for view in ("bank", "graph", "catalogue")])
    print(json.dumps(result, sort_keys=True))
    assert all(measured["forced"] and measured["controls"] for measured in result.values())
    assert all(all(control["name"] for control in measured["controls"])
               for measured in result.values())


def test_locked_and_unlocked_contrast(tmp_path: Path) -> None:
    require_browser()
    pytest.importorskip("cryptography")
    password = "synthetic final review test passphrase"
    result = scenario(public_hub(tmp_path, password), steps=[
        evaluate(CONTRAST, "locked"),
        {"kind": "fill", "selector": "#hub-passphrase", "value": password},
        {"kind": "press", "selector": "#hub-passphrase", "key": "Enter"},
        {"kind": "eval", "file": str(CHECKS / "gate-state.js"), "as": "gate",
         "args": {"wait": "unlocked"}}, evaluate(CONTRAST, "unlocked")])
    assert result["gate"]["count"] == 36 and not result["gate"]["locked"]
    for name in ("locked", "unlocked"):
        assert result[name]["checked"] and result[name]["failures"] == []
        assert result[name]["yellow"] == []


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_marked_links_and_nonfocusable_opener(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    result = scenario(positive_hub(tmp_path), browser, steps=[
        state("links", view="graph"), state("closed", opener=True)])
    assert result["links"]["hiddenFocusable"] == []
    assert result["closed"]["focus"] == "hub-title" and not result["closed"]["panelOpen"]



def test_measurement_negative_controls(tmp_path: Path) -> None:
    require_browser()
    result = scenario(public_hub(tmp_path), steps=[
        state("view", view="catalogue"),
        {"kind": "eval", "file": CONTRAST, "as": "contrast", "args": {"negative": True}},
        {"kind": "eval", "file": SPACING, "as": "spacing", "args": {"negative": True}}])
    assert "review-negative" in {item["id"] for item in result["contrast"]["failures"]}
    assert "review-yellow" in {item["id"] for item in result["contrast"]["yellow"]}
    assert "review-clipped" in {item["id"] for item in result["spacing"]["clipped"]}


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_desktop_graph_escapes_reading_measure_and_uses_viewport(
    tmp_path: Path, browser: str,
) -> None:
    require_browser(browser)
    result = scenario(public_hub(tmp_path), browser, steps=[
        {"kind": "setViewport", "width": width, "height": 900}
        if index % 2 == 0 else state(str(width), view="graph")
        for width in (1280, 1600, 1800) for index in range(2)])
    for width in (1280, 1600, 1800):
        measured = result[str(width)]
        scene = measured["scene"]
        assert abs(scene["width"] - min(1600, width - 64)) < 1
        assert abs(scene["x"] - (width - scene["width"]) / 2) < 1
        assert abs(measured["stage"]["height"] - 836) < 1
        assert measured["scrollWidth"] <= width
