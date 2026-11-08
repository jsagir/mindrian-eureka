"""Verify bank rows, provenance, filters and keyboard behavior in real browsers."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from hub_browser_support import require_browser
from mindrian_eureka.hub.deck import DECK, fill
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.run.contracts import LABEL
from test_hub_browser_core import CHECKS, METRICS, built_hub, scenario

BANK = str(CHECKS / "bank-state.js")
COBALT = "rgb(31, 63, 191)"
RED = "rgb(214, 40, 31)"
SOFT = "rgb(75, 73, 67)"


def check(name: str, **args):
    return {"kind": "eval", "file": BANK, "as": name, "args": args}


def viewport(width: int) -> dict[str, object]:
    return {"kind": "setViewport", "width": width, "height": 900}


def canonical(svg: str) -> list[list[object]]:
    """The same canonical form of a figure that bank-state.js builds in the page."""
    out: list[list[object]] = []
    for element in ET.fromstring(svg).iter():
        tag = element.tag.split("}")[-1]
        attrs = sorted(
            ([name.split("}")[-1], value] for name, value in element.attrib.items()
             if not name.startswith("xmlns")),
            key=lambda item: f"{item[0]},{item[1]}",
        )
        text = (element.text or "") if tag in ("text", "title", "desc") else ""
        out.append([tag, attrs, text])
    return out


def intersects(a: dict[str, float], b: dict[str, float]) -> bool:
    return a["left"] < b["right"] and b["left"] < a["right"] \
        and a["top"] < b["bottom"] and b["top"] < a["bottom"]


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
def test_row_has_the_prototype_parts(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path, n_records=40, pairs_per_engine=40)
    payload = build_payload(load_run(tmp_path / "run"))
    pairs = {pair["key"]: pair for pair in payload["pairs"]}
    terms = payload["terms"]["pairs"]
    figures = payload["figures"]
    state = scenario(out, browser, steps=[check("state", parts=4)])["state"]
    assert len(state["parts"]) == 4
    for part in state["parts"]:
        pair = pairs[part["key"]]
        route = f"#/pair/{pair['engine']}/{pair['rank']}"
        order = [child["class"].split()[0] for child in part["children"]]
        assert order == ["hub-bank-rank", "hub-bank-records", "hub-bank-nums", "hub-bank-body",
                         "hub-bank-figure"], order
        assert part["rankVisible"] == f"{pair['rank']:02d}"
        assert part["rankAriaHidden"] == "true"
        assert part["rankHidden"] == fill(DECK["B08.rank"], n=pair["rank"])
        assert part["title"] == {"href": route,
                                 "text": f"{pair['left']['title']} and {pair['right']['title']}"}
        assert part["titleLinks"] == 1
        assert part["recordsOrder"] == ["hub-bank-pair", "hub-bank-ids"]
        assert [(item["href"], item["text"]) for item in part["ids"]] == [
            (pair["left"]["source_link"], pair["left"]["id"]),
            (pair["right"]["source_link"], pair["right"]["id"])]
        assert part["numerals"][0]["value"] == pair["meaning_text"]
        assert part["numerals"][1]["value"] == pair["wording_text"]
        assert "hub-bank-numeral--meaning" in part["numerals"][0]["kind"]
        assert "hub-bank-numeral--wording" in part["numerals"][1]["kind"]
        assert [item["caption"] for item in part["numerals"]] == [
            DECK["B08.caption.meaning"], DECK["B08.caption.wording"]]
        for numeral in part["numerals"]:
            assert re.fullmatch(r"-?\d+\.\d{4}", numeral["value"]), numeral
        assert fill(DECK["B08.rank_score"], z=pair["rank_score_text"]) in part["numsText"]
        assert DECK["P06.inferred"] in part["numsText"]
        assert part["bodyOrder"][0] == "hub-bank-labels"
        assert part["bodyOrder"][-2:] == ["hub-bank-reading", "hub-bank-actions"]
        labels = part["labels"]
        assert payload["engines"][pair["engine"]]["short_name"] in labels
        assert DECK["P06.proposed"] in labels and labels.count(LABEL) == 1
        assert part["readingOrder"][:3] == ["", "hub-bank-shared", "hub-bank-use"]
        assert part["reading"] == pair["reading"]
        shared = terms.get(pair["pair_id"], [])
        expected = fill(DECK["B08.shared"], list=", ".join(shared)) if shared \
            else DECK["B08.shared_none"]
        assert part["shared"] == expected
        assert part["useLabel"] == DECK["B08.use.label"]
        assert part["use"] == DECK["B08.use.label"] + " " + DECK["B08.use." + pair["reading_kind"]]
        assert [(a["tag"], a["text"], a["href"]) for a in part["actions"]] == [
            ("A", DECK["B08.open"], route), ("BUTTON", DECK["B08.read"], None)]
        assert "hub-bank-open-btn" in part["actions"][0]["class"]
        assert "hub-bank-read" in part["actions"][1]["class"]
        figure = part["figure"]
        assert figure["svgCount"] == 1 and figure["role"] == "img"
        assert figure["tree"] == canonical(figures["pairs"][pair["key"]]["card"])
        assert figure["caption"] == figures["legend"]["caption"]
        assert not part["hasSeed"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_stretched_link_and_separate_controls(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path)
    state = scenario(out, browser, steps=[viewport(1280), check("state", points=True)])["state"]
    points = state["points"]
    assert points["rowPosition"] == "relative"
    assert points["after"]["position"] == "absolute" and points["after"]["content"] == '""'
    assert {points["after"][side] for side in ("top", "right", "bottom", "left")} == {"0px"}
    assert points["blank"]["inRow"] and points["blank"]["title"], points["blank"]
    assert points["title"]["title"], points["title"]
    assert len(points["sources"]) == 2
    for source in points["sources"]:
        assert source["source"] and not source["title"], source
    assert points["open"]["open"] and not points["open"]["title"], points["open"]
    assert points["read"]["read"] and not points["read"]["title"], points["read"]
    assert points["sameHref"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_legend_details_and_screening_aid_text(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path)
    legend = build_payload(load_run(tmp_path / "run"))["figures"]["legend"]
    state = scenario(out, browser, steps=[check("state")])["state"]
    assert len(state["legend"]) == 1
    details = state["legend"][0]
    assert details["open"] is False
    assert details["summary"] == legend["summary"]
    assert details["body"] == [legend["card"]]
    assert "screening aid" in details["text"] and "not evidence" in details["text"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_numerals_and_colours(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    normal = scenario(built_hub(tmp_path / "normal"), browser,
                      steps=[check("state", colours=True)])["state"]
    assert normal["colours"]
    for row in normal["colours"]:
        assert not row["weak"]
        assert (row["rank"], row["meaning"], row["wording"]) == (RED, COBALT, RED), row
    weak = built_hub(tmp_path / "weak", wording_floor=0.5, percentile_below_floor=3)
    state = scenario(weak, browser, steps=[{"kind": "click", "selector": "#bank-weak"},
                                           check("state", more=10, colours=True)])["state"]
    weak_rows = [row for row in state["colours"] if row["weak"]]
    assert len(weak_rows) == 3
    for row in weak_rows:
        assert (row["rank"], row["meaning"], row["wording"]) == (SOFT, SOFT, SOFT), row


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_extras_and_labels_do_not_overlap(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path, pair_classes=True)
    steps = []
    for width in (360, 768, 1280):
        steps.extend([viewport(width), check(str(width), overlap=True)])
    result = scenario(out, browser, steps=steps)
    for width in (360, 768, 1280):
        rows = result[str(width)]["overlap"]
        assert any(row["extras"] for row in rows), width
        for row in rows:
            assert row["labels"] is not None, (width, row["key"])
            for extras in row["extras"]:
                assert not intersects(extras, row["labels"]), (width, row["key"], extras)
                assert extras["top"] >= row["labels"]["bottom"] - 1, (width, row["key"], extras)


def test_panel_open_uses_the_tablet_layout(tmp_path: Path) -> None:
    require_browser()
    out = built_hub(tmp_path)
    result = scenario(out, steps=[viewport(1280), check("closed"),
                                  {"kind": "click", "selector": "#bank-list .hub-bank-read"},
                                  check("open", settle=100)])
    assert not result["closed"]["panelOpen"]
    for row in result["closed"]["metrics"]:
        assert row["columns"] == 5
    assert result["open"]["panelOpen"]
    for row in result["open"]["metrics"]:
        assert row["columns"] == 3, row
        assert row["figureTop"] >= row["bodyBottom"] - 1, row


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_read_button_still_opens_the_panel(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path)
    result = scenario(out, browser, steps=[
        {"kind": "click", "selector": "#bank-list .hub-bank-read"},
        check("selected"), check("cleared", clear=True)])
    selected = result["selected"]
    assert selected["panelOpen"] and selected["selection"]["type"] == "pair"
    assert selected["selection"]["key"] == selected["selected"]
    assert not result["cleared"]["panelOpen"] and result["cleared"]["selected"] is None
    assert result["cleared"]["focus"]["text"] == DECK["B08.read"]


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
        steps.extend([viewport(width), check(str(width)),
                      {"kind": "eval", "file": METRICS, "as": f"metrics-{width}"}])
    result = scenario(built_hub(tmp_path), steps=steps, reducedMotion=True)
    for width in (320, 390, 768, 1280, 1600):
        metrics = result[f"metrics-{width}"]
        assert metrics["scrollWidth"] <= width and metrics["minimum"] >= 13
        assert metrics["targets"] == []
        for row in result[str(width)]["metrics"]:
            assert row["width"] >= 44 and row["height"] >= 44
            assert row["transition"] == "0s"
            # Phase 2.3.1 plan 06: 2 tracks under 768 px, 3 from 768 px, 5 from 1024 px.
            # The Read button sits in the body block under the reading text; the figure is
            # right of the body from 1024 px and under it below 1024 px.
            assert row["buttonTop"] >= row["readingBottom"] - 1, (width, row)
            if width >= 1024:
                assert row["columns"] == 5, (width, row)
                assert abs(row["bodyTop"] - row["recordsTop"]) < 2, (width, row)
                assert row["figureLeft"] >= row["bodyRight"] - 1, (width, row)
            elif width >= 768:
                assert row["columns"] == 3, (width, row)
                assert row["figureTop"] >= row["bodyBottom"] - 1, (width, row)
            else:
                assert row["columns"] == 2, (width, row)
                assert row["figureTop"] >= row["bodyBottom"] - 1, (width, row)
        assert result[str(width)]["animations"] == 0


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_keyboard_and_hostile_records(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path, hostile=True)
    result = scenario(out, browser, steps=[
        {"kind": "focus", "selector": "#bank-engine-both"},
        {"kind": "press", "selector": "#bank-engine-both", "key": "ArrowRight"},
        check("radio"), {"kind": "press", "key": "Tab"}, check("title-link"),
        {"kind": "press", "key": "Tab"}, check("first-source"),
        {"kind": "press", "key": "Tab"}, check("second-source"),
        {"kind": "press", "key": "Tab"}, check("open-link"),
        {"kind": "press", "key": "Tab"}, check("read-button"),
        {"kind": "press", "selector": "#bank-list .hub-bank-read", "key": "Enter"},
        check("selected", more=10)])
    assert result["radio"]["filters"]["engine"] == "unusual_pairs"
    # Phase 2.3.1 plan 06: title link, source A, source B, Open this pair, Read this pair.
    title = result["title-link"]["focus"]
    assert title["tag"] == "A" and "hub-bank-open-link" in title["class"]
    assert title["href"].startswith("#/pair/unusual_pairs/")
    assert result["first-source"]["focus"]["tag"] == "A"
    assert "hub-link" in result["first-source"]["focus"]["class"]
    assert result["second-source"]["focus"]["tag"] == "A"
    assert "hub-link" in result["second-source"]["focus"]["class"]
    open_link = result["open-link"]["focus"]
    assert open_link["tag"] == "A" and open_link["text"] == DECK["B08.open"]
    assert open_link["href"] == title["href"]
    assert result["read-button"]["focus"]["text"] == DECK["B08.read"]
    assert result["selected"]["selection"]["type"] == "pair"
    assert not result["selected"]["injected"]
    rows = result["selected"]["rows"]
    assert any("<script>" in row["text"] for row in rows)
    assert any(anchor["text"] == "bank" and anchor["href"] == "#record:bank"
               for row in rows for anchor in row["anchors"])
