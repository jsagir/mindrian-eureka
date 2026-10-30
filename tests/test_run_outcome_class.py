"""Tests for the outcome class, the carried cells and the pair classes (Phase 2.2, plan 01).

Synthetic rows C00001 to C00012 only. No person, no company, no real case number.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from mindrian_eureka.run import project
from mindrian_eureka.run.console import Console
from mindrian_eureka.run.contracts import (
    MAPPING_SCHEMA,
    OUTCOME_LICENSED,
    OUTCOME_OPEN,
    PAIR_CLASSES,
    UNUSUAL_PAIRS_NAME,
    WORDING_AND_MEANING_NAME,
    Record,
)
from mindrian_eureka.run.corpus import build_corpus
from mindrian_eureka.run.mapping import MappingConfig, load_mapping_file
from mindrian_eureka.run.pipeline import RunRequest, run_pipeline
from mindrian_eureka.run.project import attach_pair_classes

DESC = "A synthetic description with enough words to pass the short body rule."
HEADERS = [
    "case_number",
    "title",
    "text_a",
    "licensed_to_jh_startup",
    "licensed_externally",
    "licenses",
    "options",
    "had_corporate_research",
    "status",
    "first_license_or_option_date",
]
CARRY = ["licensed_to_jh_startup", "licenses", "status", "first_license_or_option_date"]
RULE = {
    "licensed_when_any": [
        {"column": "licensed_to_jh_startup", "equals": "Y"},
        {"column": "licensed_externally", "equals": "Y"},
        {"column": "licenses", "greater_than": 0},
        {"column": "options", "greater_than": 0},
        {"column": "had_corporate_research", "equals": "Y"},
        {"column": "status", "equals": "Inactive- Licensed"},
    ]
}
STRICT_PAIR_KEYS = {"rank", "pair_id", "left", "right", "scores", "reading", "label"}
MARKDOWN_HEADER = "| Rank | Left record | Right record | Wording | Meaning | Rank score | Reading |"
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


def write_csv(folder: Path, name: str, rows: list[list[str]]) -> Path:
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    path.write_bytes(buffer.getvalue().encode("utf-8"))
    return path


def base_row(index: int) -> dict[str, str]:
    case = f"C{index:05d}"
    return {
        "case_number": case,
        "title": f"Synthetic title {index}",
        "text_a": f"{DESC} Row {index} is about {TOPICS[(index - 1) % len(TOPICS)]}.",
        "licensed_to_jh_startup": "N",
        "licensed_externally": "N",
        "licenses": "0",
        "options": "0",
        "had_corporate_research": "N",
        "status": "Active",
        "first_license_or_option_date": "",
    }


def twelve_rows() -> list[list[str]]:
    overrides: dict[int, dict[str, str]] = {
        1: {"licensed_to_jh_startup": "Y", "first_license_or_option_date": "2020-01-15"},
        2: {"licensed_externally": " y ", "first_license_or_option_date": "2019-06-02"},
        3: {"licenses": "2", "first_license_or_option_date": "2018-11-30"},
        4: {"options": "1", "first_license_or_option_date": "2021-03-09"},
        5: {"had_corporate_research": "Y", "first_license_or_option_date": "2017-08-21"},
        6: {"status": "Inactive- Licensed", "first_license_or_option_date": "2016-02-14"},
        7: {"licensed_to_jh_startup": "N"},
        8: {"licensed_externally": ""},
        9: {"licenses": "0"},
        10: {"licenses": "abc"},
        11: {"had_corporate_research": "n"},
        12: {"status": "Active"},
    }
    rows = [HEADERS]
    for index in range(1, 13):
        row = base_row(index)
        row.update(overrides[index])
        rows.append([row[name] for name in HEADERS])
    return rows


def write_mapping(path: Path, *, with_rule: bool) -> MappingConfig:
    entry: dict[str, Any] = {
        "id_column": "case_number",
        "title_column": "title",
        "text_columns": ["text_a"],
    }
    if with_rule:
        entry["outcome_rule"] = RULE
        entry["carry_columns"] = CARRY
    path.write_text(
        json.dumps({"schema_version": MAPPING_SCHEMA, "files": {"*": entry}}), encoding="utf-8"
    )
    return load_mapping_file(path)


def suffix(record: Record) -> str:
    return record.id.split("/", 1)[1]


def _record(record_id: str, outcome_class: str | None = None, **extras: str) -> Record:
    text = f"Body of {record_id}."
    return Record(
        id=record_id,
        title=f"Title {record_id}",
        text=text,
        source_ref=f"{record_id}.md",
        source_file=f"{record_id}.md",
        text_sha256=hashlib.sha256(text.encode()).hexdigest(),
        outcome_class=outcome_class,
        extras=dict(extras),
    )


def _unusual_item(left: str, right: str, rank: int, structural: float, semantic: float) -> dict:
    signed = semantic - structural
    return {
        "id": f"rs-pair-{left}{right}",
        "kind": "cross_domain_opportunity_pair",
        "rank": rank,
        "payload": {
            "left": {"artifact_id": left, "title": "engine title", "source_ref": "engine ref"},
            "right": {"artifact_id": right, "title": "engine title", "source_ref": "engine ref"},
            "structural_similarity": structural,
            "semantic_similarity": semantic,
            "signed_difference": signed,
            "disagreement": abs(signed),
            "method_signals": {"bm25_similarity": 0.12, "dense_z": 1.5},
            "direction": "structural_transfer",
        },
    }


def _unusual_result() -> dict[str, Any]:
    return {
        "outputs": [
            _unusual_item("a", "b", 1, 0.20, 0.80),
            _unusual_item("c", "a", 2, 0.70, 0.30),
            _unusual_item("b", "c", 3, 0.50, 0.50),
        ]
    }


def _projected(records: list[Record]) -> dict[str, Any]:
    return project.project_unusual_pairs(
        _unusual_result(), records, settings={"top_k": 3}, top_k=3, notes=[]
    )


def quiet_console() -> Console:
    return Console(quiet=True, no_color=True, stdout=StringIO(), stderr=StringIO())


# --- Rule evaluation --------------------------------------------------------


def test_rule_classifies_every_row_and_carries_the_trimmed_cells(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "recs.csv", twelve_rows())
    mapping = write_mapping(tmp_path / "map.json", with_rule=True)
    corpus = build_corpus(folder, mapping=mapping)
    by_id = {suffix(record): record for record in corpus.records}
    assert len(by_id) == 12
    for index in range(1, 7):
        assert by_id[f"C{index:05d}"].outcome_class == OUTCOME_LICENSED, index
    for index in range(7, 13):
        assert by_id[f"C{index:05d}"].outcome_class == OUTCOME_OPEN, index
    assert by_id["C00001"].extras == {
        "licensed_to_jh_startup": "Y",
        "licenses": "0",
        "status": "Active",
        "first_license_or_option_date": "2020-01-15",
    }
    assert by_id["C00002"].extras["licensed_to_jh_startup"] == "N"
    assert by_id["C00003"].extras["licenses"] == "2"
    assert by_id["C00006"].extras["status"] == "Inactive- Licensed"
    assert by_id["C00010"].extras["licenses"] == "abc"
    assert by_id["C00012"].extras["first_license_or_option_date"] == ""
    assert set(by_id["C00001"].extras) == set(CARRY)
    assert corpus.outcome_classes == {"licensed": 6, "open": 6}
    assert corpus.manifest_corpus()["outcome_classes"] == {"licensed": 6, "open": 6}
    for record in corpus.records:
        assert record.text_source is None
        assert "licensed_to_jh_startup" not in record.text


def test_non_numeric_count_cell_gives_one_warning_without_the_cell_text(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "recs.csv", twelve_rows())
    mapping = write_mapping(tmp_path / "map.json", with_rule=True)
    corpus = build_corpus(folder, mapping=mapping)
    hits = [text for text in corpus.warnings if "not whole numbers" in text]
    assert len(hits) == 1
    warning = hits[0]
    assert "licenses" in warning
    assert "1 cell" in warning
    assert "abc" not in warning
    assert "recs.csv" in warning
    assert not [text for text in corpus.warnings if "pair is possible" in text]


def test_rule_without_a_rule_leaves_records_plain(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "recs.csv", twelve_rows())
    mapping = write_mapping(tmp_path / "map.json", with_rule=False)
    corpus = build_corpus(folder, mapping=mapping)
    assert corpus.outcome_classes is None
    assert "outcome_classes" not in corpus.manifest_corpus()
    for record in corpus.records:
        assert record.outcome_class is None
        assert record.extras == {}


def test_missing_rule_or_carry_column_fails_loud(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    rows = [row[:9] for row in twelve_rows()]
    write_csv(folder, "recs.csv", rows)
    mapping = write_mapping(tmp_path / "map.json", with_rule=True)
    with pytest.raises(Exception) as info:
        build_corpus(folder, mapping=mapping)
    assert "first_license_or_option_date" in str(info.value)


# --- Class-size honesty -----------------------------------------------------


def _three_rows(licensed_count: int) -> list[list[str]]:
    rows = [HEADERS]
    for index in range(1, 4):
        row = base_row(index)
        if index <= licensed_count:
            row["licensed_to_jh_startup"] = "Y"
        rows.append([row[name] for name in HEADERS])
    return rows


def test_class_size_warning_when_every_record_is_open(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "recs.csv", _three_rows(0))
    mapping = write_mapping(tmp_path / "map.json", with_rule=True)
    corpus = build_corpus(folder, mapping=mapping)
    assert corpus.outcome_classes == {"licensed": 0, "open": 3}
    joined = "\n".join(corpus.warnings)
    assert "licensed_licensed" in joined
    assert "cross" in joined
    assert "open_open" not in joined
    assert any("holds 0 record" in text and "licensed_licensed" in text for text in corpus.warnings)
    assert any(text.startswith("No cross pair is possible") for text in corpus.warnings)


def test_class_size_warning_when_one_record_is_licensed(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "recs.csv", _three_rows(1))
    mapping = write_mapping(tmp_path / "map.json", with_rule=True)
    corpus = build_corpus(folder, mapping=mapping)
    assert corpus.outcome_classes == {"licensed": 1, "open": 2}
    hits = [text for text in corpus.warnings if "licensed_licensed" in text]
    assert len(hits) == 1
    assert "holds 1 record" in hits[0]
    assert not any("cross" in text for text in corpus.warnings)
    assert not any("open_open" in text for text in corpus.warnings)


def test_mixed_corpus_drops_the_classes_with_a_warning(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "recs.csv", _three_rows(2))
    (folder / "note.md").write_text(f"# A note\n\n{DESC} It is Markdown.\n", encoding="utf-8")
    mapping = write_mapping(tmp_path / "map.json", with_rule=True)
    corpus = build_corpus(folder, mapping=mapping)
    assert corpus.outcome_classes is None
    assert all(record.outcome_class is None for record in corpus.records)
    assert any("without an outcome class" in text for text in corpus.warnings)
    assert not any("pair is possible" in text for text in corpus.warnings)
    doc = attach_pair_classes({"counts": {"pairs": 0}, "pairs": []}, list(corpus.records))
    assert "pair_classes" not in doc["counts"]


# --- attach_pair_classes ----------------------------------------------------


def test_attach_pair_classes_adds_exactly_three_keys_and_counts() -> None:
    records = [
        _record("a", OUTCOME_OPEN, licenses="0"),
        _record("b", OUTCOME_LICENSED, licenses="2"),
        _record("c", OUTCOME_LICENSED, licenses="1"),
    ]
    doc = _projected(records)
    out = attach_pair_classes(doc, records)
    assert out is doc
    classes = {record.id: record.outcome_class for record in records}
    for pair in out["pairs"]:
        assert set(pair) == STRICT_PAIR_KEYS | {"pair_class", "left_extras", "right_extras"}
        assert pair["pair_class"] in PAIR_CLASSES
        left, right = classes[pair["left"]["id"]], classes[pair["right"]["id"]]
        expected = "cross" if left != right else f"{left}_{left}"
        assert pair["pair_class"] == expected
        left_record = records[ord(pair["left"]["id"]) - ord("a")]
        assert pair["left_extras"] == {"licenses": left_record.extras["licenses"]}
        assert set(pair["left"]) == {"id", "title", "source_ref"}
    counts = out["counts"]["pair_classes"]
    assert set(counts) == {"cross", "open_open", "licensed_licensed"}
    assert counts == {"cross": 2, "open_open": 0, "licensed_licensed": 1}
    assert sum(counts.values()) == out["counts"]["pairs"]
    json.dumps(out)


def test_attach_pair_classes_is_a_no_op_without_classes() -> None:
    records = [_record("a"), _record("b"), _record("c")]
    doc = _projected(records)
    before = json.dumps(doc, sort_keys=True)
    out = attach_pair_classes(doc, records)
    assert out is doc
    assert json.dumps(out, sort_keys=True) == before
    for pair in out["pairs"]:
        assert set(pair) == STRICT_PAIR_KEYS
    assert "pair_classes" not in out["counts"]


def test_attach_pair_classes_refuses_a_mixed_record_set() -> None:
    records = [_record("a", OUTCOME_OPEN), _record("b"), _record("c", OUTCOME_LICENSED)]
    doc = _projected(records)
    with pytest.raises(ValueError) as info:
        attach_pair_classes(doc, records)
    assert "without an outcome class" in str(info.value)


def test_attach_pair_classes_refuses_an_unknown_record_id() -> None:
    records = [
        _record("a", OUTCOME_OPEN),
        _record("b", OUTCOME_LICENSED),
        _record("c", OUTCOME_OPEN),
    ]
    doc = _projected(records)
    doc["pairs"][0]["left"]["id"] = "zz"
    with pytest.raises(ValueError):
        attach_pair_classes(doc, records)


# --- Pipeline ---------------------------------------------------------------


@pytest.fixture
def env(isolated_env: Path, stub_encoders: None) -> Path:
    return isolated_env


def _run(folder: Path, out: Path, mapping: MappingConfig, model: Path) -> Any:
    request = RunRequest(input_dir=folder, out_dir=out, mapping=mapping, model_path=model, top_k=30)
    return run_pipeline(request, quiet_console())


def test_pipeline_with_the_rule_classes_every_pair(
    env: Path, fake_model_dir: Path, tmp_path: Path
) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "recs.csv", twelve_rows())
    mapping = write_mapping(tmp_path / "map.json", with_rule=True)
    out = tmp_path / "out"
    summary = _run(folder, out, mapping, fake_model_dir)
    assert summary.unusual_pairs > 0
    assert summary.wording_and_meaning_pairs > 0
    for name in ("unusual-pairs.json", "wording-and-meaning-pairs.json"):
        doc = json.loads((out / name).read_text(encoding="utf-8"))
        assert doc["pairs"], name
        for pair in doc["pairs"]:
            assert pair["pair_class"] in PAIR_CLASSES
            assert set(pair["left_extras"]) == set(CARRY)
            assert set(pair["right_extras"]) == set(CARRY)
        counts = doc["counts"]["pair_classes"]
        assert set(counts) == {"cross", "open_open", "licensed_licensed"}
        assert sum(counts.values()) == doc["counts"]["pairs"]
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    run_settings = manifest["settings"]["run"]
    assert len(run_settings["outcome_rules"]["*"]["licensed_when_any"]) == 6
    assert run_settings["carry_columns"]["*"] == CARRY
    assert manifest["corpus"]["outcome_classes"] == {"licensed": 6, "open": 6}
    markdown = (out / "ranked-pairs.md").read_text(encoding="utf-8")
    headers = [line for line in markdown.split("\n") if line.startswith("| Rank |")]
    assert headers and all(line.endswith("| Class |") for line in headers)
    assert "Classes: cross" in markdown
    lines = (out / "corpus" / "records.jsonl").read_text(encoding="utf-8").split("\n")[1:-1]
    for line in lines:
        item = json.loads(line)
        assert item["outcome_class"] in {OUTCOME_LICENSED, OUTCOME_OPEN}
        assert set(item["extras"]) == set(CARRY)
        assert "text_source" not in item
    text = summary.lines()
    class_lines = [line for line in text.split("\n") if " classes: cross " in line]
    assert len(class_lines) == 2
    assert class_lines[0].startswith(UNUSUAL_PAIRS_NAME)
    assert class_lines[1].startswith(WORDING_AND_MEANING_NAME)
    for line in class_lines:
        assert "open_open" in line and "licensed_licensed" in line
    json_counts = summary.to_json_dict()["counts"]["pair_classes"]
    assert set(json_counts) == {"unusual_pairs", "wording_and_meaning"}


def test_pipeline_without_the_rule_writes_no_new_key(
    env: Path, fake_model_dir: Path, tmp_path: Path
) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "recs.csv", twelve_rows())
    mapping = write_mapping(tmp_path / "map.json", with_rule=False)
    out = tmp_path / "out"
    summary = _run(folder, out, mapping, fake_model_dir)
    for name in ("unusual-pairs.json", "wording-and-meaning-pairs.json"):
        doc = json.loads((out / name).read_text(encoding="utf-8"))
        assert doc["pairs"], name
        for pair in doc["pairs"]:
            assert set(pair) == STRICT_PAIR_KEYS
        assert "pair_classes" not in doc["counts"]
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert "outcome_rules" not in manifest["settings"]["run"]
    assert "carry_columns" not in manifest["settings"]["run"]
    assert "outcome_classes" not in manifest["corpus"]
    markdown = (out / "ranked-pairs.md").read_text(encoding="utf-8")
    headers = [line for line in markdown.split("\n") if line.startswith("| Rank |")]
    assert headers == [MARKDOWN_HEADER, MARKDOWN_HEADER]
    assert "Classes:" not in markdown
    for line in (out / "corpus" / "records.jsonl").read_text(encoding="utf-8").split("\n")[1:-1]:
        item = json.loads(line)
        assert "extras" not in item
        assert "outcome_class" not in item
        assert "text_source" not in item
    assert "pair_classes" not in summary.to_json_dict()["counts"]
    assert " classes: cross " not in summary.lines()
