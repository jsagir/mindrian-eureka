"""Tests for the pair classes and the carried cells in the hub (Phase 2.2, D-02 and D-03).

Every test builds its own synthetic run folder with `make_run_folder`. The frozen public
fixture under `tests/fixtures/hub_public/` is never read or written here.
"""

from __future__ import annotations

import io
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from hub_support import make_run_folder
from mindrian_eureka.hub.contracts import ENGINE_UNUSUAL, ENGINE_WORDING
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.hub.writer import HubRequest, build_hub
from mindrian_eureka.run.console import Console
from mindrian_eureka.run.contracts import (
    OUTCOME_LICENSED,
    OUTCOME_OPEN,
    PAIR_CLASSES,
    RunError,
)
from mindrian_eureka.run.output import OUTPUT_CORPUS, OUTPUT_UNUSUAL, OUTPUT_WORDING
from test_hub_reader import edit_json, rewrite

REPO = Path(__file__).resolve().parents[1]
HUB = REPO / "src" / "mindrian_eureka" / "hub"
CLASS_WORDS = ("Open next to licensed", "Both open", "Both licensed")
PAIR_FILES = (OUTPUT_UNUSUAL, OUTPUT_WORDING)


def edit_records(folder: Path, change: Callable[[dict[str, Any]], None]) -> None:
    """Change every record line of the corpus file and fix its hash in the manifest."""
    lines = (folder / OUTPUT_CORPUS).read_text(encoding="utf-8").split("\n")
    out: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        item = json.loads(line)
        if item.get("record_type") == "record":
            change(item)
        out.append(json.dumps(item, sort_keys=True, ensure_ascii=False, separators=(",", ":")))
    rewrite(folder, OUTPUT_CORPUS, ("\n".join(out) + "\n").encode("utf-8"))


def pair_class_counts(folder: Path) -> dict[str, int]:
    totals: dict[str, int] = {}
    for name in PAIR_FILES:
        doc = json.loads((folder / name).read_text(encoding="utf-8"))
        for key, value in doc["counts"]["pair_classes"].items():
            totals[key] = totals.get(key, 0) + value
    return totals


def hub_html(run: Path, out: Path) -> str:
    build_hub(HubRequest(run, out), Console(stderr=io.StringIO()))
    return (out / "hub.html").read_text(encoding="utf-8")


@pytest.fixture
def plain(tmp_path: Path) -> Path:
    return make_run_folder(tmp_path, name="plain")


@pytest.fixture
def classed(tmp_path: Path) -> Path:
    return make_run_folder(tmp_path, name="classed", pair_classes=True)


# --- 1. a run without classes -----------------------------------------------


def test_plain_run_loads_without_classes_or_extras(plain: Path) -> None:
    run = load_run(plain)
    for engine in (ENGINE_UNUSUAL, ENGINE_WORDING):
        for pair in run.engines[engine].pairs:
            assert pair.pair_class is None
            assert pair.left_extras == {}
            assert pair.right_extras == {}
    for record in run.records:
        assert record.outcome_class is None
        assert record.extras == {}
    payload = build_payload(run)
    assert "has_pair_classes" not in payload
    for item in payload["pairs"]:
        assert "pair_class" not in item
        assert "left_extras" not in item
        assert "right_extras" not in item


# --- 2. a run with classes --------------------------------------------------


def test_classed_run_loads_classes_and_extras(classed: Path) -> None:
    run = load_run(classed)
    by_id = {record.id: record for record in run.records}
    for record in run.records:
        assert record.outcome_class in {OUTCOME_LICENSED, OUTCOME_OPEN}
    for engine in (ENGINE_UNUSUAL, ENGINE_WORDING):
        assert run.engines[engine].pairs
        for pair in run.engines[engine].pairs:
            assert pair.pair_class in PAIR_CLASSES
            assert pair.left_extras == by_id[pair.left_id].extras
            assert pair.right_extras == by_id[pair.right_id].extras
    for name in PAIR_FILES:
        doc = json.loads((classed / name).read_text(encoding="utf-8"))
        assert sum(doc["counts"]["pair_classes"].values()) == doc["counts"]["pairs"]


# --- 3. the payload ---------------------------------------------------------


def test_classed_payload_carries_classes_and_the_flag(classed: Path) -> None:
    payload = build_payload(load_run(classed))
    assert payload["has_pair_classes"] is True
    counts: dict[str, int] = {}
    for item in payload["pairs"]:
        assert item["pair_class"] in PAIR_CLASSES
        assert isinstance(item["left_extras"], dict)
        assert isinstance(item["right_extras"], dict)
        counts[item["pair_class"]] = counts.get(item["pair_class"], 0) + 1
    assert counts == pair_class_counts(classed)


# --- 4. refusal without echo ------------------------------------------------


def test_unknown_pair_class_is_refused_without_echo(plain: Path) -> None:
    edit_json(plain, OUTPUT_UNUSUAL, lambda doc: doc["pairs"][0].update(pair_class="zzodd"))
    with pytest.raises(RunError) as caught:
        load_run(plain)
    assert "pair class" in caught.value.message
    assert "zzodd" not in caught.value.message


def test_extras_that_are_not_a_mapping_are_refused_without_echo(plain: Path) -> None:
    edit_json(plain, OUTPUT_UNUSUAL, lambda doc: doc["pairs"][0].update(left_extras="zzsecret"))
    with pytest.raises(RunError) as caught:
        load_run(plain)
    assert "extras" in caught.value.message
    assert "zzsecret" not in caught.value.message


def test_extras_with_a_value_that_is_not_text_are_refused(plain: Path) -> None:
    edit_json(plain, OUTPUT_UNUSUAL, lambda doc: doc["pairs"][0].update(left_extras={"k": 5}))
    with pytest.raises(RunError) as caught:
        load_run(plain)
    assert "extras" in caught.value.message


def test_unknown_outcome_class_is_refused_without_echo(plain: Path) -> None:
    edit_records(plain, lambda item: item.update(outcome_class="zzodd"))
    with pytest.raises(RunError) as caught:
        load_run(plain)
    assert "outcome class" in caught.value.message
    assert "zzodd" not in caught.value.message


# --- 5. acceptance ----------------------------------------------------------


def test_known_pair_class_is_accepted(plain: Path) -> None:
    edit_json(plain, OUTPUT_UNUSUAL, lambda doc: doc["pairs"][0].update(pair_class="cross"))
    assert load_run(plain).engines[ENGINE_UNUSUAL].pairs[0].pair_class == "cross"


# --- 6. the server-side page row --------------------------------------------


def test_page_row_shows_the_class_and_the_carried_cells(classed: Path, tmp_path: Path) -> None:
    html = hub_html(classed, tmp_path / "hub-classed")
    class_labels = re.findall(r'class="hub-label hub-label-class">([^<]*)<', html)
    assert class_labels
    assert class_labels[0] in CLASS_WORDS
    assert "status: Active" in html or "status: Inactive- Licensed" in html
    chips = re.findall(r'class="hub-label">([^<]*)<', html)
    assert chips
    assert not [chip for chip in chips if chip.endswith(": ")]
    assert "first_license_or_option_date: <" not in html


def test_page_row_of_a_plain_run_shows_no_class(plain: Path, tmp_path: Path) -> None:
    html = hub_html(plain, tmp_path / "hub-plain")
    for words in CLASS_WORDS:
        assert words not in html
    assert "hub-label-class" not in html
    assert "hub-pair-extras" not in html


# --- 7. static script facts -------------------------------------------------


def test_bank_script_holds_the_class_filter_and_the_chips() -> None:
    bank = (HUB / "assets" / "authored" / "hub-bank.js").read_text(encoding="utf-8")
    for needle in ('"pairClass"', '"P10."', '"B15.legend"', "hub-bank-class", "hub-bank-extras"):
        assert needle in bank
    core = (HUB / "assets" / "authored" / "hub-core.js").read_text(encoding="utf-8")
    assert 'pairClass: "all"' in core


def test_page_declares_the_dynamic_deck_keys() -> None:
    page = (HUB / "page.py").read_text(encoding="utf-8")
    declared = " ".join(
        line.split(":", 1)[1] for line in page.splitlines() if line.startswith("# deck keys:")
    ).split()
    for key in (
        "P10.cross",
        "P10.open_open",
        "P10.licensed_licensed",
        "B15.all",
        "B15.cross",
        "B15.open_open",
        "B15.licensed_licensed",
    ):
        assert key in declared
