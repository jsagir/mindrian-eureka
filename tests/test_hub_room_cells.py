"""Tests for the room-seed keys of the hub reader (Phase 2.3, plan 01).

Every test builds its own synthetic run folder with `make_run_folder`. The frozen public
fixture under `tests/fixtures/hub_public/` is never read or written here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from hub_support import make_run_folder
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.run.contracts import RunError, sha256_bytes
from mindrian_eureka.run.output import OUTPUT_CORPUS
from test_hub_extras import edit_records
from test_hub_reader import read_manifest, write_manifest

CELLS = {"problem": "text", "status": "carried", "funding_total": "export_only", "topic": "blank"}
SECTION_MAP = {
    "*": {
        "sections": [
            {"section": "problem-definition", "columns": ["problem", "topic"]},
            {"section": "financial-model", "columns": ["funding_total"]},
        ],
        "not_in_export": [{"item": "patents", "section": "legal-ip", "source": "SynthDB"}],
    }
}


def with_room_cells(folder: Path) -> None:
    """Add cell states and one text source to the corpus, and the section map to the manifest."""
    seen = {"count": 0}

    def change(item: dict[str, Any]) -> None:
        item["room_cells"] = dict(CELLS)
        if seen["count"] == 0:
            item["text_source"] = "sidecar"
        seen["count"] += 1

    edit_records(folder, change)
    manifest = read_manifest(folder)
    manifest["settings"]["run"]["room_sections"] = SECTION_MAP
    write_manifest(folder, manifest)


@pytest.fixture
def run(tmp_path: Path) -> Path:
    return make_run_folder(tmp_path)


def test_reader_exposes_cells_sections_tool_and_corpus_hash(run: Path) -> None:
    with_room_cells(run)
    data = load_run(run)
    assert data.records[0].room_cells == CELLS
    assert data.records[0].text_source == "sidecar"
    assert data.records[1].text_source is None
    assert data.room_sections == SECTION_MAP
    assert data.tool["name"] == "mindrian-eureka"
    assert data.corpus_sha256 == sha256_bytes((run / OUTPUT_CORPUS).read_bytes())


def test_plain_run_has_empty_defaults(run: Path) -> None:
    data = load_run(run)
    assert all(record.room_cells == {} for record in data.records)
    assert all(record.text_source is None for record in data.records)
    assert data.room_sections == {}
    assert data.tool["name"] == "mindrian-eureka"
    assert len(data.corpus_sha256) == 64


def test_unknown_cell_state_is_refused_without_echo(run: Path) -> None:
    def change(item: dict[str, Any]) -> None:
        item["room_cells"] = {"problem": "zzodd"}

    edit_records(run, change)
    with pytest.raises(RunError) as info:
        load_run(run)
    assert "cell state" in info.value.message
    assert "zzodd" not in info.value.message


def _set(key: str, value: Any) -> Any:
    def change(item: dict[str, Any]) -> None:
        item[key] = value

    return change


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("room_cells", ["problem"]),
        ("room_cells", {"problem": 3}),
        ("text_source", 7),
    ],
    ids=["cells-is-a-list", "state-is-not-text", "text-source-is-a-number"],
)
def test_bad_record_shapes_are_refused(run: Path, key: str, value: Any) -> None:
    edit_records(run, _set(key, value))
    with pytest.raises(RunError):
        load_run(run)


def test_bad_section_map_shape_is_refused(run: Path) -> None:
    manifest = read_manifest(run)
    manifest["settings"]["run"]["room_sections"] = ["not", "a", "mapping"]
    write_manifest(run, manifest)
    with pytest.raises(RunError):
        load_run(run)
