"""Verify bank rows, provenance, filters and keyboard behavior in real browsers."""

from __future__ import annotations

from pathlib import Path

import pytest
from hub_browser_support import require_browser
from mindrian_eureka.hub.deck import DECK, fill
from mindrian_eureka.run.contracts import LABEL
from test_hub_browser_core import CHECKS, METRICS, built_hub, scenario

BANK = str(CHECKS / "bank-state.js")


def check(name: str, **args):
    return {"kind": "eval", "file": BANK, "as": name, "args": args}


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_paging_order_and_all_row_provenance(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path, n_records=40, pairs_per_engine=40)
    result = scenario(out, browser, steps=[check("first"), check("second", more=1),
        check("third", more=1), check("all", more=1), check("broken", removeLabel=True)])
    for name, shown in (("first", 25), ("second", 50), ("third", 75), ("all", 80)):
        state = result[name]
        assert len(state["rows"]) == shown
        assert state["status"] == fill(DECK["B09.status"], a=shown, b=80)
        assert state["violations"] == []
    assert [(row["rank"], row["engine"]) for row in result["first"]["rows"][:4]] == [
        (1, "unusual_pairs"), (1, "wording_and_meaning"),
        (2, "unusual_pairs"), (2, "wording_and_meaning")]
    for row in result["all"]["rows"]:
        assert row["text"].count(LABEL) == 1
        assert len(row["anchors"]) == 2 and row["labels"] == 1
        assert row["buttons"] == [DECK["B08.read"]]
    assert len(result["broken"]["afterMutation"]) == 1
    assert result["broken"]["afterMutation"][0].startswith("label:")


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_filters_selection_and_focus(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path, n_records=40)
    result = scenario(out, browser, steps=[
        {"kind": "click", "selector": "#bank-engine-wording_and_meaning"},
        check("filtered", views=True),
        {"kind": "click", "selector": "#bank-list .hub-bank-read"},
        check("selected"), check("cleared", clear=True)])
    state = result["filtered"]
    assert state["status"] == fill(DECK["B09.status"], a=25, b=40)
    assert {row["engine"] for row in state["rows"]} == {"wording_and_meaning"}
    assert state["filters"]["engine"] == "wording_and_meaning"
    chosen = [radio["value"] for radio in state["radios"] if radio["checked"]]
    assert chosen == ["wording_and_meaning"]
    selected = result["selected"]
    assert selected["selection"] == {"type": "pair", "key": selected["selected"]}
    assert result["cleared"]["selected"] is None
    assert result["cleared"]["focus"]["text"] == DECK["B08.read"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_weak_rows_and_cutoffs(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    weak = built_hub(tmp_path / "weak", wording_floor=0.5, percentile_below_floor=3)
    states = scenario(weak, browser, steps=[check("default", more=10),
        {"kind": "click", "selector": "#bank-weak"}, check("weak", more=10)])
    assert states["default"]["weakPresent"] and not states["default"]["weakChecked"]
    assert len(states["default"]["rows"]) == 77 and states["default"]["weakRows"] == 0
    assert len(states["weak"]["rows"]) == 80 and states["weak"]["weakRows"] == 3
    assert sum(DECK["P06.hidden"] in row["text"] for row in states["weak"]["rows"]) == 3
    mixed = scenario(built_hub(tmp_path / "mixed"), browser, steps=[check("state")])["state"]
    assert mixed["cutoffs"] == fill(DECK["B05.one.unusual_pairs"], floor="0.90") + DECK["B06"]
    none = scenario(built_hub(tmp_path / "none", unusual_floor=0), browser,
                    steps=[check("state")])["state"]
    assert none["cutoffs"] == DECK["B06"] * 2 and not none["weakPresent"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_empty_and_filter_empty(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    empty = scenario(built_hub(tmp_path / "empty", zero_pairs=True), browser,
                     steps=[check("state")])["state"]
    assert DECK["B10"] in empty["listText"] and DECK["B11"] in empty["listText"]
    assert "A plain engine note." in empty["listText"]
    out = built_hub(tmp_path / "partial", pairs_per_engine=(40, 0))
    states = scenario(out, browser, steps=[check("empty", engine="wording_and_meaning"),
        {"kind": "click", "selector": "#bank-list button"}, check("restored")])
    assert DECK["B12"] in states["empty"]["listText"]
    assert DECK["B13.body"] in states["empty"]["listText"]
    assert states["restored"]["filters"]["engine"] == "both"
    assert len(states["restored"]["rows"]) == 25


def test_widths_and_reduced_motion(tmp_path: Path) -> None:
    require_browser()
    steps = []
    for width in (320, 390, 768, 1280, 1600):
        steps.extend([{"kind": "setViewport", "width": width, "height": 900},
                      check(str(width)),
                      {"kind": "eval", "file": METRICS, "as": f"metrics-{width}"}])
    result = scenario(built_hub(tmp_path), steps=steps, reducedMotion=True)
    for width in (320, 390, 768, 1280, 1600):
        metrics = result[f"metrics-{width}"]
        assert metrics["scrollWidth"] <= width and metrics["minimum"] >= 13
        assert metrics["targets"] == []
        for row in result[str(width)]["metrics"]:
            assert row["width"] >= 44 and row["height"] >= 44
            assert row["transition"] == "0s"
            if width >= 1024:
                assert row["columns"] == 12
                assert abs(row["buttonTop"] - row["recordsTop"]) < 2
        assert result[str(width)]["animations"] == 0


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_keyboard_and_hostile_records(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path, hostile=True)
    result = scenario(out, browser, steps=[
        {"kind": "focus", "selector": "#bank-engine-both"},
        {"kind": "press", "selector": "#bank-engine-both", "key": "ArrowRight"},
        check("radio"), {"kind": "press", "key": "Tab"}, check("first-source"),
        {"kind": "press", "key": "Tab"}, check("second-source"),
        {"kind": "press", "key": "Tab"}, check("read-button"),
        {"kind": "press", "selector": "#bank-list .hub-bank-read", "key": "Enter"},
        check("selected", more=10)])
    assert result["radio"]["filters"]["engine"] == "unusual_pairs"
    assert result["first-source"]["focus"]["tag"] == "A"
    assert result["second-source"]["focus"]["tag"] == "A"
    assert result["read-button"]["focus"]["text"] == DECK["B08.read"]
    assert result["selected"]["selection"]["type"] == "pair"
    assert not result["selected"]["injected"]
    rows = result["selected"]["rows"]
    assert any("<script>" in row["text"] for row in rows)
    assert any(anchor["text"] == "bank" and anchor["href"] == "#record:bank"
               for row in rows for anchor in row["anchors"])
