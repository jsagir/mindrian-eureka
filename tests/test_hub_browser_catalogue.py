"""Verify catalogue search, filter, paging, sources and responsive semantics."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from hub_browser_support import require_browser
from hub_support import make_run_folder
from mindrian_eureka.hub.deck import DECK, fill
from mindrian_eureka.hub.writer import HubRequest, build_hub
from mindrian_eureka.run.console import Console
from mindrian_eureka.run.output import canonical_json
from test_hub_browser_core import CHECKS, METRICS, built_hub, scenario

CATALOGUE = str(CHECKS / "catalogue-state.js")


def check(name: str, **args):
    return {"kind": "eval", "file": CATALOGUE, "as": name, "args": args}


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_paging_and_source_links(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    result = scenario(built_hub(tmp_path, n_records=120), browser,
        steps=[check("first"), check("second", more=1), check("all", more=1)])
    for name, count in (("first", 50), ("second", 100), ("all", 120)):
        state = result[name]
        assert len(state["ids"]) == state["rowCount"] == count
        assert state["ids"] == sorted(state["ids"])
        assert state["status"] == fill(DECK["C05"], a=count, b=120)
        assert state["violations"] == []
        assert state["buttonNames"] == [fill(DECK["C07"], ID=value) for value in state["ids"]]
        assert all(
            not link["href"].startswith(("http:", "https:", "//")) for link in state["anchors"]
        )
    assert result["all"]["ids"] == result["all"]["expected"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_search_and_empty_reset(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path, n_records=120)
    steps = [check("id", query="doc01", more=10), check("title", query="channel", more=10),
             check("text", query="synthetic", more=10),
             check("tokens", query="synthetic channel", more=10),
             check("none", query="not-a-present-token"),
             {"kind": "click", "selector": "#catalogue-clear"}, check("reset")]
    result = scenario(out, browser, steps=steps)
    for name in ("id", "title", "text", "tokens"):
        assert result[name]["ids"] == result[name]["expected"]
        assert result[name]["ids"]
        assert result[name]["live"] == "polite"
    assert not result["none"]["ids"]
    assert DECK["C08"] in result["none"]["listText"]
    assert DECK["C09.body"] in result["none"]["listText"]
    assert len(result["reset"]["ids"]) == 50
    assert result["reset"]["filters"]["query"] == ""


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_filters_combine_and_persist(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    result = scenario(built_hub(tmp_path, n_records=120), browser, steps=[check("all"),
        check("file", file="doc003.md", query="doc003", more=10, views=True),
        check("none", file="all", query="", inPair="none", more=10),
        check("some", inPair="some", more=10)])
    options = result["all"]["options"]["file"]
    assert options[0]["text"] == DECK["C04.file.all"]
    assert [option["value"] for option in options[1:]] == [f"doc{n:03d}.md" for n in range(120)]
    assert result["file"]["ids"] == ["doc003"]
    assert result["file"]["filters"]["file"] == "doc003.md"
    for name in ("none", "some"):
        assert result[name]["ids"] == result[name]["expected"]
        assert result[name]["ids"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_selection_keyboard_and_hostile_data(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path, n_records=120, hostile=True, copies=3, empty_text=1)
    result = scenario(out, browser, viewport={"width": 320, "height": 900}, steps=[
        check("initial", more=10),
        {"kind": "click", "selector": "#catalogue-list tbody tr:nth-child(3) button"},
        check("selected"),
        {"kind": "focus", "selector": "#catalogue-list tbody tr:first-child button"},
        {"kind": "press", "selector": "#catalogue-list tbody tr:first-child button",
         "key": "Enter"},
        check("proto"),
        {"kind": "click", "selector": "#catalogue-list tbody tr:nth-child(2) .hub-catalogue-file"},
        check("block")])
    assert result["selected"]["selected"] == result["initial"]["ids"][2]
    assert result["proto"]["selection"] == {"type": "record", "id": "__proto__"}
    assert result["block"]["selected"] == result["initial"]["ids"][1]
    assert not result["initial"]["injected"]
    assert any("<script>" in title for title in result["initial"]["titleTexts"])
    source_links = {link["text"]: link["href"] for link in result["initial"]["anchors"]}
    assert source_links["bank"] == "#record:bank"
    assert "doc119" in result["initial"]["ids"]


def test_five_widths_table_semantics(tmp_path: Path) -> None:
    require_browser()
    steps = []
    for width in (320, 390, 768, 1280, 1600):
        steps.extend([{"kind": "setViewport", "width": width, "height": 900}, check(str(width)),
                      {"kind": "eval", "file": METRICS, "as": f"metrics-{width}"}])
    result = scenario(built_hub(tmp_path, n_records=120), steps=steps)
    for width in (320, 390, 768, 1280, 1600):
        state = result[str(width)]
        assert state["tableCount"] == 1 and state["rowCount"] == 50
        expected_headers = [DECK[f"C06.{key}"] for key in ("id", "title", "file", "pairs")]
        assert state["header"]["names"] == expected_headers
        assert state["header"]["scopes"] == ["col"] * 4
        if width < 768:
            assert set(state["display"].values()) == {"block"}
            assert state["header"]["clip"] == "inset(50%)"
        else:
            assert state["display"] == {"table": "table", "row": "table-row", "cell": "table-cell"}
        if width >= 1024:
            assert state["header"]["position"] == "sticky" and state["header"]["top"] == "64px"
        metric = result[f"metrics-{width}"]
        assert metric["scrollWidth"] <= width
        assert metric["minimum"] >= 13 and metric["targets"] == []


def test_long_source_file_wraps(tmp_path: Path) -> None:
    require_browser()
    run = make_run_folder(tmp_path)
    corpus = run / "corpus/records.jsonl"
    lines = [json.loads(line) for line in corpus.read_text().splitlines()]
    long_name = "synthetic-" + "x" * 120 + ".md"
    lines[1]["source_file"] = long_name
    corpus.write_text("\n".join(json.dumps(line, sort_keys=True) for line in lines) + "\n")
    manifest_path = run / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    for entry in manifest["outputs"]:
        if entry["path"] == "corpus/records.jsonl":
            entry["sha256"] = hashlib.sha256(corpus.read_bytes()).hexdigest()
            entry["bytes"] = corpus.stat().st_size
    manifest_path.write_bytes(canonical_json(manifest))
    out = tmp_path / "hub"
    build_hub(HubRequest(run, out), Console(quiet=True))
    result = scenario(out, viewport={"width": 320, "height": 900}, steps=[check("state"),
        {"kind": "eval", "file": METRICS, "as": "metrics"}])
    assert long_name in result["state"]["sourceTexts"]
    assert result["metrics"]["scrollWidth"] == 320


@pytest.fixture(scope="module")
def large_hub(tmp_path_factory: pytest.TempPathFactory) -> Path:
    require_browser()
    return built_hub(
        tmp_path_factory.mktemp("catalogue-scale"), n_records=3000, pairs_per_engine=200
    )


def test_scale_search(large_hub: Path) -> None:
    require_browser()
    result = scenario(large_hub, steps=[check("initial"), check("search", timedQuery="synthetic")])
    assert result["initial"]["rowCount"] == 50
    assert result["search"]["rowCount"] == 50
    assert len(result["search"]["expected"]) == 3000
    seconds = result["search"]["measured"]["ms"]
    print(f"Search across 3000 records: {seconds:.4f} ms")
    assert seconds < 500
