"""RUN-05 proof: every output file and the summary keep the label and the score meaning."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from conftest import InputSet
from mindrian_eureka.cli import main
from mindrian_eureka.run.contracts import LABEL, SCORE_MEANING, SUMMARY_LINE
from mindrian_eureka.run.project import (
    READING_AGREE,
    READING_MEANING_HIGHER,
    READING_WORDING_HIGHER,
)

SHORT_CODE = re.compile(r"\b(R[S]|H[S]I)\b")
RANKED_JSON = {
    "unusual-pairs.json": "unusual_pairs",
    "wording-and-meaning-pairs.json": "wording_and_meaning",
}
ENGINE_NAMES = (
    "Find Unusual Pairs Across a Research Collection",
    "Rank Unusual Pairs by Wording and Meaning",
)


@pytest.fixture
def run_out(
    isolated_env: Path,
    stub_encoders: None,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> tuple[Path, str, str]:
    """Run once through the CLI. Return the output folder, standard output and standard error."""
    inputs = tmp_inputs("markdown")
    out = tmp_path / "out"
    code = main(["run", str(inputs.folder), "--out", str(out), "--model-path", str(fake_model_dir)])
    assert code == 0
    captured = capsys.readouterr()
    return out, captured.out, captured.err


def output_files(out: Path) -> list[Path]:
    return sorted(path for path in out.rglob("*") if path.is_file())


def strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


# --- (a) every file carries the label -----------------------------------------


def test_every_output_file_carries_the_label(run_out: tuple[Path, str, str]) -> None:
    out, _stdout, _stderr = run_out
    files = output_files(out)
    names = {path.relative_to(out).as_posix() for path in files}
    assert names == {
        "unusual-pairs.json",
        "wording-and-meaning-pairs.json",
        "ranked-pairs.md",
        "corpus/records.jsonl",
        "manifest.json",
        "run-info.json",
    }
    for path in files:
        assert LABEL in path.read_text(encoding="utf-8"), path.name


# --- (b) ranked JSON files ----------------------------------------------------


@pytest.mark.parametrize(("name", "key"), sorted(RANKED_JSON.items()))
def test_ranked_json_label_and_score_meaning(
    run_out: tuple[Path, str, str], name: str, key: str
) -> None:
    out, _stdout, _stderr = run_out
    document = json.loads((out / name).read_text(encoding="utf-8"))
    assert document["label"] == LABEL
    assert document["score_meaning"] == SCORE_MEANING[key]
    assert document["pairs"]
    for pair in document["pairs"]:
        assert pair["label"] == LABEL
        assert pair["reading"].strip()


# --- (c) the Markdown report --------------------------------------------------


def test_markdown_report_holds_names_summary_and_score_meaning(
    run_out: tuple[Path, str, str],
) -> None:
    out, _stdout, _stderr = run_out
    text = (out / "ranked-pairs.md").read_text(encoding="utf-8")
    for name in ENGINE_NAMES:
        assert name in text
    assert SUMMARY_LINE in text
    for meaning in SCORE_MEANING.values():
        assert meaning in text


# --- (d) the summary ----------------------------------------------------------


def test_stdout_ends_with_the_summary_line(run_out: tuple[Path, str, str]) -> None:
    _out, stdout, _stderr = run_out
    lines = [line for line in stdout.splitlines() if line.strip()]
    assert lines[-1] == SUMMARY_LINE


def test_json_summary_has_label_and_summary_line(
    isolated_env: Path,
    stub_encoders: None,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = tmp_inputs("markdown")
    argv = ["run", str(inputs.folder), "--out", str(tmp_path / "out")]
    code = main([*argv, "--model-path", str(fake_model_dir), "--json"])
    assert code == 0
    document = json.loads(capsys.readouterr().out)
    assert document["label"] == LABEL
    assert document["summary_line"] == SUMMARY_LINE


# --- (e) the reading agrees with the numbers ----------------------------------


def test_unusual_pairs_reading_follows_the_sign(run_out: tuple[Path, str, str]) -> None:
    out, _stdout, _stderr = run_out
    document = json.loads((out / "unusual-pairs.json").read_text(encoding="utf-8"))
    seen = set()
    for pair in document["pairs"]:
        gap = pair["scores"]["signed_gap"]
        if gap > 0:
            expected = READING_MEANING_HIGHER
        elif gap < 0:
            expected = READING_WORDING_HIGHER
        else:
            expected = READING_AGREE
        assert pair["reading"] == expected
        seen.add(pair["reading"])
    assert seen


def test_wording_and_meaning_reading_follows_the_scores(run_out: tuple[Path, str, str]) -> None:
    out, _stdout, _stderr = run_out
    document = json.loads((out / "wording-and-meaning-pairs.json").read_text(encoding="utf-8"))
    for pair in document["pairs"]:
        wording = pair["scores"]["wording_similarity"]
        meaning = pair["scores"]["meaning_similarity"]
        if meaning > wording:
            expected = READING_MEANING_HIGHER
        elif wording > meaning:
            expected = READING_WORDING_HIGHER
        else:
            expected = READING_AGREE
        assert pair["reading"] == expected


# --- (f) no short engine code anywhere a user can see -------------------------


def test_no_short_engine_code_in_output_or_streams(run_out: tuple[Path, str, str]) -> None:
    out, stdout, stderr = run_out
    assert SHORT_CODE.search((out / "ranked-pairs.md").read_text(encoding="utf-8")) is None
    assert SHORT_CODE.search(stdout) is None
    assert SHORT_CODE.search(stderr) is None
    for path in output_files(out):
        if path.suffix == ".json":
            document = json.loads(path.read_text(encoding="utf-8"))
            for value in strings(document):
                assert SHORT_CODE.search(value) is None, (path.name, value)


@pytest.mark.parametrize("command", [(), ("run",), ("doctor",)])
def test_no_short_engine_code_in_help(
    capsys: pytest.CaptureFixture[str], command: tuple[str, ...]
) -> None:
    with pytest.raises(SystemExit) as caught:
        main([*command, "--help"])
    assert caught.value.code == 0
    assert SHORT_CODE.search(capsys.readouterr().out) is None


def test_no_short_engine_code_in_missing_model_error(
    isolated_env: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = tmp_inputs("markdown")
    assert main(["run", str(inputs.folder), "--out", str(tmp_path / "out")]) == 1
    err = capsys.readouterr().err
    assert "No local model found." in err
    assert SHORT_CODE.search(err) is None


def test_small_collection_warning_holds_no_short_engine_code(
    isolated_env: Path,
    stub_encoders: None,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    inputs = tmp_inputs("markdown", count=4)
    out = tmp_path / "out"
    argv = ["run", str(inputs.folder), "--out", str(out), "--model-path", str(fake_model_dir)]
    assert main(argv) == 0
    captured = capsys.readouterr()
    assert SHORT_CODE.search(captured.err) is None
    for path in output_files(out):
        assert SHORT_CODE.search(path.read_text(encoding="utf-8")) is None, path.name
    notes = json.loads((out / "unusual-pairs.json").read_text(encoding="utf-8"))["notes"]
    assert any("at least 10 eligible pairs" in note for note in notes)


# --- (g) no claim of proof ----------------------------------------------------


def test_report_never_claims_validation(run_out: tuple[Path, str, str]) -> None:
    out, stdout, _stderr = run_out
    for text in ((out / "ranked-pairs.md").read_text(encoding="utf-8"), stdout):
        lowered = text.lower()
        assert "validated finding" not in lowered
        assert "proven" not in lowered
