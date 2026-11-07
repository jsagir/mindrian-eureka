"""Tests for the `room_sections` mapping block and the cell states (Phase 2.3, plan 01).

Synthetic rows C00001 and up. The sentinel person value and the sentinel money value
must never reach an output file. No real person, no company, no real case number.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from mindrian_eureka.run.contracts import MAPPING_SCHEMA, UsageError
from mindrian_eureka.run.corpus import build_corpus
from mindrian_eureka.run.mapping import MappingConfig, load_mapping_file
from mindrian_eureka.run.output import corpus_lines
from mindrian_eureka.run.pipeline import RunRequest, run_pipeline
from test_run_outcome_class import quiet_console
from test_run_partner_mapping import _write_csv

PERSON = "ZZ Synthetic Person"
MONEY_VALUE = "987654"
DESC = "A synthetic description with enough words to pass the short body rule of the run."
HEADERS = [
    "case_number",
    "title",
    "problem",
    "solution",
    "both_col",
    "topic",
    "status",
    "funding_total",
    "lead_inventor",
]
SECTION_COLUMNS = [
    "problem",
    "topic",
    "solution",
    "both_col",
    "status",
    "funding_total",
    "lead_inventor",
]
SECTIONS: dict[str, Any] = {
    "problem-definition": ["problem", "topic"],
    "solution-design": ["solution", "both_col"],
    "legal-ip": ["status"],
    "financial-model": ["funding_total"],
    "team": ["lead_inventor"],
    "not_in_export": [{"item": "patents", "section": "legal-ip", "source": "SynthDB"}],
}
TOPICS = [
    "pebble sorting by weight",
    "lantern glass that resists frost",
    "a loom that counts its own threads",
    "river maps drawn from bird songs",
    "clay pipes that hum in the wind",
    "a clock that runs on tide pull",
    "paper that folds itself at dawn",
    "salt crystals grown in square moulds",
    "a bridge rope woven from reeds",
    "kites that carry small letters",
    "bread ovens heated by stored sun",
    "wheels that whistle at speed",
]


# --- Helpers ----------------------------------------------------------------


def entry_data(*, with_sections: bool = True, **extra: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id_column": "case_number",
        "title_column": "title",
        "text_columns": ["problem", "solution", "both_col"],
        "extra_fields": ["topic"],
        "labels": {"topic": "Topic"},
        "html": "always",
        "carry_columns": ["both_col", "status"],
    }
    if with_sections:
        entry["room_sections"] = copy.deepcopy(SECTIONS)
    entry.update(extra)
    return entry


def write_mapping(path: Path, entry: dict[str, Any]) -> MappingConfig:
    doc = {"schema_version": MAPPING_SCHEMA, "files": {"*": entry}}
    path.write_text(json.dumps(doc), encoding="utf-8")
    return load_mapping_file(path)


def row_of(index: int, **over: str) -> dict[str, str]:
    row = {
        "case_number": f"C{index:05d}",
        "title": f"Synthetic title {index}",
        "problem": f"{DESC} Row {index} is about {TOPICS[(index - 1) % len(TOPICS)]}.",
        "solution": f"{DESC} Solution {index}.",
        "both_col": "carried text",
        "topic": "a topic",
        "status": "Active",
        "funding_total": MONEY_VALUE,
        "lead_inventor": PERSON,
    }
    row.update(over)
    return row


def csv_rows(rows: list[dict[str, str]]) -> list[list[str]]:
    return [HEADERS, *([row[name] for name in HEADERS] for row in rows)]


def matrix_rows() -> list[dict[str, str]]:
    blank = {
        "solution": "",
        "both_col": "",
        "topic": "",
        "status": "",
        "funding_total": "",
        "lead_inventor": "",
    }
    return [
        row_of(1),
        row_of(2, solution="<p> </p>"),
        row_of(3, **blank),
        row_of(4, problem="   ", topic="", funding_total="5", lead_inventor=""),
        row_of(5, funding_total="  "),
        row_of(6, status=""),
    ]


def twelve_rows() -> list[dict[str, str]]:
    return [row_of(i, solution="" if i % 3 == 0 else f"{DESC} Solution {i}.") for i in range(1, 13)]


def by_suffix(corpus: Any) -> dict[str, Any]:
    return {record.id.split("/", 1)[1]: record for record in corpus.records}


# --- Mapping ----------------------------------------------------------------


def test_mapping_keeps_section_order(tmp_path: Path) -> None:
    from mindrian_eureka.run.mapping import NotInExportItem, RoomSections

    entry = write_mapping(tmp_path / "map.json", entry_data()).files["*"]
    sections = entry.room_sections
    assert isinstance(sections, RoomSections)
    assert sections.sections == (
        ("problem-definition", ("problem", "topic")),
        ("solution-design", ("solution", "both_col")),
        ("legal-ip", ("status",)),
        ("financial-model", ("funding_total",)),
        ("team", ("lead_inventor",)),
    )
    assert len(sections.not_in_export) == 1
    item = sections.not_in_export[0]
    assert isinstance(item, NotInExportItem)
    assert (item.item, item.section, item.source) == ("patents", "legal-ip", "SynthDB")
    assert list(sections.columns) == SECTION_COLUMNS


def test_mapping_without_the_block_has_none(tmp_path: Path) -> None:
    entry = write_mapping(tmp_path / "map.json", entry_data(with_sections=False)).files["*"]
    assert entry.room_sections is None


def test_as_data_shape_and_order(tmp_path: Path) -> None:
    entry = write_mapping(tmp_path / "map.json", entry_data()).files["*"]
    assert entry.room_sections is not None
    assert entry.room_sections.as_data() == {
        "sections": [
            {"section": "problem-definition", "columns": ["problem", "topic"]},
            {"section": "solution-design", "columns": ["solution", "both_col"]},
            {"section": "legal-ip", "columns": ["status"]},
            {"section": "financial-model", "columns": ["funding_total"]},
            {"section": "team", "columns": ["lead_inventor"]},
        ],
        "not_in_export": [{"item": "patents", "section": "legal-ip", "source": "SynthDB"}],
    }


NOT_IN = {"item": "patents", "section": "legal-ip", "source": "SynthDB"}


@pytest.mark.parametrize(
    "block",
    [
        ["problem"],
        {"Problem": ["a"]},
        {"problem_definition": ["a"]},
        {"legal-ip": []},
        {"legal-ip": ["a", "a"]},
        {"legal-ip": ["a"], "team": ["a"]},
        {"legal-ip": ["a"], "not_in_export": [{"item": "patents", "section": "legal-ip"}]},
        {"legal-ip": ["a"], "not_in_export": [{**NOT_IN, "section": "team"}]},
        {"legal-ip": ["a"], "not_in_export": [NOT_IN, {**NOT_IN, "source": "Other"}]},
        {"not_in_export": [NOT_IN]},
    ],
    ids=[
        "block-is-a-list",
        "capital-letter",
        "underscore-name",
        "empty-columns",
        "repeated-column",
        "column-in-two-sections",
        "item-without-source",
        "item-section-unknown",
        "item-repeated",
        "no-section",
    ],
)
def test_room_sections_refusals(tmp_path: Path, block: Any) -> None:
    entry = entry_data(with_sections=False, room_sections=block)
    path = tmp_path / "bad-map.json"
    path.write_text(
        json.dumps({"schema_version": MAPPING_SCHEMA, "files": {"*": entry}}), encoding="utf-8"
    )
    with pytest.raises(UsageError) as info:
        load_mapping_file(path)
    assert "bad-map.json" in info.value.message
    assert info.value.exit_code == 2
    assert info.value.fix


# --- Cell states ------------------------------------------------------------


def test_missing_section_column_fails_loud(tmp_path: Path) -> None:
    mapping = write_mapping(tmp_path / "map.json", entry_data())
    headers = [name for name in HEADERS if name != "lead_inventor"]
    rows = [[row[name] for name in headers] for row in (row_of(1), row_of(2))]
    _write_csv(tmp_path / "in", "recs.csv", [headers, *rows])
    with pytest.raises(UsageError) as info:
        build_corpus(tmp_path / "in", mapping=mapping)
    assert "lead_inventor" in info.value.message
    assert "recs.csv" in info.value.message


def test_cell_states_matrix(tmp_path: Path) -> None:
    mapping = write_mapping(tmp_path / "map.json", entry_data())
    _write_csv(tmp_path / "in", "recs.csv", csv_rows(matrix_rows()))
    corpus = build_corpus(tmp_path / "in", mapping=mapping)
    records = by_suffix(corpus)
    assert len(records) == 6
    full = {
        "problem": "text",
        "topic": "text",
        "solution": "text",
        "both_col": "carried",
        "status": "carried",
        "funding_total": "export_only",
        "lead_inventor": "export_only",
    }
    expected = {
        "C00001": full,
        "C00002": {**full, "solution": "blank"},
        "C00003": {
            "problem": "text",
            "topic": "blank",
            "solution": "blank",
            "both_col": "blank",
            "status": "blank",
            "funding_total": "blank",
            "lead_inventor": "blank",
        },
        "C00004": {**full, "problem": "blank", "topic": "blank", "lead_inventor": "blank"},
        "C00005": {**full, "funding_total": "blank"},
        "C00006": {**full, "status": "blank"},
    }
    for key, states in expected.items():
        cells = records[key].room_cells
        assert dict(cells) == states, key
        assert list(cells) == SECTION_COLUMNS, key


def test_people_and_money_values_never_reach_the_corpus(tmp_path: Path) -> None:
    mapping = write_mapping(tmp_path / "map.json", entry_data())
    _write_csv(tmp_path / "in", "recs.csv", csv_rows(matrix_rows()))
    corpus = build_corpus(tmp_path / "in", mapping=mapping)
    data = corpus_lines(corpus.records)
    assert PERSON.encode() not in data
    assert MONEY_VALUE.encode() not in data
    first = by_suffix(corpus)["C00001"]
    assert first.room_cells["lead_inventor"] == "export_only"
    assert first.room_cells["funding_total"] == "export_only"
    for record in corpus.records:
        assert "lead_inventor" not in record.extras
        assert "funding_total" not in record.extras
        assert PERSON not in record.text
        assert MONEY_VALUE not in record.text


def test_default_run_parity(tmp_path: Path) -> None:
    map_a = write_mapping(tmp_path / "a.json", entry_data(with_sections=False))
    map_b = write_mapping(tmp_path / "b.json", entry_data())
    _write_csv(tmp_path / "in", "recs.csv", csv_rows(matrix_rows()))
    corpus_a = build_corpus(tmp_path / "in", mapping=map_a)
    corpus_b = build_corpus(tmp_path / "in", mapping=map_b)
    assert all(record.room_cells == {} for record in corpus_a.records)
    assert corpus_a.corpus_digest == corpus_b.corpus_digest
    bytes_a = corpus_lines(corpus_a.records)
    assert b"room_cells" not in bytes_a
    lines_a = [json.loads(line) for line in bytes_a.decode("utf-8").split("\n") if line]
    lines_b = [
        json.loads(line)
        for line in corpus_lines(corpus_b.records).decode("utf-8").split("\n")
        if line
    ]
    assert any("room_cells" in item for item in lines_b)
    for item in lines_b:
        item.pop("room_cells", None)
    assert lines_a == lines_b


def test_value_map_misses_are_counted_once(tmp_path: Path) -> None:
    entry = entry_data(value_maps={"solution": {"A": "decoded solution text for a coded cell"}})
    mapping = write_mapping(tmp_path / "map.json", entry)
    rows = [
        row_of(1, solution="A"),
        row_of(2, solution="ZZ"),
        row_of(3, solution="ZZ"),
        row_of(4, solution="YY"),
    ]
    _write_csv(tmp_path / "in", "recs.csv", csv_rows(rows))
    corpus = build_corpus(tmp_path / "in", mapping=mapping)
    notes = [w for w in corpus.warnings if "column solution" in w and "value map" in w]
    assert len(notes) == 1
    assert "3 cell(s)" in notes[0]
    records = by_suffix(corpus)
    assert records["C00002"].room_cells["solution"] == "text"


# --- Pipeline ---------------------------------------------------------------


@pytest.fixture
def env(isolated_env: Path, stub_encoders: None) -> Path:
    return isolated_env


def _run(folder: Path, out: Path, mapping: MappingConfig, model: Path) -> Any:
    request = RunRequest(input_dir=folder, out_dir=out, mapping=mapping, model_path=model, top_k=30)
    return run_pipeline(request, quiet_console())


def test_pipeline_records_the_section_map(env: Path, fake_model_dir: Path, tmp_path: Path) -> None:
    folder = tmp_path / "in"
    _write_csv(folder, "recs.csv", csv_rows(twelve_rows()))
    map_a = write_mapping(tmp_path / "a.json", entry_data(with_sections=False))
    map_b = write_mapping(tmp_path / "b.json", entry_data())
    out_a = tmp_path / "out-a"
    out_b = tmp_path / "out-b"
    _run(folder, out_a, map_a, fake_model_dir)
    _run(folder, out_b, map_b, fake_model_dir)
    manifest_a = json.loads((out_a / "manifest.json").read_text(encoding="utf-8"))
    manifest_b = json.loads((out_b / "manifest.json").read_text(encoding="utf-8"))
    run_b = manifest_b["settings"]["run"]
    expected = map_b.files["*"].room_sections
    assert expected is not None
    assert run_b["room_sections"]["*"] == expected.as_data()
    assert set(run_b) - set(manifest_a["settings"]["run"]) == {"room_sections"}
    lines = (out_b / "corpus" / "records.jsonl").read_text(encoding="utf-8").split("\n")[1:-1]
    assert len(lines) == 12
    for line in lines:
        item = json.loads(line)
        # The corpus file sorts keys. The order of the columns lives in the manifest.
        assert set(item["room_cells"]) == set(SECTION_COLUMNS)
    text_b = (out_b / "corpus" / "records.jsonl").read_bytes()
    assert PERSON.encode() not in text_b
    assert MONEY_VALUE.encode() not in text_b
    for name in ("unusual-pairs.json", "wording-and-meaning-pairs.json"):
        assert b"room_cells" not in (out_b / name).read_bytes()
        assert (out_a / name).read_bytes() == (out_b / name).read_bytes()


def test_pipeline_without_the_block_writes_no_new_key(
    env: Path, fake_model_dir: Path, tmp_path: Path
) -> None:
    folder = tmp_path / "in"
    _write_csv(folder, "recs.csv", csv_rows(twelve_rows()))
    mapping = write_mapping(tmp_path / "map.json", entry_data(with_sections=False))
    out = tmp_path / "out"
    _run(folder, out, mapping, fake_model_dir)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert "room_sections" not in manifest["settings"]["run"]
    for line in (out / "corpus" / "records.jsonl").read_text(encoding="utf-8").split("\n")[1:-1]:
        assert "room_cells" not in json.loads(line)
