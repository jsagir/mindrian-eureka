"""Tests for the shared run contracts."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
from mindrian_eureka.run import contracts

SRC = str(Path(__file__).resolve().parent.parent / "src")


def test_exit_codes() -> None:
    assert contracts.EXIT_OK == 0
    assert contracts.EXIT_FAILURE == 1
    assert contracts.EXIT_USAGE == 2
    assert contracts.EXIT_INTERRUPTED == 130


def test_error_classes_keep_message_and_fix() -> None:
    usage = contracts.UsageError("bad flag", fix="use --help")
    run = contracts.RunError("failed")
    assert usage.exit_code == 2
    assert usage.message == "bad flag"
    assert usage.fix == "use --help"
    assert run.exit_code == 1
    assert run.fix is None
    assert isinstance(usage, contracts.EurekaError)
    assert str(run) == "failed"


def test_label_and_summary_line_are_exact() -> None:
    assert contracts.LABEL == "candidate, not verified"
    assert contracts.SUMMARY_LINE == (
        "All results are candidates, not verified. They are leads for human review."
    )


@pytest.mark.parametrize("key", ["unusual_pairs", "wording_and_meaning"])
def test_score_meaning_texts(key: str) -> None:
    text = contracts.SCORE_MEANING[key]
    assert not re.search(r"\b(R[S]|H[S]I)\b", text)
    assert chr(0x2014) not in text
    assert "does not show novelty" in text


def test_score_meaning_has_two_keys() -> None:
    assert set(contracts.SCORE_MEANING) == {"unusual_pairs", "wording_and_meaning"}


def test_record_model_text_rule() -> None:
    record = contracts.Record(
        id="a", title="Title", text="Body", source_ref="x/a", source_file="x.md",
        text_sha256=contracts.sha256_text("Body"),
    )
    assert record.model_text == "Title\n\nBody"
    empty = contracts.Record(
        id="b", title="", text="Body", source_ref="x/b", source_file="x.md",
        text_sha256=contracts.sha256_text("Body"),
    )
    assert empty.model_text == "Body"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("a\r\nb", "a\nb"),
        ("a\rb", "a\nb"),
        ("é", "é"),
        ("  padded \n", "padded"),
    ],
)
def test_normalize_text(raw: str, expected: str) -> None:
    assert contracts.normalize_text(raw) == expected
    assert contracts.normalize_text(contracts.normalize_text(raw)) == expected


def test_sha256_helpers() -> None:
    known = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert contracts.sha256_bytes(b"abc") == known
    assert contracts.sha256_text("abc") == known


def test_schema_ids() -> None:
    assert contracts.MAPPING_SCHEMA == "eureka.run-mapping.v1"
    assert contracts.PAIRS_SCHEMA.startswith("eureka.run-")


def test_import_is_light() -> None:
    # -I ignores PYTHONPATH, so the code adds the source folder to sys.path itself.
    code = (
        f"import sys; sys.path.insert(0, {SRC!r});"
        "import mindrian_eureka.run.contracts;"
        "heavy = ('numpy', 'sklearn', 'torch', 'sentence_transformers');"
        "bad = [m for m in heavy if m in sys.modules];"
        "print(','.join(bad))"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == ""
