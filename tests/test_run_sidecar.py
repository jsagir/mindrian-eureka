"""Tests for the case-number text side-car of `eureka run` (Phase 2.2, plan 02).

Synthetic rows C00001 to C00012 only. No person, no company, no real case number.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from collections.abc import Iterator
from io import StringIO
from pathlib import Path
from typing import Any

import pytest
from mindrian_eureka.cli import main
from mindrian_eureka.run.command import build_run_request, register_commands
from mindrian_eureka.run.console import Console
from mindrian_eureka.run.contracts import (
    MAPPING_SCHEMA,
    RunError,
    UsageError,
    normalize_text,
    sha256_bytes,
    sha256_text,
)
from mindrian_eureka.run.corpus import TextSidecar, build_corpus, load_text_sidecar
from mindrian_eureka.run.manifest import sha256_file
from mindrian_eureka.run.mapping import MappingConfig, load_mapping_file
from mindrian_eureka.run.output import corpus_lines
from mindrian_eureka.run.pipeline import RunRequest, run_pipeline

DESC = "A synthetic description with enough words to pass the short body rule."
HEADERS = ["case_number", "title", "text_a"]
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
LONG_SIDECAR = (
    "A synthetic catalog text about {topic}. It holds enough words to pass the short "
    "body rule on its own."
)
COVERAGE_KEYS = {"records_total", "own_text_ok", "filled_from_sidecar", "still_thin"}
SIDECAR_KEYS = {"sha256", "bytes", "records", "matched", "unmatched"}


# --- Helpers ----------------------------------------------------------------


def write_csv(folder: Path, name: str, rows: list[list[str]]) -> Path:
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerows(rows)
    path.write_bytes(buffer.getvalue().encode("utf-8"))
    return path


def case(index: int) -> str:
    return f"C{index:05d}"


def long_text(index: int) -> str:
    return f"{DESC} Row {index} is about {TOPICS[(index - 1) % len(TOPICS)]}."


def short_text(index: int) -> str:
    return f"Short row {index}."


def rows(count: int, long_up_to: int) -> list[list[str]]:
    out = [HEADERS]
    for index in range(1, count + 1):
        text = long_text(index) if index <= long_up_to else short_text(index)
        out.append([case(index), f"Synthetic title {index}", text])
    return out


def write_mapping(path: Path) -> MappingConfig:
    entry: dict[str, Any] = {
        "id_column": "case_number",
        "title_column": "title",
        "text_columns": ["text_a"],
    }
    path.write_text(
        json.dumps({"schema_version": MAPPING_SCHEMA, "files": {"*": entry}}), encoding="utf-8"
    )
    return load_mapping_file(path)


def write_sidecar_csv(path: Path, entries: dict[str, str]) -> Path:
    return write_csv(path.parent, path.name, [["case_number", "text"], *entries.items()])


def six_row_sidecar(topic_index: int = 4) -> dict[str, str]:
    return {
        case(4): LONG_SIDECAR.format(topic=TOPICS[topic_index - 1]),
        case(5): "Tiny.",
        "C99999": LONG_SIDECAR.format(topic=TOPICS[5]),
    }


def suffix(record_id: str) -> str:
    return record_id.split("/", 1)[1]


def quiet_console() -> Console:
    return Console(quiet=True, no_color=True, stdout=StringIO(), stderr=StringIO())


def parse(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="eureka")
    register_commands(parser.add_subparsers(dest="command", required=True))
    return parser.parse_args(argv)


def strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


# --- Loader -----------------------------------------------------------------


def test_csv_sidecar_loads_first_column_as_id_and_text_column(tmp_path: Path) -> None:
    path = tmp_path / "sidecar.csv"
    write_csv(
        tmp_path,
        "sidecar.csv",
        [
            ["case_number", "note", "text"],
            [" C00001 ", "x", "  Alpha text.\r\nSecond line.  "],
            ["C00002", "y", "Beta text."],
        ],
    )
    loaded = load_text_sidecar(path)
    assert isinstance(loaded, TextSidecar)
    assert loaded.entries == {
        "C00001": normalize_text("  Alpha text.\r\nSecond line.  "),
        "C00002": "Beta text.",
    }
    assert loaded.entries["C00001"] == "Alpha text.\nSecond line."
    assert loaded.sha256 == sha256_bytes(path.read_bytes())
    assert loaded.bytes == len(path.read_bytes())
    assert loaded.records == 2 == len(loaded.entries)
    assert loaded.id_header == "case_number"
    assert loaded.skipped == 0


def test_json_sidecar_loads_an_object_of_strings(tmp_path: Path) -> None:
    path = tmp_path / "sidecar.json"
    raw = json.dumps({"C00001": " Alpha text. ", "C00002": "Beta\r\ntext."}).encode("utf-8")
    path.write_bytes(raw)
    loaded = load_text_sidecar(path)
    assert loaded.entries == {"C00001": "Alpha text.", "C00002": "Beta\ntext."}
    assert loaded.sha256 == sha256_bytes(raw)
    assert loaded.bytes == len(raw)
    assert loaded.records == 2


def test_csv_sidecar_without_text_column_is_refused(tmp_path: Path) -> None:
    path = write_csv(tmp_path, "sidecar.csv", [["case_number", "body"], ["C00001", "Alpha."]])
    with pytest.raises(UsageError) as info:
        load_text_sidecar(path)
    assert "text" in info.value.message
    assert info.value.exit_code == 2
    assert info.value.fix


@pytest.mark.parametrize(
    "document",
    [["C00001", "Alpha."], {"C00001": 1}, {"C00001": {"text": "Alpha."}}, "Alpha."],
)
def test_json_sidecar_that_is_not_an_object_of_strings_is_refused(
    tmp_path: Path, document: Any
) -> None:
    path = tmp_path / "sidecar.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(UsageError) as info:
        load_text_sidecar(path)
    assert "sidecar.json" in info.value.message
    assert "Alpha." not in info.value.message
    assert info.value.fix


def test_other_suffix_is_refused_with_a_fix(tmp_path: Path) -> None:
    path = tmp_path / "sidecar.txt"
    path.write_text("C00001\tAlpha.\n", encoding="utf-8")
    with pytest.raises(UsageError) as info:
        load_text_sidecar(path)
    assert "sidecar.txt" in info.value.message
    assert info.value.fix


def test_duplicate_ids_are_refused_with_a_count_only(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "sidecar.csv",
        [
            ["case_number", "text"],
            ["C00001", "Alpha one."],
            ["C00002", "Beta."],
            ["C00001", "Alpha two."],
            ["C00002", "Beta two."],
        ],
    )
    with pytest.raises(RunError) as info:
        load_text_sidecar(path)
    assert "2" in info.value.message
    assert "C00001" not in info.value.message
    assert "Alpha" not in info.value.message


def test_blank_id_or_blank_text_rows_are_skipped_and_counted(tmp_path: Path) -> None:
    path = write_csv(
        tmp_path,
        "sidecar.csv",
        [
            ["case_number", "text"],
            ["C00001", "Alpha."],
            ["", "No id."],
            ["C00003", "   "],
            ["C00004", "Delta."],
        ],
    )
    loaded = load_text_sidecar(path)
    assert loaded.entries == {"C00001": "Alpha.", "C00004": "Delta."}
    assert loaded.records == 2
    assert loaded.skipped == 2


# --- Join -------------------------------------------------------------------


def test_sidecar_fills_thin_records_and_counts_coverage(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "recs.csv", rows(6, 3))
    mapping = write_mapping(tmp_path / "map.json")
    sidecar = write_sidecar_csv(tmp_path / "sidecar.csv", six_row_sidecar())
    corpus = build_corpus(folder, mapping=mapping, text_sidecar=sidecar)
    by_id = {suffix(record.id): record for record in corpus.records}
    assert set(by_id) == {case(1), case(2), case(3), case(4)}
    filled = by_id[case(4)]
    own = normalize_text(short_text(4))
    expected = own + "\n\n" + normalize_text(six_row_sidecar()[case(4)])
    assert filled.text == expected
    assert filled.text.startswith(own)
    assert filled.text_source == "sidecar"
    assert filled.text_sha256 == sha256_text(filled.text)
    for index in (1, 2, 3):
        assert by_id[case(index)].text_source is None
        assert by_id[case(index)].text == normalize_text(long_text(index))
    assert corpus.text_coverage == {
        "records_total": 6,
        "own_text_ok": 3,
        "filled_from_sidecar": 1,
        "still_thin": 2,
    }
    loaded = load_text_sidecar(sidecar)
    assert corpus.manifest_inputs()["text_sidecar"] == {
        "sha256": loaded.sha256,
        "bytes": loaded.bytes,
        "records": 3,
        "matched": 2,
        "unmatched": 1,
    }
    assert corpus.manifest_corpus()["text_coverage"] == corpus.text_coverage
    assert any("1 side-car id(s) matched no record" in text for text in corpus.warnings)
    assert "C99999" not in "\n".join(corpus.warnings)
    assert sorted(suffix(item.id) for item in corpus.dropped) == [case(5), case(6)]
    assert all(item.reason == "body_under_50_chars" for item in corpus.dropped)
    assert corpus.records_read == 6


def test_sidecar_inside_the_input_folder_is_not_ingested(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "recs.csv", rows(6, 3))
    mapping = write_mapping(tmp_path / "map.json")
    inside = write_sidecar_csv(folder / "sidecar.csv", six_row_sidecar())
    outside = write_sidecar_csv(tmp_path / "sidecar.csv", six_row_sidecar())
    with_inside = build_corpus(folder, mapping=mapping, text_sidecar=inside)
    assert [item.path for item in with_inside.input_files] == ["recs.csv"]
    (folder / "sidecar.csv").unlink()
    with_outside = build_corpus(folder, mapping=mapping, text_sidecar=outside)
    assert len(with_inside.records) == len(with_outside.records) == 4
    assert with_inside.text_coverage == with_outside.text_coverage
    assert with_inside.corpus_digest == with_outside.corpus_digest


def test_sidecar_with_a_markdown_only_folder_joins_nothing(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    for index in range(1, 4):
        (folder / f"note-{index}.md").write_text(
            f"# Note {index}\n\n{long_text(index)}\n", encoding="utf-8"
        )
    sidecar = write_sidecar_csv(tmp_path / "sidecar.csv", six_row_sidecar())
    corpus = build_corpus(folder, mapping=None, text_sidecar=sidecar)
    assert len(corpus.records) == 3
    assert all(record.text_source is None for record in corpus.records)
    assert "The side-car matched no record. The input holds no CSV record id." in corpus.warnings
    assert corpus.text_coverage == {
        "records_total": 3,
        "own_text_ok": 3,
        "filled_from_sidecar": 0,
        "still_thin": 0,
    }
    assert corpus.manifest_inputs()["text_sidecar"]["matched"] == 0
    assert corpus.manifest_inputs()["text_sidecar"]["unmatched"] == 3


def test_without_a_sidecar_nothing_new_is_written(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "recs.csv", rows(6, 3))
    mapping = write_mapping(tmp_path / "map.json")
    corpus = build_corpus(folder, mapping=mapping)
    assert corpus.text_coverage is None
    assert corpus.text_sidecar is None
    assert "text_sidecar" not in corpus.manifest_inputs()
    assert "text_coverage" not in corpus.manifest_corpus()
    assert all(record.text_source is None for record in corpus.records)
    assert b"text_source" not in corpus_lines(corpus.records)
    assert len(corpus.records) == 3


# --- CLI --------------------------------------------------------------------


def test_text_sidecar_flag_sets_the_request(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "recs.csv", rows(6, 3))
    mapping = tmp_path / "map.json"
    write_mapping(mapping)
    sidecar = write_sidecar_csv(tmp_path / "sidecar.csv", six_row_sidecar())
    argv = [
        "run",
        str(folder),
        "--out",
        str(tmp_path / "out"),
        "--mapping",
        str(mapping),
        "--text-sidecar",
        str(sidecar),
    ]
    request = build_run_request(parse(argv), argv)
    assert request.text_sidecar == Path(str(sidecar))
    assert request.mapping is not None


def test_text_sidecar_without_mapping_is_a_usage_error(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "recs.csv", rows(6, 3))
    sidecar = write_sidecar_csv(tmp_path / "sidecar.csv", six_row_sidecar())
    argv = ["run", str(folder), "--out", str(tmp_path / "out"), "--text-sidecar", str(sidecar)]
    with pytest.raises(UsageError) as info:
        build_run_request(parse(argv), argv)
    assert info.value.exit_code == 2
    assert info.value.fix
    assert "--mapping" in info.value.fix or "mapping" in info.value.fix


def test_run_help_names_the_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["run", "--help"])
    assert caught.value.code == 0
    assert "--text-sidecar" in capsys.readouterr().out


def test_missing_sidecar_path_is_a_usage_error(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "recs.csv", rows(6, 3))
    mapping = write_mapping(tmp_path / "map.json")
    missing = tmp_path / "no-such-sidecar.csv"
    request = RunRequest(
        input_dir=folder,
        out_dir=tmp_path / "out",
        mapping=mapping,
        text_sidecar=missing,
        dry_run=True,
    )
    with pytest.raises(UsageError) as info:
        run_pipeline(request, quiet_console())
    assert "no-such-sidecar.csv" in info.value.message
    assert str(tmp_path) not in info.value.message
    assert info.value.fix


# --- Pipeline ---------------------------------------------------------------


@pytest.fixture
def env(isolated_env: Path, stub_encoders: None) -> Path:
    return isolated_env


def _twelve_with_sidecar(tmp_path: Path) -> tuple[Path, MappingConfig, Path]:
    folder = tmp_path / "in"
    write_csv(folder, "recs.csv", rows(12, 9))
    mapping = write_mapping(tmp_path / "map.json")
    sidecar = write_sidecar_csv(
        tmp_path / "sidecar.csv",
        {
            case(10): LONG_SIDECAR.format(topic=TOPICS[9]),
            case(11): LONG_SIDECAR.format(topic=TOPICS[10]),
            "C99999": LONG_SIDECAR.format(topic=TOPICS[5]),
        },
    )
    return folder, mapping, sidecar


def test_pipeline_with_a_sidecar_reports_coverage_and_hash(
    env: Path, fake_model_dir: Path, tmp_path: Path
) -> None:
    folder, mapping, sidecar = _twelve_with_sidecar(tmp_path)
    out = tmp_path / "out"
    request = RunRequest(
        input_dir=folder,
        out_dir=out,
        mapping=mapping,
        model_path=fake_model_dir,
        top_k=30,
        text_sidecar=sidecar,
    )
    summary = run_pipeline(request, quiet_console())
    assert summary.records_used == 11
    assert summary.text_coverage == {
        "records_total": 12,
        "own_text_ok": 9,
        "filled_from_sidecar": 2,
        "still_thin": 1,
    }
    coverage_lines = [
        line for line in summary.lines().split("\n") if line.startswith("Text coverage:")
    ]
    assert len(coverage_lines) == 1
    assert coverage_lines[0] == (
        "Text coverage: 12 records, 9 with own text, 2 filled from the side-car, "
        "1 still thin and dropped"
    )
    counts = summary.to_json_dict()["counts"]["text_coverage"]
    assert set(counts) == COVERAGE_KEYS
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    recorded = manifest["inputs"]["text_sidecar"]
    assert set(recorded) == SIDECAR_KEYS
    assert recorded["sha256"] == sha256_file(sidecar)
    assert recorded["records"] == 3
    assert recorded["matched"] == 2
    assert recorded["unmatched"] == 1
    assert manifest["corpus"]["text_coverage"] == summary.text_coverage
    assert [item["path"] for item in manifest["inputs"]["files"]] == ["recs.csv"]
    lines = (out / "corpus" / "records.jsonl").read_text(encoding="utf-8").split("\n")[1:-1]
    filled = [line for line in lines if '"text_source":"sidecar"' in line]
    assert len(filled) == 2
    assert all('"text_source"' not in line for line in lines if line not in filled)
    for text in strings(manifest):
        assert not text.startswith("/"), text
        assert str(tmp_path) not in text
        assert str(env) not in text


def test_dry_run_with_a_sidecar_prints_the_coverage_line(env: Path, tmp_path: Path) -> None:
    folder, mapping, sidecar = _twelve_with_sidecar(tmp_path)
    request = RunRequest(
        input_dir=folder,
        out_dir=tmp_path / "out",
        mapping=mapping,
        text_sidecar=sidecar,
        dry_run=True,
    )
    summary = run_pipeline(request, quiet_console())
    assert summary.dry_run is True
    assert summary.text_coverage is not None
    assert "Text coverage: 12 records, 9 with own text" in summary.lines()
    assert set(summary.to_json_dict()["counts"]["text_coverage"]) == COVERAGE_KEYS
    assert not (tmp_path / "out").exists()


def test_pipeline_without_a_sidecar_writes_no_coverage(
    env: Path, fake_model_dir: Path, tmp_path: Path
) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "recs.csv", rows(12, 12))
    mapping = write_mapping(tmp_path / "map.json")
    out = tmp_path / "out"
    request = RunRequest(
        input_dir=folder, out_dir=out, mapping=mapping, model_path=fake_model_dir, top_k=30
    )
    summary = run_pipeline(request, quiet_console())
    assert summary.text_coverage is None
    assert "Text coverage:" not in summary.lines()
    assert "text_coverage" not in summary.to_json_dict()["counts"]
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert "text_sidecar" not in manifest["inputs"]
    assert "text_coverage" not in manifest["corpus"]
    assert "text_source" not in (out / "corpus" / "records.jsonl").read_text(encoding="utf-8")
