"""Tests for the clean corpus builder of `eureka run`."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import InputSet
from mindrian_eureka.run import corpus as corpus_module
from mindrian_eureka.run.contracts import RunError, UsageError, sha256_text
from mindrian_eureka.run.corpus import build_corpus

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
