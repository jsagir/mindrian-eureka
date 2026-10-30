"""Tests for the clean corpus builder of `eureka run`."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import InputSet
from jsonschema import Draft202012Validator
from mindrian_eureka.run import corpus as corpus_module
from mindrian_eureka.run.contracts import RunError, UsageError, sha256_text
from mindrian_eureka.run.corpus import build_corpus
from mindrian_eureka.run.mapping import (
    MAPPING_JSON_SCHEMA,
    CsvMapping,
    MappingConfig,
    load_mapping_file,
    mapping_from_flags,
)
from mindrian_eureka.run.textclean import html_to_text, looks_like_html

SRC = Path(__file__).resolve().parents[1] / "src"
SECRET = "Quartz lanterns drift beyond the orchard wall"


def body(tag: str) -> str:
    """Return a synthetic body of more than 50 characters that is unique for the tag."""
    return f"Synthetic body about {tag}. It has enough words to pass the short body rule."


def write_md(folder: Path, rel: str, text: str, newline: str = "\n") -> Path:
    path = folder / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.replace("\n", newline).encode("utf-8"))
    return path


def make_folder(base: Path, name: str, count: int = 6, newline: str = "\n") -> Path:
    folder = base / name
    folder.mkdir()
    for index in range(count):
        write_md(folder, f"sec/r{index}.md", f"# Title {index}\n\n{body(str(index))}\n", newline)
    return folder


def tree_hash(folder: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(folder.rglob("*")):
        digest.update(path.relative_to(folder).as_posix().encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


# --- happy path --------------------------------------------------------------


def test_markdown_fixture_gives_32_sorted_records(tmp_inputs: Callable[..., InputSet]) -> None:
    inputs = tmp_inputs("markdown")
    corpus = build_corpus(inputs.folder, mapping=None)
    assert len(corpus.records) == 32
    assert [r.id for r in corpus.records] == inputs.ids
    assert corpus.dropped == ()
    assert corpus.caps_hit == ()
    assert corpus.records_read == 32
    assert corpus.mapping_sha256 is None
    assert len(corpus.input_files) == 32


def test_root_level_file_gets_its_stem_as_id(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    write_md(folder, "b.md", body("b"))
    write_md(folder, "synthetic/a.md", body("a"))
    corpus = build_corpus(folder, mapping=None)
    assert [r.id for r in corpus.records] == ["b", "synthetic/a"]
    assert corpus.records[1].source_ref == "synthetic/a.md"
    assert corpus.records[1].source_file == "synthetic/a.md"
    assert corpus.records[0].text_sha256 == sha256_text(corpus.records[0].text)


def test_digest_formulas(tmp_path: Path) -> None:
    folder = make_folder(tmp_path, "in")
    corpus = build_corpus(folder, mapping=None)
    lines = [f"{r.id}\t{sha256_text(r.model_text)}" for r in corpus.records]
    assert corpus.corpus_digest == sha256_text("\n".join(lines))
    file_lines = [f"{f.path}\t{f.sha256}" for f in corpus.input_files]
    assert file_lines == sorted(file_lines)
    assert corpus.folder_digest == sha256_text("\n".join(file_lines))
    inputs = corpus.manifest_inputs()
    assert set(inputs) == {"files", "mapping_sha256", "folder_digest"}
    assert set(inputs["files"][0]) == {"path", "bytes", "sha256"}
    info = corpus.manifest_corpus()
    assert set(info) == {"records_read", "records_used", "dropped", "corpus_digest", "caps_hit"}
    assert info["records_used"] == 6


# --- titles ------------------------------------------------------------------


def test_title_from_front_matter(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    write_md(folder, "a.md", f'---\ntitle: "Front Title"\nother: x\n---\n# Heading\n\n{body("a")}')
    write_md(folder, "b.md", body("b"))
    record = build_corpus(folder, mapping=None).records[0]
    assert record.title == "Front Title"
    assert record.text.startswith("# Heading")


def test_title_from_heading_removes_the_heading_line(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    write_md(folder, "a.md", f"# My Heading\n\n{body('a')}")
    write_md(folder, "b.md", body("b"))
    record = build_corpus(folder, mapping=None).records[0]
    assert record.title == "My Heading"
    assert "My Heading" not in record.text
    assert record.model_text.startswith("My Heading\n\nSynthetic body")


def test_heading_inside_body_is_kept(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    write_md(folder, "a.md", f"{body('a')}\n\n# Late Heading\n\nMore text here.")
    write_md(folder, "b.md", body("b"))
    record = build_corpus(folder, mapping=None).records[0]
    assert record.title == "Late Heading"
    assert "# Late Heading" in record.text


def test_title_from_file_stem(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    write_md(folder, "my-first_note.md", body("a"))
    write_md(folder, "z.md", body("b"))
    assert build_corpus(folder, mapping=None).records[0].title == "my first note"


# --- determinism -------------------------------------------------------------


@pytest.mark.parametrize("newline", ["\r\n", "\r"])
def test_line_endings_keep_ids_and_corpus_digest(tmp_path: Path, newline: str) -> None:
    lf = build_corpus(make_folder(tmp_path, "lf"), mapping=None)
    other = build_corpus(make_folder(tmp_path, "other", newline=newline), mapping=None)
    assert [r.id for r in lf.records] == [r.id for r in other.records]
    assert lf.corpus_digest == other.corpus_digest
    assert lf.folder_digest != other.folder_digest


@pytest.mark.parametrize("reverse", [False, True])
def test_creation_order_does_not_change_the_corpus(tmp_path: Path, reverse: bool) -> None:
    names = [f"n{i}" for i in range(8)]
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    for name in names:
        write_md(first, f"s/{name}.md", body(name))
    for name in reversed(names) if reverse else names:
        write_md(second, f"s/{name}.md", body(name))
    a = build_corpus(first, mapping=None)
    b = build_corpus(second, mapping=None)
    assert a.manifest_corpus() == b.manifest_corpus()
    assert a.manifest_inputs() == b.manifest_inputs()
    assert a.records == b.records


def test_unicode_form_does_not_change_the_digest(tmp_path: Path) -> None:
    composed = tmp_path / "composed"
    decomposed = tmp_path / "decomposed"
    for folder, word in ((composed, "café"), (decomposed, "café")):
        folder.mkdir()
        write_md(folder, "a.md", f"# {word}\n\n{body(word)}")
        write_md(folder, "b.md", body("b"))
    one = build_corpus(composed, mapping=None)
    two = build_corpus(decomposed, mapping=None)
    assert one.records[0].title == two.records[0].title


# --- drops -------------------------------------------------------------------


def test_short_body_is_dropped_and_listed(tmp_path: Path) -> None:
    folder = make_folder(tmp_path, "in", count=5)
    write_md(folder, "sec/tiny.md", "# Tiny\n\nToo short.")
    corpus = build_corpus(folder, mapping=None)
    assert len(corpus.records) == 5
    assert corpus.records_read == 6
    assert [(d.id, d.reason, d.source_file) for d in corpus.dropped] == [
        ("sec/tiny", "body_under_50_chars", "sec/tiny.md")
    ]
    assert corpus.manifest_corpus()["dropped"][0]["id"] == "sec/tiny"
    assert any("Dropped 1" in w for w in corpus.warnings)


def test_hidden_and_node_modules_are_skipped(tmp_path: Path) -> None:
    folder = make_folder(tmp_path, "in", count=3)
    write_md(folder, ".hidden/x.md", body("x"))
    write_md(folder, ".dot.md", body("dot"))
    write_md(folder, "node_modules/pkg/readme.md", body("pkg"))
    corpus = build_corpus(folder, mapping=None)
    assert len(corpus.records) == 3
    assert all(not f.path.startswith((".", "node_modules")) for f in corpus.input_files)


def test_symlink_outside_the_folder_is_skipped_with_a_warning(tmp_path: Path) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text(body("outside"), encoding="utf-8")
    folder = make_folder(tmp_path, "in", count=3)
    other_dir = tmp_path / "other-dir"
    other_dir.mkdir()
    write_md(other_dir, "inner.md", body("inner"))
    try:
        (folder / "escape.md").symlink_to(outside)
        (folder / "dirlink").symlink_to(other_dir, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks are not available")
    corpus = build_corpus(folder, mapping=None)
    assert len(corpus.records) == 3
    assert any("escape.md" in w for w in corpus.warnings)
    assert any("dirlink" in w for w in corpus.warnings)


def test_symlink_inside_the_folder_is_read(tmp_path: Path) -> None:
    folder = make_folder(tmp_path, "in", count=3)
    try:
        (folder / "alias.md").symlink_to(folder / "sec" / "r0.md")
    except OSError:
        pytest.skip("symlinks are not available")
    corpus = build_corpus(folder, mapping=None)
    assert "alias" in [r.id for r in corpus.records]


# --- stop conditions ---------------------------------------------------------


def test_duplicate_ids_name_both_files(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    write_md(folder, "x.md", body("one"))
    upper = folder / "x.MD"
    upper.write_text(body("two"), encoding="utf-8")
    if len(list(folder.iterdir())) < 2:
        pytest.skip("the file system ignores letter case")
    with pytest.raises(RunError) as info:
        build_corpus(folder, mapping=None)
    assert "x.md" in info.value.message
    assert "x.MD" in info.value.message
    assert info.value.exit_code == 1


@pytest.mark.parametrize("count", [0, 1])
def test_fewer_than_two_usable_records_stop_the_run(tmp_path: Path, count: int) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    for index in range(count):
        write_md(folder, f"r{index}.md", body(str(index)))
    write_md(folder, "tiny.md", "short")
    with pytest.raises(RunError) as info:
        build_corpus(folder, mapping=None)
    assert f"{count} usable" in info.value.message
    assert f"{count + 1} read" in info.value.message
    assert "1 dropped" in info.value.message


@pytest.mark.parametrize("count", [2, 3, 4])
def test_two_to_four_records_give_a_warning(tmp_path: Path, count: int) -> None:
    folder = make_folder(tmp_path, "in", count=count)
    corpus = build_corpus(folder, mapping=None)
    assert any("at least 5 records" in w for w in corpus.warnings)


def test_five_records_give_no_small_corpus_warning(tmp_path: Path) -> None:
    corpus = build_corpus(make_folder(tmp_path, "in", count=5), mapping=None)
    assert not any("at least 5" in w for w in corpus.warnings)


@pytest.mark.parametrize(("count", "cap"), [(9, 5), (6, 5), (12, 2)])
def test_cap_keeps_first_ids_and_records_one_cap_hit(tmp_path: Path, count: int, cap: int) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    for index in range(count):
        write_md(folder, f"r{index:02d}.md", body(str(index)))
    corpus = build_corpus(folder, mapping=None, max_artifacts=cap)
    ids = [f"r{index:02d}" for index in range(count)]
    assert [r.id for r in corpus.records] == ids[:cap]
    assert len(corpus.caps_hit) == 1
    hit = corpus.caps_hit[0]
    assert (hit.name, hit.limit, hit.records_in, hit.records_used) == (
        "max_artifacts",
        cap,
        count,
        cap,
    )
    assert hit.dropped_count == count - cap
    assert hit.dropped_ids_sha256 == sha256_text("\n".join(ids[cap:]))
    assert corpus.manifest_corpus()["caps_hit"][0]["dropped_count"] == count - cap
    assert corpus.manifest_corpus()["records_used"] == cap
    assert any(f"The cap is {cap}" in w for w in corpus.warnings)


def test_no_cap_hit_at_exact_cap(tmp_path: Path) -> None:
    corpus = build_corpus(make_folder(tmp_path, "in", count=5), mapping=None, max_artifacts=5)
    assert corpus.caps_hit == ()


def test_record_over_the_character_limit_names_the_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = make_folder(tmp_path, "in", count=3)
    monkeypatch.setattr(corpus_module, "MAX_RECORD_CHARS", 100)
    write_md(folder, "sec/huge.md", "# Huge\n\n" + "word " * 60)
    with pytest.raises(RunError) as info:
        build_corpus(folder, mapping=None)
    assert "sec/huge" in info.value.message


def test_total_text_over_the_limit_stops_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = make_folder(tmp_path, "in", count=4)
    monkeypatch.setattr(corpus_module, "MAX_TOTAL_TEXT_BYTES", 200)
    with pytest.raises(RunError):
        build_corpus(folder, mapping=None)


def test_input_file_over_the_limit_names_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = make_folder(tmp_path, "in", count=3)
    monkeypatch.setattr(corpus_module, "MAX_INPUT_FILE_BYTES", 50)
    with pytest.raises(RunError) as info:
        build_corpus(folder, mapping=None)
    assert "sec/r0.md" in info.value.message


def test_file_that_is_not_utf8_stops_with_a_fix(tmp_path: Path) -> None:
    folder = make_folder(tmp_path, "in", count=3)
    (folder / "bad.md").write_bytes(b"\xff\xfe\x00bad")
    with pytest.raises(RunError) as info:
        build_corpus(folder, mapping=None)
    assert "bad.md" in info.value.message
    assert info.value.fix == "Save the file as UTF-8"


def test_bad_arguments_raise_usage_error(tmp_path: Path) -> None:
    folder = make_folder(tmp_path, "in", count=3)
    empty = tmp_path / "empty"
    empty.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    (other / "notes.txt").write_text("not a record", encoding="utf-8")
    cases: list[tuple[Path, int]] = [
        (tmp_path / "missing", 10),
        (empty, 10),
        (other, 10),
        (folder, 1),
        (folder, 5001),
    ]
    for path, cap in cases:
        with pytest.raises(UsageError) as info:
            build_corpus(path, mapping=None, max_artifacts=cap)
        assert info.value.exit_code == 2
        assert info.value.fix


def test_error_text_never_holds_record_text(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    write_md(folder, "a.md", f"# T\n\n{SECRET} and more words to pass the length rule easily.")
    write_md(folder, "tiny.md", f"{SECRET}")
    with pytest.raises(RunError) as info:
        build_corpus(folder, mapping=None)
    assert SECRET not in info.value.message
    assert SECRET not in (info.value.fix or "")


# --- read only and imports ---------------------------------------------------


def test_source_folder_is_not_changed(tmp_path: Path) -> None:
    folder = make_folder(tmp_path, "in", count=6)
    write_md(folder, "sec/tiny.md", "short")
    before = tree_hash(folder)
    build_corpus(folder, mapping=None)
    build_corpus(folder, mapping=None, max_artifacts=3)
    assert tree_hash(folder) == before


def test_module_does_not_import_numpy() -> None:
    code = (
        f"import sys; sys.path.insert(0, {str(SRC)!r}); import mindrian_eureka.run.corpus; "
        "bad = [m for m in ('numpy', 'sklearn', 'torch') if m in sys.modules]; "
        "sys.exit(1 if bad else 0)"
    )
    result = subprocess.run([sys.executable, "-I", "-c", code], check=False)
    assert result.returncode == 0


# --- CSV helpers -------------------------------------------------------------

DESC = "A synthetic description with enough words to pass the short body rule."


def write_csv(folder: Path, name: str, rows: list[list[str]], newline: str = "\n") -> Path:
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator=newline).writerows(rows)
    path.write_bytes(buffer.getvalue().encode("utf-8"))
    return path


def simple_rows(count: int = 6) -> list[list[str]]:
    rows = [["case_id", "title", "description", "note"]]
    for index in range(count):
        rows.append([f"c{index}", f"Title {index}", f"{DESC} Row {index}.", f"n{index}"])
    return rows


def flags_mapping(**kwargs: Any) -> MappingConfig:
    base: dict[str, Any] = {
        "id_column": "case_id",
        "title_column": "title",
        "text_columns": ["description"],
        "source_column": None,
        "delimiter": None,
    }
    base.update(kwargs)
    config = mapping_from_flags(**base)
    assert config is not None
    return config


def entry_mapping(entry: dict[str, Any], key: str = "*") -> MappingConfig:
    columns = entry.pop("text_columns")
    config = MappingConfig(
        files={key: CsvMapping(text_columns=tuple(columns), **entry)}, sha256="test"
    )
    return config


# --- CSV ---------------------------------------------------------------------


def test_csv_fixture_through_mapping_file(tmp_inputs: Callable[..., InputSet]) -> None:
    inputs = tmp_inputs("csv")
    assert inputs.mapping_file is not None
    mapping = load_mapping_file(inputs.mapping_file)
    corpus = build_corpus(inputs.folder, mapping=mapping)
    assert [r.id for r in corpus.records] == inputs.ids
    assert corpus.mapping_sha256 == mapping.sha256
    assert corpus.manifest_inputs()["mapping_sha256"] == mapping.sha256
    first = corpus.records[0]
    assert "\n\nRegion: " not in first.text
    assert "state_code: " in first.text
    assert any(name in first.text for name in ("Northern Fictia", "Southern Fictia"))
    assert first.source_ref == f"records.csv#{first.id.split('/', 1)[1]}"
    assert first.source_file == "records.csv"


def test_csv_mapping_file_and_flags_give_equal_corpus(
    tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    inputs = tmp_inputs("csv")
    file_path = tmp_path / "plain-map.json"
    file_path.write_text(
        json.dumps(
            {
                "schema_version": "eureka.run-mapping.v1",
                "files": {
                    "*": {
                        "id_column": "case_id",
                        "title_column": "title",
                        "text_columns": ["description"],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    by_file = build_corpus(inputs.folder, mapping=load_mapping_file(file_path))
    by_flags = build_corpus(inputs.folder, mapping=flags_mapping())
    assert by_file.records == by_flags.records
    assert by_file.manifest_corpus() == by_flags.manifest_corpus()
    assert len(by_file.records) == 32


def test_csv_shuffled_rows_and_crlf_keep_ids_and_digest(tmp_path: Path) -> None:
    rows = simple_rows(8)
    shuffled = [rows[0], *reversed(rows[1:])]
    a = tmp_path / "a"
    b = tmp_path / "b"
    c = tmp_path / "c"
    write_csv(a, "records.csv", rows)
    write_csv(b, "records.csv", shuffled)
    write_csv(c, "records.csv", rows, newline="\r\n")
    one = build_corpus(a, mapping=flags_mapping())
    two = build_corpus(b, mapping=flags_mapping())
    three = build_corpus(c, mapping=flags_mapping())
    ids = [r.id for r in one.records]
    assert ids == [r.id for r in two.records] == [r.id for r in three.records]
    assert one.corpus_digest == two.corpus_digest == three.corpus_digest
    assert one.folder_digest != two.folder_digest
    assert one.folder_digest != three.folder_digest


def test_csv_without_mapping_prints_headers_and_a_valid_skeleton(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    header = ["Case ID", "Title", "Description", "Zip"]
    write_csv(folder, "data/partner.csv", [header, ["1", "t", "d", "z"]])
    with pytest.raises(UsageError) as info:
        build_corpus(folder, mapping=None)
    message = info.value.message
    assert info.value.exit_code == 2
    for name in ("Case ID", "Title", "Description", "Zip"):
        assert name in message
    block = message[message.index("{") :]
    data = json.loads(block)
    assert list(Draft202012Validator(MAPPING_JSON_SCHEMA).iter_errors(data)) == []
    assert data["files"]["data/partner.csv"]["id_column"] == "Case ID"


def test_csv_without_matching_entry_is_unmapped(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "a.csv", simple_rows())
    other = entry_mapping({"text_columns": ["description"]}, key="other.csv")
    with pytest.raises(UsageError):
        build_corpus(folder, mapping=other)


def test_csv_exact_key_wins_over_star(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "a.csv", simple_rows())
    mapping = MappingConfig(
        files={
            "*": CsvMapping(text_columns=("missing",)),
            "a.csv": CsvMapping(text_columns=("description",), id_column="case_id"),
        },
        sha256="x",
    )
    assert len(build_corpus(folder, mapping=mapping).records) == 6


def test_csv_semicolon_file_skeleton_has_delimiter(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    (folder / "s.csv").write_text("id;title;description\n1;t;d\n", encoding="utf-8")
    with pytest.raises(UsageError) as info:
        build_corpus(folder, mapping=None)
    data = json.loads(info.value.message[info.value.message.index("{") :])
    assert data["files"]["s.csv"]["delimiter"] == ";"
    assert "description" in info.value.message


def test_csv_empty_file_is_reported(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    (folder / "e.csv").write_bytes(b"")
    with pytest.raises(UsageError) as info:
        build_corpus(folder, mapping=None)
    assert "empty" in info.value.message
    with pytest.raises(RunError):
        build_corpus(folder, mapping=flags_mapping())


def test_csv_missing_column_lists_available_headers(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "a.csv", simple_rows())
    with pytest.raises(UsageError) as info:
        build_corpus(folder, mapping=flags_mapping(text_columns=["nope", "description"]))
    assert "nope" in info.value.message
    assert "case_id, title, description, note" in info.value.message


def test_csv_duplicate_header_names_raise(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    (folder / "d.csv").write_text("a,a,b\n1,2,3\n", encoding="utf-8")
    with pytest.raises(UsageError) as info:
        mapping = flags_mapping(id_column=None, title_column=None, text_columns=["b"])
        build_corpus(folder, mapping=mapping)
    assert "a" in info.value.message


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Case One!", "Case_One_"),
        ("a/b\\c", "a_b_c"),
        ("keep-this_1.2", "keep-this_1.2"),
        ("  padded  ", "padded"),
    ],
)
def test_csv_id_is_sanitized(tmp_path: Path, raw: str, expected: str) -> None:
    folder = tmp_path / "in"
    rows = simple_rows(5)
    rows[1][0] = raw
    write_csv(folder, "recs.csv", rows)
    corpus = build_corpus(folder, mapping=flags_mapping())
    assert f"recs/{expected}" in [r.id for r in corpus.records]


def test_csv_empty_id_cell_names_file_and_data_row(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    rows = simple_rows(5)
    rows[3][0] = "  "
    write_csv(folder, "recs.csv", rows)
    with pytest.raises(RunError) as info:
        build_corpus(folder, mapping=flags_mapping())
    assert "recs.csv row 3" in info.value.message


@pytest.mark.parametrize("bad", [".", "..", "..."])
def test_csv_dot_only_id_is_refused(tmp_path: Path, bad: str) -> None:
    folder = tmp_path / "in"
    rows = simple_rows(5)
    rows[1][0] = bad
    write_csv(folder, "recs.csv", rows)
    with pytest.raises(RunError):
        build_corpus(folder, mapping=flags_mapping())


def test_csv_duplicate_id_values_collide(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    rows = simple_rows(5)
    rows[2][0] = rows[1][0]
    write_csv(folder, "recs.csv", rows)
    with pytest.raises(RunError) as info:
        build_corpus(folder, mapping=flags_mapping())
    assert "recs/c0" in info.value.message
    assert "row 1" in info.value.message
    assert "row 2" in info.value.message


def test_csv_without_id_column_uses_a_text_hash(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    write_csv(folder, "recs.csv", simple_rows(5))
    mapping = flags_mapping(id_column=None, title_column=None)
    corpus = build_corpus(folder, mapping=mapping)
    for record in corpus.records:
        stem, _, part = record.id.partition("/")
        assert stem == "recs"
        assert re.fullmatch(r"h[0-9a-f]{12}", part)
        assert part == "h" + sha256_text(record.text)[:12]


def test_csv_identical_rows_without_id_column_collide(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    rows = simple_rows(5)
    rows[2] = list(rows[1])
    write_csv(folder, "recs.csv", rows)
    with pytest.raises(RunError) as info:
        build_corpus(folder, mapping=flags_mapping(id_column=None, title_column=None))
    assert "id column" in (info.value.fix or "")


def test_csv_text_assembly_labels_extras_and_empty_cells(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    rows = [
        ["id", "title", "problem", "need", "gap", "region"],
        ["a", "T1", f"{DESC} A.", "Need A text.", "", "1"],
        ["b", "T2", f"{DESC} B.", "", "", ""],
    ]
    write_csv(folder, "recs.csv", rows)
    mapping = entry_mapping(
        {
            "text_columns": ["problem", "need", "gap"],
            "id_column": "id",
            "title_column": "title",
            "labels": {"need": "Stated need", "region": "Region"},
            "extra_fields": ["region"],
            "value_maps": {"region": {"1": "North"}},
        }
    )
    corpus = build_corpus(folder, mapping=mapping)
    first, second = corpus.records
    assert first.text == f"{DESC} A.\n\nStated need:\nNeed A text.\n\nRegion: North"
    assert first.title == "T1"
    assert second.text == f"{DESC} B."


def test_csv_value_map_warning_gives_count_and_capped_examples(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    rows = [["id", "text", "code"]]
    codes = ["1", "2", "x" * 60, "q1", "q2", "q3", "q4", "q5"]
    for index, code in enumerate(codes):
        rows.append([f"r{index}", f"{DESC} {index}.", code])
    write_csv(folder, "recs.csv", rows)
    mapping = entry_mapping(
        {
            "text_columns": ["text"],
            "id_column": "id",
            "extra_fields": ["code"],
            "value_maps": {"code": {"1": "One", "2": "Two"}},
        }
    )
    corpus = build_corpus(folder, mapping=mapping)
    warns = [w for w in corpus.warnings if "value map" in w]
    assert len(warns) == 1
    assert "6 cell(s)" in warns[0]
    examples = warns[0].split("Examples: ")[1].split(", ")
    assert len(examples) == 5
    assert all(len(example) <= 43 for example in examples)
    texts = {r.id: r.text for r in corpus.records}
    assert texts["recs/r0"].endswith("code: One")
    assert texts["recs/r3"].endswith("code: q1")


@pytest.mark.parametrize(
    ("mode", "cell", "expected"),
    [
        ("auto", "x < 5 and y > 2", "x < 5 and y > 2"),
        ("auto", "<p>Fish &amp; chips</p><p>Pie</p>", "Fish & chips\nPie"),
        ("never", "<p>Fish</p>", "<p>Fish</p>"),
        ("always", "x &lt; 5", "x < 5"),
        ("auto", "plain text", "plain text"),
    ],
)
def test_csv_html_modes(tmp_path: Path, mode: str, cell: str, expected: str) -> None:
    folder = tmp_path / "in"
    padding = " " + DESC
    rows = [["id", "text"]] + [[f"r{i}", cell + padding] for i in range(2)]
    write_csv(folder, "recs.csv", rows)
    mapping = entry_mapping({"text_columns": ["text"], "id_column": "id", "html": mode})
    corpus = build_corpus(folder, mapping=mapping)
    assert corpus.records[0].text.startswith(expected)


def test_csv_source_column_and_title(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    rows = [["id", "title", "text", "url"]]
    rows.append(["a", "Alpha", f"{DESC} A.", "https://example.test/a"])
    rows.append(["b", "", f"{DESC} B.", ""])
    write_csv(folder, "recs.csv", rows)
    mapping = flags_mapping(id_column="id", source_column="url", text_columns=["text"])
    corpus = build_corpus(folder, mapping=mapping)
    first, second = corpus.records
    assert (first.title, first.source_ref) == ("Alpha", "https://example.test/a")
    assert (second.title, second.source_ref) == ("", "recs.csv#b")


def test_csv_bom_semicolon_and_quoted_newline(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    folder.mkdir()
    lines = ["id;text"]
    for index in range(4):
        lines.append(f'r{index};"{DESC}\nSecond line {index}."')
    (folder / "s.csv").write_bytes(b"\xef\xbb\xbf" + "\r\n".join(lines).encode("utf-8"))
    mapping = flags_mapping(
        id_column="id", title_column=None, text_columns=["text"], delimiter=";"
    )
    corpus = build_corpus(folder, mapping=mapping)
    assert [r.id for r in corpus.records] == [f"s/r{i}" for i in range(4)]
    assert "\nSecond line 0." in corpus.records[0].text


def test_csv_blank_rows_are_skipped_with_a_warning(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    rows = simple_rows(5)
    rows.insert(2, ["", "", "", ""])
    write_csv(folder, "recs.csv", rows)
    corpus = build_corpus(folder, mapping=flags_mapping())
    assert len(corpus.records) == 5
    assert any("blank row" in w for w in corpus.warnings)


def test_csv_large_cell_is_read_and_field_limit_is_restored(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    rows = simple_rows(5)
    rows[1][2] = "word " * 40_000
    write_csv(folder, "recs.csv", rows)
    before = csv.field_size_limit()
    corpus = build_corpus(folder, mapping=flags_mapping())
    assert csv.field_size_limit() == before
    assert max(len(r.text) for r in corpus.records) == 199_999


def test_csv_cell_above_the_record_limit_names_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "in"
    rows = simple_rows(5)
    rows[1][2] = "word " * 400
    write_csv(folder, "big.csv", rows)
    monkeypatch.setattr(corpus_module, "MAX_RECORD_CHARS", 1000)
    before = csv.field_size_limit()
    with pytest.raises(RunError) as info:
        build_corpus(folder, mapping=flags_mapping())
    assert "big.csv" in info.value.message
    assert csv.field_size_limit() == before


def test_csv_error_text_never_holds_cell_text(tmp_path: Path) -> None:
    folder = tmp_path / "in"
    rows = simple_rows(5)
    rows[2][0] = ""
    rows[2][2] = SECRET
    write_csv(folder, "recs.csv", rows)
    with pytest.raises(RunError) as info:
        build_corpus(folder, mapping=flags_mapping())
    assert SECRET not in info.value.message


def test_csv_source_folder_is_not_changed(tmp_inputs: Callable[..., InputSet]) -> None:
    inputs = tmp_inputs("csv")
    before = tree_hash(inputs.folder)
    build_corpus(inputs.folder, mapping=flags_mapping())
    assert tree_hash(inputs.folder) == before


def test_csv_and_markdown_in_one_folder(tmp_path: Path) -> None:
    folder = make_folder(tmp_path, "in", count=3)
    write_csv(folder, "table.csv", simple_rows(3))
    corpus = build_corpus(folder, mapping=flags_mapping())
    ids = [r.id for r in corpus.records]
    assert ids == sorted(ids)
    assert "table/c0" in ids and "sec/r0" in ids
    assert len(corpus.records) == 6


# --- textclean ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("<p>Fish &amp; chips</p><p>Pie</p>", "Fish & chips\nPie"),
        ("<script>var a = 1;</script><p>Keep</p>", "Keep"),
        ("<style>p {color: red}</style>Text", "Text"),
        ("<head><title>Skip</title></head><body>Body</body>", "Body"),
        ("one<br>two<br/>three", "one\ntwo\nthree"),
        ("<ul><li>a</li><li>b</li></ul>", "a\nb"),
        ("a   b\t\tc", "a b c"),
        ("<p>a</p>\n\n\n\n<p>b</p>", "a\n\nb"),
        ("x &lt; 5 &nbsp;&gt; 2", "x < 5 > 2"),
        ("", ""),
    ],
)
def test_html_to_text(value: str, expected: str) -> None:
    assert html_to_text(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("<p>x</p>", True),
        ("</div>", True),
        ("<!-- c -->", True),
        ("x < 5", False),
        ("a<3 and b", False),
        ("plain", False),
        ("", False),
    ],
)
def test_looks_like_html(value: str, expected: bool) -> None:
    assert looks_like_html(value) is expected
