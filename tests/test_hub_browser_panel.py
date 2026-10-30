"""Verify panel provenance, positive synthetic Potential eureka, focus and sheet behavior."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from hub_browser_support import require_browser
from hub_support import build_run_folder_with_potential_eureka, make_run_folder
from mindrian_eureka.hub.deck import DECK, fill
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.hub.writer import HubRequest, build_hub
from mindrian_eureka.run.console import Console
from mindrian_eureka.run.contracts import LABEL
from test_hub_browser_core import CHECKS, METRICS, built_hub, scenario

PANEL = str(CHECKS / "panel-state.js")


def check(name: str, **args):
    return {"kind": "eval", "file": PANEL, "as": name, "args": args}


def positive_hub(tmp_path: Path) -> Path:
    run = build_run_folder_with_potential_eureka(tmp_path)
    out = tmp_path / "hub"
    build_hub(HubRequest(run, out), Console(stderr=io.StringIO()))
    return out


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_every_item_provenance_and_negative(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    state = scenario(built_hub(tmp_path, copies=3, empty_text=1, long_text=2), browser,
                     steps=[check("state", audit=True)])["state"]
    assert state["audit"]["checked"] == 30 + 40 + 40
    assert state["audit"]["failures"] == []
    assert state["audit"]["negative"] == ["status"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_positive_eureka_chip_explanation_status_source(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    result = scenario(positive_hub(tmp_path), browser, steps=[check("state", record="bridge")])
    state = result["state"]
    assert state["bridge"]
    assert state["selection"]["id"] == "synthetic-b-000"
    assert state["bridgeChip"] == DECK["P06.eureka"]
    assert state["bridgeStyle"] == {"background": "rgb(242, 194, 0)",
                                    "color": "rgb(17, 17, 17)",
                                    "border": "rgb(17, 17, 17)", "width": "1px"}
    assert LABEL in state["text"] and state["labelValid"]
    assert DECK["P03.why"] in state["headings"]
    assert "2 neighborhoods" in state["why"]
    assert "Neighborhood 1, Neighborhood 2" in state["why"]
    assert "a place to look" in state["why"] and "not a result" in state["why"]
    assert any(link["text"] == DECK["P05.open"] and link["href"] == state["sourceLink"]
               for link in state["anchors"])
    assert "synthetic test fixture" in state["text"].lower()
    assert "not a finding" in state["text"]


def test_field_order_flags_and_text_boundaries(tmp_path: Path) -> None:
    require_browser()
    out = built_hub(tmp_path, copies=3, empty_text=1, long_text=2)
    result = scenario(out, steps=[check("copy", record="copy"), check("clean", record="clean"),
        check("long", record="long"), check("short", record="short"),
        check("surrogate", surrogate=True), check("pair", pair=True)])
    assert DECK["P03.check"] in result["copy"]["headings"]
    assert "Identical text to" in result["copy"]["text"]
    assert DECK["P03.check"] not in result["clean"]["headings"]
    assert DECK["P03.why"] not in result["clean"]["headings"]
    headings = result["long"]["headings"]
    ordered = [DECK["P03.source"], DECK["P03.text"], DECK["P03.hood"]]
    positions = [headings.index(value) for value in ordered]
    assert positions == sorted(positions)
    for name in ("long", "surrogate"):
        state = result[name]
        assert len(state["excerpt"]) == 600
        assert state["excerpt"] + state["rest"] == state["recordText"]
        assert any(item["summary"] == DECK["P05.full"] for item in state["details"])
    assert not result["short"]["rest"]
    assert result["pair"]["headings"][1:5] == [DECK["P03.two"], DECK["P03.scores"],
                                                  DECK["P03.reading"], DECK["P03.meaning"]]
    assert result["pair"]["labelValid"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_focus_close_escape_and_removed_opener(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path)
    result = scenario(out, browser, steps=[
        {"kind": "click", "selector": "#bank-list .hub-bank-read"}, check("open"),
        {"kind": "click", "selector": "#hub-panel-close"}, check("closed"),
        {"kind": "click", "selector": "#bank-list .hub-bank-read"},
        {"kind": "press", "key": "Escape"}, check("escape"),
        check("removed", removeOpener=True)])
    assert result["open"]["focus"]["id"] == "hub-panel-title"
    for name in ("closed", "escape"):
        assert not result[name]["panelOpen"]
        assert result[name]["focus"]["text"] == DECK["B08.read"]
    assert result["removed"]["focus"]["id"] == "hub-title"
    assert not result["removed"]["sheetHeight"]


def test_catalogue_close_hidden_opener_and_no_modal(tmp_path: Path) -> None:
    require_browser()
    out = built_hub(tmp_path)
    result = scenario(out, steps=[
        {"kind": "click", "selector": '#hub-nav a[href="#catalogue"]'},
        {"kind": "click", "selector": "#catalogue-list tbody tr button"}, check("open"),
        {"kind": "click", "selector": "#hub-panel-close"}, check("closed"),
        check("last", record="doc003", focusLast=True),
        {"kind": "press", "key": "Tab"}, check("outside"),
        check("hidden", hideOpener=True)])
    assert not result["open"]["modal"]
    assert result["closed"]["focus"]["text"]
    assert result["closed"]["focus"]["id"] != "hub-title"
    assert not result["outside"]["focus"]["inPanel"]
    assert result["hidden"]["focus"]["id"] == "hub-title"


def test_five_widths_sheet_and_empty_face(tmp_path: Path) -> None:
    require_browser()
    steps = []
    for width in (320, 390, 768, 1280, 1600):
        steps.extend([{"kind": "setViewport", "width": width, "height": 900},
                      check(f"empty-{width}", clear=True),
                      check(str(width), record="long", scrollOpener=width >= 1024),
                      {"kind": "eval", "file": METRICS, "as": f"metrics-{width}"}])
    result = scenario(built_hub(tmp_path, long_text=2), steps=steps)
    for width in (320, 390, 768, 1280, 1600):
        state = result[str(width)]
        assert state["rootOpen"] and state["panelOpen"] and state["position"] == "fixed"
        assert state["live"] == "polite" and state["labelledby"] == "hub-panel-title"
        assert state["scrollWidth"] <= width
        assert result[f"metrics-{width}"]["minimum"] >= 13
        assert result[f"metrics-{width}"]["targets"] == []
        if width < 1024:
            assert state["bounds"]["height"] <= 900 * .62 + 1
            assert state["scrollHeight"] > state["clientHeight"]
            assert state["sheetHeight"] and not result[f"empty-{width}"]["sheetHeight"]
            assert not result[f"empty-{width}"]["faceVisible"]
        else:
            assert state["uncovered"] is True
            assert state["bounds"]["width"] == 400
            assert result[f"empty-{width}"]["faceVisible"]
            assert DECK["P01.heading"] in result[f"empty-{width}"]["text"]


def test_no_hover_open_and_hostile_text(tmp_path: Path) -> None:
    require_browser()
    state = scenario(built_hub(tmp_path, hostile=True), steps=[
        {"kind": "hover", "selector": "#bank-list .hub-bank-read"}, check("hover"),
        check("hostile", record="doc003")])
    assert not state["hover"]["panelOpen"]
    assert "<script>" in state["hostile"]["text"] and not state["hostile"]["injected"]
    assert state["hostile"]["labelValid"]
    assert all(not link["href"].startswith(("http:", "https:", "javascript:", "//"))
               for link in state["hostile"]["anchors"])


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_stage_background_close(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    state = scenario(built_hub(tmp_path), browser, steps=[
        check("open", record="doc003"), check("closed", background=True)])
    assert state["open"]["panelOpen"]
    assert not state["closed"]["panelOpen"]
    assert state["closed"]["selection"] is None


def test_file_source_and_catalogue_links(tmp_path: Path) -> None:
    require_browser()
    run = make_run_folder(tmp_path)
    sources = tmp_path / "sources"
    sources.mkdir()
    for record in load_run(run).records:
        (sources / record.source_file).write_text("Synthetic test source, not a finding.")
    out = tmp_path / "hub"
    build_hub(HubRequest(run, out, sources), Console(stderr=io.StringIO()))
    state = scenario(out, steps=[check("state", record="doc003")])["state"]
    anchors = {link["text"]: link["href"] for link in state["anchors"]}
    assert anchors[DECK["P05.open"]] == "../sources/doc003.md"
    assert anchors[DECK["P05.catalogue"]] == "#doc003"


def test_panel_copy_is_deck_or_source(tmp_path: Path) -> None:
    require_browser()
    out = positive_hub(tmp_path)
    payload = build_payload(load_run(tmp_path / "synthetic-potential-eureka"))
    state = scenario(out, steps=[check("state", record="bridge")])["state"]
    allowed = {value for value in DECK.values() if "{" not in value}
    for record in payload["records"]:
        allowed.update(record[key] for key in ("id", "title", "text", "source_ref", "source_file"))
        allowed.update({record["text"][:600], record["text"][600:],
                        fill(DECK["P03.pairs"], n=len(record["pair_keys"]))})
        if record["bridge"]:
            names = ", ".join(DECK["P03.hood"] + " " + str(n) for n in record["bridge_hoods"])
            allowed.add(fill(DECK["P07"], n=len(record["bridge_hoods"]), list=names))
    for pair in payload["pairs"]:
        allowed.update({pair["reading"], fill(DECK["B08.rank"], n=pair["rank"]),
                        fill(DECK["B08.wording"], x=pair["wording_text"]),
                        fill(DECK["B08.meaning"], y=pair["meaning_text"]),
                        fill(DECK["B08.rank_score"], z=pair["rank_score_text"])})
    for hood in payload["hoods"]:
        allowed.add(fill(DECK["P08"], k=hood["number"], n=hood["size"]))
    for engine in payload["engines"].values():
        allowed.update({engine["name"], engine["score_meaning"]})
    allowed = {value.strip() for value in allowed}
    assert set(state["texts"]) <= allowed
    assert not any(char in state["text"] for char in (chr(0x2013), chr(0x2014)))
