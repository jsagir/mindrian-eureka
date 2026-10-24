"""Exercise the actual local hub core in Chromium and Firefox."""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pytest
from hub_browser_support import file_url, require_browser, run_scenario
from hub_support import make_run_folder
from mindrian_eureka.hub.deck import DECK, fill
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.hub.writer import HubRequest, build_hub
from mindrian_eureka.run.console import Console

CHECKS = Path(__file__).parent / "hub_browser/checks"
STATE = str(CHECKS / "core-state.js")
METRICS = str(CHECKS / "core-metrics.js")
API = {"data", "copy", "fmt", "el", "state", "registerView", "registerPanel", "select",
       "clearSelection", "setFilter", "on", "emit", "go", "search", "motion", "index",
       "notice", "start"}


def built_hub(tmp_path: Path, **run_options) -> Path:
    run = make_run_folder(tmp_path, **run_options)
    out = tmp_path / "hub"
    build_hub(HubRequest(run, out), Console(stderr=io.StringIO()))
    return out


def evaluate(name: str, **args):
    return {"kind": "eval", "file": STATE, "as": name, "args": args}


def scenario(out: Path, browser: str = "chromium", *, steps=None, clean=True, **options):
    result = run_scenario({"browser": browser, "url": file_url(out / "hub.html"),
                           "steps": steps or [evaluate("state")], **options})
    assert result["ok"], result["stepErrors"]
    assert result["blockedRequests"] == []
    assert result["pageErrors"] == []
    assert result["cspViolations"] == []
    if clean:
        assert not [message for message in result["console"] if message["type"] == "error"]
    return result["results"]


def test_widths_and_metrics(tmp_path: Path) -> None:
    require_browser()
    out = built_hub(tmp_path, hostile=True)
    steps = []
    for width in (320, 390, 768, 1280, 1600):
        steps.extend([{"kind": "setViewport", "width": width, "height": 900},
                      {"kind": "eval", "file": METRICS, "as": str(width)}])
    result = scenario(out, steps=steps)
    print(json.dumps(result, sort_keys=True))
    for width, measured in result.items():
        assert measured["small"] == [], (width, measured)
        assert measured["minimum"] >= 13
        assert measured["targets"] == []
        assert measured["scrollWidth"] <= measured["innerWidth"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_views_filters_selection_and_api(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path)
    steps = [evaluate("initial", safety=True),
             {"kind": "click", "selector": '#hub-nav a[href="#graph"]'},
             evaluate("graph", filter={"name": "engine", "value": "wording_and_meaning"}),
             evaluate("catalogue", go="catalogue", select={"type": "record", "id": "doc003"}),
             evaluate("bank", go="bank")]
    result = scenario(out, browser, steps=steps)
    initial = result["initial"]
    assert API <= set(initial["api"])
    assert all(initial["safe"].values()) and len(initial["safe"]) == 7
    assert initial["search"][0] == "doc003"
    assert initial["h1Count"] == 1 and initial["face"].endswith("theo-handover.svg")
    assert initial["status"] == DECK["G06"]
    assert initial["duration"] == 760
    graph = result["graph"]
    assert graph["h1"] == DECK["Gr01"] and graph["title"] == DECK["G01.graph"]
    assert graph["focus"]["id"] == "hub-title" and graph["active"] == ["graph"]
    assert graph["current"] == "#graph"
    assert result["bank"]["state"]["filters"]["engine"] == "wording_and_meaning"
    assert result["bank"]["state"]["selection"] == {"type": "record", "id": "doc003"}


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_hash_routes_and_hostile_data(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path, hostile=True)
    steps = [evaluate("bank-id", hash="record:bank"), evaluate("proto", hash="__proto__"),
             evaluate("record", hash="doc003"), evaluate("unknown", hash="nosuchrecord")]
    result = scenario(out, browser, steps=steps)
    assert result["bank-id"]["state"]["selection"]["id"] == "bank"
    assert result["proto"]["state"]["selection"]["id"] == "__proto__"
    assert result["record"]["state"]["selection"]["id"] == "doc003"
    assert result["unknown"]["notice"] == fill(DECK["E05"], ID="nosuchrecord")
    assert result["unknown"]["active"] == result["record"]["active"]
    assert result["unknown"]["state"]["selection"] == result["record"]["state"]["selection"]
    assert not result["unknown"]["injected"]
    sources = result["unknown"]["scripts"]
    assert sources and all(source and (out / source).is_file() for source in sources)
    assert len(sources) == len(set(sources))


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
@pytest.mark.parametrize("missing", ["data", "copy", "schema"])
def test_missing_files_and_schema(tmp_path: Path, browser: str, missing: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path)
    if missing == "schema":
        path = out / "hub-data.js"
        path.write_text(path.read_text().replace("eureka.hub-data.v1", "eureka.hub-data.v0"))
    else:
        (out / f"hub-{missing}.js").unlink()
    state = scenario(out, browser, clean=missing == "schema")["state"]
    if missing == "copy":
        assert state["bankRows"] and state["catalogueRows"]
    else:
        assert DECK["E01" if missing == "data" else "E03"] in state["status"]
        assert state["face"].endswith("theo-limit.svg")
    assert state["active"] == ["bank", "graph", "catalogue"]


def test_counts_footer_and_data_check(tmp_path: Path) -> None:
    require_browser()
    out = built_hub(tmp_path, copies=3, empty_text=1)
    payload = build_payload(load_run(tmp_path / "run"))
    state = scenario(out)["state"]
    counts = payload["counts"]
    assert state["counts"] == [counts["records"], counts["pairs"]["unusual_pairs"],
                               counts["pairs"]["wording_and_meaning"], counts["hoods"]]
    expected = fill(DECK["G14"], version=payload["tool_version"],
                    fingerprint=payload["run_fingerprint"][:12], records=counts["records"])
    assert state["footer"] == DECK["G05"] + expected
    assert fill(DECK["D02.same"], n=payload["data_check"]["identical_records"]) in state["check"]
    assert fill(DECK["D02.empty"], n=1) in state["check"]
    empty = built_hub(tmp_path / "empty", zero_pairs=True)
    state = scenario(empty)["state"]
    assert state["face"].endswith("theo-limit.svg")
    assert state["status"] == DECK["B10"] + " " + DECK["B11"]


# Camera moves are short (760 ms), user-triggered, and instant under prefers-reduced-motion.
# They are not substantial or ambient motion, so the hub has no in-page motion setting.
# Status: book silent, proposed segment; the owner may require one control (Instant camera)
# at the plan 17 brand stop.
@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_reduced_motion(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    state = scenario(built_hub(tmp_path), browser, reducedMotion=True)["state"]
    assert state["reduced"] and state["duration"] == 0
    assert state["animations"] == 0 and state["motionControls"] == []


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_no_javascript_lists_remain(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    steps = [{"kind": "dom", "as": "dom"}]
    for selector in ("#bank", "#graph", "#catalogue", "#bank-list", "#graph-list",
                     "#catalogue-list", "noscript"):
        steps.append({"kind": "visible", "selector": selector, "as": selector})
    result = scenario(built_hub(tmp_path), browser, javaScript=False, steps=steps)
    assert 'class="no-js"' in result["dom"]
    assert DECK["G12"] in result["dom"]
    assert all(result[selector] for selector in result if selector != "dom")



def test_focus_order(tmp_path: Path) -> None:
    require_browser()
    steps = []
    for index in range(8):
        steps.extend([{"kind": "press", "key": "Tab"}, evaluate(str(index))])
    result = scenario(built_hub(tmp_path), steps=steps)
    assert result["0"]["focus"]["class"] == "hub-skip"
    assert result["1"]["focus"]["tag"] == "A"
    for index in range(8):
        assert result[str(index)]["outline"] == "3px"
    assert [result[str(index)]["focus"]["href"] for index in (1, 2, 3)] == [
        "#bank", "#graph", "#catalogue"
    ]


def test_shell_copy_is_sourced(tmp_path: Path) -> None:
    require_browser()
    out = built_hub(tmp_path)
    payload = build_payload(load_run(tmp_path / "run"))
    state = scenario(out)["state"]
    allowed = {text for text in DECK.values() if "{" not in text}
    allowed.update(str(value) for value in state["counts"])
    check = payload["data_check"]
    allowed.update({
        fill(DECK["D02.same"], n=check["identical_records"]),
        fill(DECK["D02.empty"], n=check["no_text_records"]),
        fill(DECK["D02.removed"], n=check["removed_count"], reason=check["removed_text"])
        .replace(". .", "."),
        fill(DECK["G14"], version=payload["tool_version"],
             fingerprint=payload["run_fingerprint"][:12], records=payload["counts"]["records"]),
    })
    assert set(state["shellWords"]) <= allowed
    for text in state["shellWords"]:
        assert not any(char in text for char in (chr(0x2013), chr(0x2014)))
        assert not re.search(r"\b(R[S]|H[S]I)\b", text)


@pytest.mark.parametrize("fragment", ["nosuchrecord", "%not-encoded"])
def test_initial_unknown_hash_keeps_bank(tmp_path: Path, fragment: str) -> None:
    require_browser()
    out = built_hub(tmp_path)
    state = scenario(out, url=file_url(out / "hub.html", fragment))["state"]
    assert state["active"] == ["bank"]
    assert state["state"]["selection"] is None
    assert state["notice"] == fill(DECK["E05"], ID=fragment)


def test_extensions_and_clear_restore_focus(tmp_path: Path) -> None:
    require_browser()
    state = scenario(built_hub(tmp_path), steps=[evaluate("state", extension=True)])["state"]
    extension = state["extension"]
    assert extension["renders"] == 1
    assert extension["shown"] == extension["hidden"] == 1
    assert extension["events"] == ["select", "clear"]
    assert extension["emptySearch"] == [] and extension["exactSearch"][0] == "doc003"
    assert state["state"]["selection"] is None and not state["state"]["panelOpen"]
    assert state["focus"]["href"] == "#bank"
