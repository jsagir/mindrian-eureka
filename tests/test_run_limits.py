"""Tests for the shared run limits and the two engine entry points that use them."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mindrian_eureka import hsi_engine, limits
from mindrian_eureka.opportunity_pairs import runner


def _document(count: int) -> dict[str, Any]:
    return {
        "artifacts": [
            {"id": f"a{index}", "text": f"record text number {index}", "source_ref": f"r/{index}"}
            for index in range(count)
        ]
    }


def test_constants_have_documented_values() -> None:
    expected = {
        "MAX_TOP_K": 200,
        "MAX_ARTIFACTS": 3000,
        "HARD_MAX_ARTIFACTS": 5000,
        "MAX_RECORD_CHARS": 1_000_000,
        "MAX_TOTAL_TEXT_BYTES": 20 * 1024 * 1024,
        "MAX_INPUT_FILE_BYTES": 256 * 1024 * 1024,
        "MIN_BODY_CHARS": 50,
    }
    for name, value in expected.items():
        actual = getattr(limits, name)
        assert type(actual) is int
        assert actual == value


@pytest.mark.parametrize("count", [2, 3000])
def test_validate_document_accepts_up_to_default_cap(count: int) -> None:
    runner.validate_document(_document(count))


def test_validate_document_rejects_above_default_cap() -> None:
    with pytest.raises(ValueError, match="Artifact limit is 3,000 per run"):
        runner.validate_document(_document(3001))


def test_validate_document_accepts_raised_limit() -> None:
    runner.validate_document(_document(3001), max_artifacts=5000)


def test_validate_document_rejects_above_raised_limit() -> None:
    with pytest.raises(ValueError, match="Artifact limit is 5,000 per run"):
        runner.validate_document(_document(5001), max_artifacts=5000)


@pytest.mark.parametrize("bad", [1, 0, 5001, -3])
def test_validate_document_rejects_bad_max_artifacts(bad: int) -> None:
    with pytest.raises(ValueError, match="max_artifacts must be between 2 and 5000"):
        runner.validate_document(_document(3), max_artifacts=bad)


def test_run_document_rejects_top_k_above_cap(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="top_k must be between 0 and 200"):
        runner.run_document(
            _document(3), encoder_name="sentence-transformers", model_path="unused",
            top_k=201, cache_path=tmp_path / "cache.sqlite3",
        )


def test_run_document_top_k_check_names_negative(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="top_k must be between 0 and 200"):
        runner.run_document(
            _document(3), encoder_name="sentence-transformers", model_path="unused",
            top_k=-1, cache_path=tmp_path / "cache.sqlite3",
        )


def test_hsi_rejects_too_many_artifacts() -> None:
    with pytest.raises(hsi_engine.HSIInputError, match=r"artifacts must contain 2\.\.3000"):
        hsi_engine.run_hsi(_document(3001))


def test_hsi_rejects_top_k_above_cap() -> None:
    document = _document(2)
    document["top_k"] = 201
    with pytest.raises(hsi_engine.HSIInputError, match="top_k must be an integer from 1 to 200"):
        hsi_engine.run_hsi(document)
