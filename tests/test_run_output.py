"""Tests for the canonical writer, corpus lines, Markdown report and staged folder."""

from __future__ import annotations

import json
import os
import re
import stat
from pathlib import Path
from typing import Any

import pytest
from mindrian_eureka.run import output
from mindrian_eureka.run.contracts import (
    CORPUS_SCHEMA,
    LABEL,
    MANIFEST_SCHEMA,
    SUMMARY_LINE,
    UNUSUAL_PAIRS_NAME,
    WORDING_AND_MEANING_NAME,
    Record,
    UsageError,
    sha256_text,
)

POSIX = os.name == "posix"
SHORT_CODES = re.compile(r"\b(R[S]|H[S]I)\b")


def _record(record_id: str, title: str = "A title", text: str = "Body text.") -> Record:
    return Record(
        id=record_id,
        title=title,
        text=text,
        source_ref=f"{record_id}.md",
        source_file=f"{record_id}.md",
        text_sha256=sha256_text(text),
    )


def _projected(name: str, meaning: str, pairs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "label": LABEL,
        "engine": {"name": name, "capability_id": "x"},
        "score_meaning": meaning,
        "notes": ["Note one.", "Note | two"],
        "pairs": pairs,
    }


def _pair(left_title: str = "Left", right_title: str = "Right") -> dict[str, Any]:
    return {
        "rank": 1,
        "left": {"id": "a", "title": left_title, "source_ref": "a.md"},
        "right": {"id": "b", "title": right_title, "source_ref": "b.md"},
        "scores": {
            "wording_similarity": 0.123456,
            "meaning_similarity": 0.9,
            "rank_score": 1.0,
        },
        "reading": "Similar meaning, different wording.",
    }


def _write_manifest(folder: Path, schema: str = MANIFEST_SCHEMA) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "manifest.json").write_text(json.dumps({"schema_version": schema}), encoding="utf-8")


# --- canonical_json ---------------------------------------------------------


def test_key_order_independence() -> None:
    first = {"b": 1, "a": {"y": 2, "x": [1, 2]}}
    second = {"a": {"x": [1, 2], "y": 2}, "b": 1}
    assert output.canonical_json(first) == output.canonical_json(second)


def test_lists_are_not_sorted() -> None:
    data = json.loads(output.canonical_json({"v": [3, 1, 2]}))
    assert data["v"] == [3, 1, 2]


@pytest.mark.parametrize(
    ("value", "digits", "expected"),
    [
        (0.1234567891, 6, "0.123457"),
        (0.1234567891, None, "0.1234567891"),
        (0.1234567891, 2, "0.12"),
        (-0.0, 6, "0.0"),
        (-0.0000001, 6, "0.0"),
        (1, 6, "1"),
        (True, 6, "true"),
    ],
)
def test_rounding_and_minus_zero(value: object, digits: int | None, expected: str) -> None:
    text = output.canonical_json({"v": value}, digits=digits).decode("utf-8")
    assert f'"v": {expected}' in text


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_nan_and_infinity_refused_at_depth(bad: float) -> None:
    with pytest.raises(ValueError):
        output.canonical_json({"a": [{"b": (1.0, bad)}]})
    with pytest.raises(ValueError):
        output.canonical_json({"a": bad}, digits=None)


def test_no_bom_no_cr_final_lf_utf8() -> None:
    data = output.canonical_json({"text": "line one\nline two", "name": "caf\u00e9"})
    assert not data.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in data
    assert data.endswith(b"}\n")
    assert "caf\u00e9".encode() in data
    assert json.loads(data)["text"] == "line one\nline two"


# --- corpus_lines -----------------------------------------------------------


def test_corpus_lines_shape() -> None:
    records = [_record("a", text="Line one\nline two"), _record("b", title="Caf\u00e9")]
    data = output.corpus_lines(records)
    assert data.endswith(b"\n")
    assert b"\r" not in data
    lines = data.decode("utf-8").split("\n")[:-1]
    parsed = [json.loads(line) for line in lines]
    assert parsed[0] == {
        "record_type": "header",
        "schema_version": CORPUS_SCHEMA,
        "label": LABEL,
        "record_count": 2,
    }
    assert [item["record_type"] for item in parsed[1:]] == ["record", "record"]
    assert set(parsed[1]) == {
        "record_type",
        "id",
        "title",
        "text",
        "source_ref",
        "source_file",
        "text_sha256",
    }
    assert parsed[1]["text"] == "Line one\nline two"
    assert parsed[1]["text_sha256"] == sha256_text("Line one\nline two")
    assert ": " not in lines[0]


def test_corpus_lines_empty() -> None:
    lines = output.corpus_lines([]).decode("utf-8").split("\n")
    assert json.loads(lines[0])["record_count"] == 0
    assert lines[1] == ""


# --- Markdown ---------------------------------------------------------------


def _markdown(**kwargs: Any) -> str:
    unusual = _projected(UNUSUAL_PAIRS_NAME, "Meaning one.", [_pair(**kwargs)])
    wording = _projected(WORDING_AND_MEANING_NAME, "Meaning two.", [])
    return output.render_ranked_markdown(unusual, wording)


def test_markdown_content() -> None:
    text = _markdown()
    assert text.startswith("# ")
    assert LABEL in text
    assert SUMMARY_LINE in text
    assert f"## {UNUSUAL_PAIRS_NAME}" in text
    assert f"## {WORDING_AND_MEANING_NAME}" in text
    assert text.count(f"Label: {LABEL}") >= 3
    assert "Meaning one." in text
    assert "Meaning two." in text
    assert "- Note one." in text
    header = "| Rank | Left record | Right record | Wording | Meaning | Rank score | Reading |"
    assert header in text
    assert "| 1 | Left (a) | Right (b) | 0.1235 | 0.9000 | 1.0000 | Similar meaning" in text
    assert "\r" not in text
    assert chr(0x2014) not in text
    assert not SHORT_CODES.search(text)
    assert text.endswith("\n")


def test_markdown_escapes_pipe_and_line_breaks() -> None:
    text = _markdown(left_title="One | two\nthree\r\nfour")
    assert "One \\| two three four (a)" in text
    assert "- Note \\| two" in text


def test_markdown_truncates_long_titles() -> None:
    text = _markdown(left_title="x" * 200)
    cell = next(line for line in text.splitlines() if line.startswith("| 1 |")).split(" | ")[1]
    title = cell.rsplit(" (a)", 1)[0]
    assert title.endswith("...")
    assert len(title) == 80


def test_markdown_empty_title_shows_id() -> None:
    text = _markdown(left_title="")
    assert "| a | Right (b) |" in text


def test_markdown_missing_scores_show_dash() -> None:
    pair = _pair()
    pair["scores"] = {}
    unusual = _projected(UNUSUAL_PAIRS_NAME, "m", [pair])
    wording = _projected(WORDING_AND_MEANING_NAME, "m", [])
    text = output.render_ranked_markdown(unusual, wording)
    assert "| - | - | - |" in text


# --- StagedRun --------------------------------------------------------------


def test_write_publish_and_digest(tmp_path: Path) -> None:
    out = tmp_path / "run"
    with output.StagedRun(out) as staged:
        digest = staged.write("corpus/records.jsonl", b"hello\n")
        assert staged.path.parent == tmp_path
        assert not out.exists()
        staged.publish()
    assert digest == output.FileDigest(
        "corpus/records.jsonl",
        "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03",
        6,
    )
    assert digest.as_dict() == {"path": digest.path, "sha256": digest.sha256, "bytes": 6}
    assert (out / "corpus" / "records.jsonl").read_bytes() == b"hello\n"
    assert not any(p.name.startswith(".") for p in tmp_path.iterdir())


@pytest.mark.skipif(not POSIX, reason="POSIX modes")
def test_modes(tmp_path: Path) -> None:
    with output.StagedRun(tmp_path / "run") as staged:
        staged.write("a/b.txt", b"x")
        assert stat.S_IMODE(staged.path.stat().st_mode) == 0o700
        assert stat.S_IMODE((staged.path / "a").stat().st_mode) == 0o700
        assert stat.S_IMODE((staged.path / "a" / "b.txt").stat().st_mode) == 0o600
        staged.publish()


def test_discard_removes_staging(tmp_path: Path) -> None:
    staged = output.StagedRun(tmp_path / "run")
    staged.write("a.txt", b"x")
    staged.discard()
    assert not staged.path.exists()
    assert not (tmp_path / "run").exists()


def test_cleanup_on_exception(tmp_path: Path) -> None:
    out = tmp_path / "run"
    with pytest.raises(RuntimeError), output.StagedRun(out) as staged:
        staged.write("a.txt", b"x")
        raise RuntimeError("boom")
    assert not out.exists()
    assert not [p for p in tmp_path.iterdir() if ".staging-" in p.name]


def test_leaving_without_publish_discards(tmp_path: Path) -> None:
    out = tmp_path / "run"
    with output.StagedRun(out) as staged:
        staged.write("a.txt", b"x")
    assert not out.exists()
    assert not [p for p in tmp_path.iterdir() if ".staging-" in p.name]


def test_stale_staging_folder_is_removed(tmp_path: Path) -> None:
    out = tmp_path / "run"
    stale = tmp_path / f".run.staging-{os.getpid()}"
    stale.mkdir()
    (stale / "old.txt").write_text("old", encoding="utf-8")
    with output.StagedRun(out) as staged:
        assert not (staged.path / "old.txt").exists()


def test_replaces_old_run_folder(tmp_path: Path) -> None:
    out = tmp_path / "run"
    _write_manifest(out)
    (out / "old.txt").write_text("old", encoding="utf-8")
    with output.StagedRun(out) as staged:
        staged.write("new.txt", b"new")
        staged.publish()
    assert (out / "new.txt").read_bytes() == b"new"
    assert not (out / "old.txt").exists()
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".")]


def test_replaces_empty_folder(tmp_path: Path) -> None:
    out = tmp_path / "run"
    out.mkdir()
    with output.StagedRun(out) as staged:
        staged.write("new.txt", b"new")
        staged.publish()
    assert (out / "new.txt").exists()


def test_refuses_foreign_folder(tmp_path: Path) -> None:
    out = tmp_path / "run"
    out.mkdir()
    (out / "mine.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(UsageError, match="not an Eureka run"), output.StagedRun(out) as staged:
        staged.write("new.txt", b"new")
        staged.publish()
    assert (out / "mine.txt").read_text(encoding="utf-8") == "keep"
    assert not (out / "new.txt").exists()
    assert not [p for p in tmp_path.iterdir() if ".staging-" in p.name]


def test_refuses_existing_file(tmp_path: Path) -> None:
    out = tmp_path / "run"
    out.write_text("a file", encoding="utf-8")
    with pytest.raises(UsageError), output.StagedRun(out) as staged:
        staged.publish()
    assert out.read_text(encoding="utf-8") == "a file"


@pytest.mark.parametrize(
    "bad",
    ["", "/abs/file.txt", "../escape.txt", "a/../../escape.txt", "a\\..\\escape.txt", "C:\\x.txt"],
)
def test_path_traversal_refused(tmp_path: Path, bad: str) -> None:
    with output.StagedRun(tmp_path / "run") as staged, pytest.raises(ValueError):
        staged.write(bad, b"x")
    assert not (tmp_path / "escape.txt").exists()


def test_staging_next_to_out_dir_in_new_parent(tmp_path: Path) -> None:
    out = tmp_path / "deep" / "er" / "run"
    with output.StagedRun(out) as staged:
        staged.write("a.txt", b"x")
        staged.publish()
    assert (out / "a.txt").exists()


# --- is_eureka_run_folder ---------------------------------------------------


def test_is_eureka_run_folder(tmp_path: Path) -> None:
    good = tmp_path / "good"
    _write_manifest(good)
    wrong = tmp_path / "wrong"
    _write_manifest(wrong, schema="other")
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "manifest.json").write_text("{not json", encoding="utf-8")
    listy = tmp_path / "listy"
    listy.mkdir()
    (listy / "manifest.json").write_text("[]", encoding="utf-8")
    empty = tmp_path / "empty"
    empty.mkdir()
    assert output.is_eureka_run_folder(good)
    for folder in (wrong, broken, listy, empty, tmp_path / "missing"):
        assert not output.is_eureka_run_folder(folder)


# --- ensure_out_dir_allowed -------------------------------------------------


def test_out_equal_to_input_refused(tmp_path: Path) -> None:
    source = tmp_path / "in"
    source.mkdir()
    with pytest.raises(UsageError, match="input folder"):
        output.ensure_out_dir_allowed(source, source)


def test_out_inside_input_refused(tmp_path: Path) -> None:
    source = tmp_path / "in"
    source.mkdir()
    with pytest.raises(UsageError, match="inside"):
        output.ensure_out_dir_allowed(source, source / "results")


def test_input_inside_out_refused(tmp_path: Path) -> None:
    out = tmp_path / "out"
    source = out / "in"
    source.mkdir(parents=True)
    with pytest.raises(UsageError, match="inside the output folder"):
        output.ensure_out_dir_allowed(source, out)


def test_out_is_file_refused(tmp_path: Path) -> None:
    source = tmp_path / "in"
    source.mkdir()
    out = tmp_path / "file"
    out.write_text("x", encoding="utf-8")
    with pytest.raises(UsageError, match="file"):
        output.ensure_out_dir_allowed(source, out)


def test_out_non_empty_foreign_folder_refused(tmp_path: Path) -> None:
    source = tmp_path / "in"
    source.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    (out / "x.txt").write_text("x", encoding="utf-8")
    with pytest.raises(UsageError, match="output folder exists and is not an Eureka run"):
        output.ensure_out_dir_allowed(source, out)


def test_out_allowed_cases(tmp_path: Path) -> None:
    source = tmp_path / "in"
    source.mkdir()
    empty = tmp_path / "empty"
    empty.mkdir()
    previous = tmp_path / "previous"
    _write_manifest(previous)
    sibling_of_input = tmp_path / "in-results"
    for allowed in (
        tmp_path / "new",
        empty,
        previous,
        tmp_path / "missing" / "deeper" / "run",
        sibling_of_input,
    ):
        output.ensure_out_dir_allowed(source, allowed)


def test_out_parent_is_file_refused(tmp_path: Path) -> None:
    source = tmp_path / "in"
    source.mkdir()
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    with pytest.raises(UsageError, match="parent"):
        output.ensure_out_dir_allowed(source, blocker / "run")


# --- replaceable predicate and kind word (hub hook) ----------------------------


def _is_marked(folder: Path) -> bool:
    return (folder / "hub-marker.txt").is_file()


def _marked_folder(path: Path) -> Path:
    path.mkdir()
    (path / "hub-marker.txt").write_text("hub", encoding="utf-8")
    (path / "old.txt").write_text("old", encoding="utf-8")
    return path


def test_default_call_refuses_foreign_folder_with_the_old_text(tmp_path: Path) -> None:
    out = tmp_path / "run"
    out.mkdir()
    (out / "mine.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(UsageError) as caught, output.StagedRun(out) as staged:
        staged.write("new.txt", b"new")
        staged.publish()
    assert caught.value.message == "output folder exists and is not an Eureka run"
    assert caught.value.fix == (
        "Choose a new folder name, an empty folder, or the folder of an earlier run."
    )
    assert (out / "mine.txt").read_text(encoding="utf-8") == "keep"


def test_predicate_lets_publish_replace_a_marked_folder(tmp_path: Path) -> None:
    out = _marked_folder(tmp_path / "hub")
    with output.StagedRun(out, replaceable=_is_marked, kind="Eureka hub") as staged:
        staged.write("new.txt", b"new")
        staged.publish()
    assert (out / "new.txt").read_bytes() == b"new"
    assert not (out / "old.txt").exists()
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".")]


def test_false_predicate_refuses_and_keeps_the_staging_folder(tmp_path: Path) -> None:
    out = tmp_path / "hub"
    out.mkdir()
    (out / "mine.txt").write_text("keep", encoding="utf-8")
    staged = output.StagedRun(out, replaceable=_is_marked, kind="Eureka hub")
    staged.write("new.txt", b"new")
    with pytest.raises(UsageError, match="output folder exists and is not an Eureka hub"):
        staged.publish()
    assert (out / "mine.txt").read_text(encoding="utf-8") == "keep"
    assert (staged.path / "new.txt").exists()
    staged.discard()


def test_ensure_out_dir_allowed_applies_the_predicate(tmp_path: Path) -> None:
    source = tmp_path / "in"
    source.mkdir()
    marked = _marked_folder(tmp_path / "hub")
    output.ensure_out_dir_allowed(source, marked, replaceable=_is_marked, kind="Eureka hub")
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "x.txt").write_text("x", encoding="utf-8")
    with pytest.raises(UsageError, match="output folder exists and is not an Eureka hub"):
        output.ensure_out_dir_allowed(source, foreign, replaceable=_is_marked, kind="Eureka hub")
    other = tmp_path / "other"
    _write_manifest(other)
    with pytest.raises(UsageError, match="not an Eureka hub"):
        output.ensure_out_dir_allowed(source, other, replaceable=_is_marked, kind="Eureka hub")


def test_ensure_out_dir_allowed_keeps_the_input_guards_with_a_predicate(tmp_path: Path) -> None:
    source = tmp_path / "in"
    source.mkdir()
    with pytest.raises(UsageError, match="input folder"):
        output.ensure_out_dir_allowed(source, source, replaceable=_is_marked, kind="Eureka hub")
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    with pytest.raises(UsageError, match="file"):
        output.ensure_out_dir_allowed(source, blocker, replaceable=_is_marked, kind="Eureka hub")


def test_empty_folder_is_replaced_with_any_predicate(tmp_path: Path) -> None:
    out = tmp_path / "hub"
    out.mkdir()
    with output.StagedRun(out, replaceable=lambda _folder: False, kind="Eureka hub") as staged:
        staged.write("new.txt", b"new")
        staged.publish()
    assert (out / "new.txt").read_bytes() == b"new"
    source = tmp_path / "in"
    source.mkdir()
    empty = tmp_path / "empty"
    empty.mkdir()
    output.ensure_out_dir_allowed(source, empty, replaceable=lambda _f: False, kind="Eureka hub")


def test_source_has_no_short_engine_codes_or_em_dash() -> None:
    text = Path(output.__file__).read_text(encoding="utf-8")
    assert chr(0x2014) not in text
    assert not SHORT_CODES.search(text)
