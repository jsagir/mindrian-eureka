"""Scale check of the hub on a synthetic 2,000-record run (Phase 2.2, D-03a).

The run has 40 blank titles, 60 long list cells with `;` and `>` separators, pair classes
and carried cells on every pair. It is built once per module in a temporary folder with
`make_run_folder`; nothing under `tests/fixtures/` is read or written. The browser part
needs Node and the Playwright package: it skips with a reason without them and fails
under `EUREKA_REQUIRE_BROWSER=1`.
"""

from __future__ import annotations

import io
import time
from pathlib import Path

import pytest
from hub_browser_support import require_browser
from hub_scan import scan_for_network
from hub_support import make_run_folder
from mindrian_eureka.hub.contracts import ENGINE_UNUSUAL, ENGINE_WORDING
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.hub.writer import HubRequest, HubSummary, build_hub
from mindrian_eureka.run.console import Console
from test_hub_browser_core import scenario

CHECKS = Path(__file__).parent / "hub_browser/checks"
BANK = str(CHECKS / "bank-state.js")
RECORDS = 2000
PAIRS = 100
BLANK_TITLES = 40
LIST_CELLS = 60


def build_scale_run(tmp_path: Path) -> tuple[Path, Path, HubSummary, float]:
    """Build the synthetic run and its hub. Return the run, the hub, the summary and seconds."""
    run = make_run_folder(
        tmp_path,
        name="scale",
        n_records=RECORDS,
        pairs_per_engine=PAIRS,
        blank_titles=BLANK_TITLES,
        list_cells=LIST_CELLS,
        pair_classes=True,
        clusters=12,
    )
    out = tmp_path / "hub"
    started = time.monotonic()
    summary = build_hub(HubRequest(run, out), Console(stderr=io.StringIO()))
    seconds = time.monotonic() - started
    print(f"scale check: hub build of {RECORDS} records took {seconds:.2f} s")
    return run, out, summary, seconds


@pytest.fixture(scope="module")
def scale(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path, HubSummary, float]:
    return build_scale_run(tmp_path_factory.mktemp("scale"))


def test_scale_run_builds_and_reloads(scale: tuple[Path, Path, HubSummary, float]) -> None:
    run, out, summary, seconds = scale
    assert seconds > 0.0
    assert summary.records == RECORDS
    assert summary.pairs == {ENGINE_UNUSUAL: PAIRS, ENGINE_WORDING: PAIRS}
    data = load_run(run)
    assert len(data.records) == RECORDS
    assert len(data.engines[ENGINE_UNUSUAL].pairs) == PAIRS
    assert len(data.engines[ENGINE_WORDING].pairs) == PAIRS
    assert sum(1 for record in data.records if record.title == "") == BLANK_TITLES
    with_cells = [record for record in data.records if ";" in record.text and ">" in record.text]
    assert len(with_cells) >= LIST_CELLS
    assert (out / "hub.html").is_file()
    assert scan_for_network(out) == []


def test_scale_run_reads_classes_in_payload(scale: tuple[Path, Path, HubSummary, float]) -> None:
    run = scale[0]
    payload = build_payload(load_run(run))
    assert payload["has_pair_classes"] is True
    counts: dict[str, int] = {}
    for pair in payload["pairs"]:
        counts[pair["pair_class"]] = counts.get(pair["pair_class"], 0) + 1
    assert set(counts) <= {"cross", "open_open", "licensed_licensed"}
    assert sum(counts.values()) == 2 * PAIRS


def test_scale_hub_opens_in_a_browser(scale: tuple[Path, Path, HubSummary, float]) -> None:
    require_browser()
    out = scale[1]
    steps = [
        {"kind": "eval", "file": BANK, "as": "before"},
        {"kind": "click", "selector": "#bank-class-cross"},
        {"kind": "eval", "file": BANK, "as": "after"},
    ]
    result = scenario(out, steps=steps)
    before = len(result["before"]["rows"])
    after = len(result["after"]["rows"])
    assert before > 0
    assert 0 < after <= before
    assert result["after"]["filters"]["pairClass"] == "cross"
    assert result["before"]["violations"] == []
    assert result["after"]["violations"] == []
