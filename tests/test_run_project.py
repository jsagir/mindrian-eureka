"""Tests for the projection of engine results (plan 02-04, task 1)."""

from __future__ import annotations

import copy
import hashlib
from typing import Any

import pytest
from mindrian_eureka.run import project
from mindrian_eureka.run.contracts import (
    LABEL,
    PAIRS_SCHEMA,
    SCORE_MEANING,
    UNUSUAL_PAIRS_CAPABILITY,
    UNUSUAL_PAIRS_NAME,
    WORDING_AND_MEANING_CAPABILITY,
    WORDING_AND_MEANING_NAME,
    Record,
)

FORBIDDEN_KEYS = (
    "started_at",
    "finished_at",
    "duration_ms",
    "generated_at",
    "retrieved_at",
    "model_provider",
    "room_dir",
    "excerpt",
    "source_trail",
    "extracted_sentence",
    "review_context",
    "breakthrough_potential",
)
SECRET_PATH = "/home/someone/private/models/all-MiniLM-L6-v2"


def _record(record_id: str, title: str = "") -> Record:
    text = f"Body of {record_id}."
    return Record(
        id=record_id,
        title=title or f"Title {record_id}",
        text=text,
        source_ref=f"{record_id}.md",
        source_file=f"{record_id}.md",
        text_sha256=hashlib.sha256(text.encode()).hexdigest(),
    )


@pytest.fixture
def records() -> list[Record]:
    return [_record("a"), _record("b"), _record("c")]


def _unusual_item(
    left: str, right: str, rank: int, structural: float, semantic: float, direction: str
) -> dict[str, Any]:
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
            "method_signals": {
                "scoring": "hybrid_2026",
                "bm25_similarity": 0.12,
                "dense_z": 1.5,
                "gap_percentile": 0.97,
                "flag": True,
            },
            "direction": direction,
            "direction_meaning": "engine text",
            "interpretation_to_review": "engine text",
        },
        "source_refs": ["x"],
        "review_context": {"left_evidence": {"excerpt": "SECRET EXCERPT"}},
    }


@pytest.fixture
def unusual_result() -> dict[str, Any]:
    return {
        "outputs": [
            _unusual_item("a", "b", 1, 0.20, 0.80, "structural_transfer"),
            _unusual_item("c", "a", 2, 0.70, 0.30, "semantic_implementation"),
        ],
        "runner": {"started_at": "2026-10-24T10:00:00Z", "finished_at": "2026-10-24T10:01:00Z"},
        "resource_use": {"duration_ms": 61000},
        "model_provider": {"path": SECRET_PATH},
    }


def _wording_pair(
    left: str, right: str, rank: int, lsa: float, sem: float, label: str
) -> dict[str, Any]:
    return {
        "left_id": left,
        "right_id": right,
        "rank": rank,
        "lsa_sim": lsa,
        "semantic_sim": sem,
        "lexical_sim": 0.1,
        "bm25_sim": 0.2,
        "hsi_score": 0.9,
        "hsi_percentile": 0.99,
        "hsi_z": 2.5,
        "surprise_type": label,
        "second_signal": {
            "method": "bm25_vs_dense_surprise",
            "surprise": 0.3,
            "percentile": 0.9,
            "confirmed": True,
        },
        "source_trail": [
            {"retrieved_at": "2026-10-24T10:00:00Z", "extracted_sentence": "SECRET SENTENCE"}
        ],
        "novelty_check": {"status": "in_room_check_only"},
    }


@pytest.fixture
def wording_pairs() -> list[dict[str, Any]]:
    return [
        _wording_pair("a", "b", 1, 0.8, 0.2, "structural_transfer"),
        _wording_pair("b", "c", 2, 0.2, 0.8, "semantic_implementation"),
    ]


def _keys(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            found.add(str(key))
            found |= _keys(item)
    elif isinstance(value, list):
        for item in value:
            found |= _keys(item)
    return found


# --- Readings ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.5, project.READING_MEANING_HIGHER),
        (-0.5, project.READING_WORDING_HIGHER),
        (0.0, project.READING_AGREE),
    ],
)
def test_direction_for_unusual_pair(value: float, expected: str) -> None:
    assert project.direction_for_unusual_pair(value) == expected
    assert project.READING_MEANING_HIGHER == "Similar meaning, different wording."
    assert project.READING_WORDING_HIGHER == "Similar wording, different meaning."
    assert project.READING_AGREE == "Wording and meaning agree on this pair."


@pytest.mark.parametrize(
    ("wording", "meaning", "expected"),
    [
        (0.2, 0.8, project.READING_MEANING_HIGHER),
        (0.8, 0.2, project.READING_WORDING_HIGHER),
        (0.5, 0.5, project.READING_AGREE),
    ],
)
def test_direction_for_wording_pair(wording: float, meaning: float, expected: str) -> None:
    assert project.direction_for_wording_pair(wording, meaning) == expected


@pytest.mark.parametrize("label", ["structural_transfer", "semantic_implementation", "other"])
def test_unusual_reading_ignores_engine_label(
    records: list[Record], label: str
) -> None:
    result = {"outputs": [_unusual_item("a", "b", 1, 0.2, 0.8, label)]}
    out = project.project_unusual_pairs(result, records, settings={}, top_k=5, notes=[])
    assert out["pairs"][0]["reading"] == project.READING_MEANING_HIGHER


@pytest.mark.parametrize("label", ["structural_transfer", "semantic_implementation", "other"])
def test_wording_reading_ignores_engine_label(records: list[Record], label: str) -> None:
    pairs = [_wording_pair("a", "b", 1, 0.8, 0.2, label)]
    out = project.project_wording_and_meaning(pairs, records, settings={}, top_k=5, notes=[])
    assert out["pairs"][0]["reading"] == project.READING_WORDING_HIGHER


def test_polarity_unusual_engine_matches_its_label(
    records: list[Record], unusual_result: dict[str, Any]
) -> None:
    """For this engine, structural_transfer means the meaning score is higher."""
    out = project.project_unusual_pairs(unusual_result, records, settings={}, top_k=5, notes=[])
    by_label = {
        item["payload"]["direction"]: pair["reading"]
        for item, pair in zip(unusual_result["outputs"], out["pairs"], strict=True)
    }
    assert by_label["structural_transfer"] == project.READING_MEANING_HIGHER
    assert by_label["semantic_implementation"] == project.READING_WORDING_HIGHER


def test_polarity_wording_engine_is_opposite(
    records: list[Record], wording_pairs: list[dict[str, Any]]
) -> None:
    """For this engine, structural_transfer means the wording score is higher."""
    out = project.project_wording_and_meaning(
        wording_pairs, records, settings={}, top_k=5, notes=[]
    )
    by_label = {
        pair["surprise_type"]: projected["reading"]
        for pair, projected in zip(wording_pairs, out["pairs"], strict=True)
    }
    assert by_label["structural_transfer"] == project.READING_WORDING_HIGHER
    assert by_label["semantic_implementation"] == project.READING_MEANING_HIGHER


# --- Shape ------------------------------------------------------------------


def test_unusual_file_shape(records: list[Record], unusual_result: dict[str, Any]) -> None:
    out = project.project_unusual_pairs(
        unusual_result, records, settings={"top_k": 2}, top_k=2, notes=["note one"]
    )
    assert set(out) == {
        "schema_version",
        "label",
        "engine",
        "score_meaning",
        "notes",
        "settings",
        "counts",
        "pairs",
    }
    assert out["schema_version"] == PAIRS_SCHEMA
    assert out["label"] == LABEL
    assert out["engine"] == {
        "name": UNUSUAL_PAIRS_NAME,
        "capability_id": UNUSUAL_PAIRS_CAPABILITY,
    }
    assert out["score_meaning"] == SCORE_MEANING["unusual_pairs"]
    assert out["notes"] == ["note one"]
    assert out["counts"] == {
        "records_scored": 3,
        "pairs": 2,
        "top_k": 2,
        "top_k_reached": True,
    }
    pair = out["pairs"][0]
    assert set(pair) == {"rank", "pair_id", "left", "right", "scores", "reading", "label"}
    assert pair["label"] == LABEL
    assert set(pair["left"]) == {"id", "title", "source_ref"}
    assert set(pair["scores"]) == {
        "wording_similarity",
        "meaning_similarity",
        "signed_gap",
        "rank_score",
        "method_signals",
    }
    assert pair["scores"]["method_signals"] == {
        "bm25_similarity": 0.12,
        "dense_z": 1.5,
        "gap_percentile": 0.97,
    }
    assert list(pair["scores"]["method_signals"]) == sorted(pair["scores"]["method_signals"])


def test_wording_file_shape(records: list[Record], wording_pairs: list[dict[str, Any]]) -> None:
    out = project.project_wording_and_meaning(
        wording_pairs, records, settings={"tier": 1}, top_k=200, notes=[]
    )
    assert out["engine"] == {
        "name": WORDING_AND_MEANING_NAME,
        "capability_id": WORDING_AND_MEANING_CAPABILITY,
    }
    assert out["score_meaning"] == SCORE_MEANING["wording_and_meaning"]
    assert out["counts"]["top_k_reached"] is False
    assert out["settings"] == {"tier": 1}
    scores = out["pairs"][0]["scores"]
    assert set(scores) == {
        "wording_similarity",
        "lexical_similarity",
        "bm25_similarity",
        "meaning_similarity",
        "rank_score",
        "percentile",
        "z_score",
        "second_signal",
    }
    assert scores["wording_similarity"] == 0.8
    assert scores["second_signal"]["confirmed"] is True


def test_wording_bm25_is_optional(records: list[Record]) -> None:
    pair = _wording_pair("a", "b", 1, 0.8, 0.2, "x")
    del pair["bm25_sim"]
    del pair["second_signal"]
    out = project.project_wording_and_meaning([pair], records, settings={}, top_k=5, notes=[])
    assert "bm25_similarity" not in out["pairs"][0]["scores"]
    assert "second_signal" not in out["pairs"][0]["scores"]


def test_titles_and_refs_come_from_records(
    unusual_result: dict[str, Any], records: list[Record]
) -> None:
    out = project.project_unusual_pairs(unusual_result, records, settings={}, top_k=5, notes=[])
    left = out["pairs"][0]["left"]
    assert left == {"id": "a", "title": "Title a", "source_ref": "a.md"}


def test_unknown_id_raises(
    unusual_result: dict[str, Any], wording_pairs: list[dict[str, Any]]
) -> None:
    only_a = [_record("a")]
    with pytest.raises(ValueError, match="Unknown record id"):
        project.project_unusual_pairs(unusual_result, only_a, settings={}, top_k=5, notes=[])
    with pytest.raises(ValueError, match="Unknown record id"):
        project.project_wording_and_meaning(wording_pairs, only_a, settings={}, top_k=5, notes=[])


# --- Pair id ----------------------------------------------------------------


def test_pair_id_formula_and_order_independence(records: list[Record]) -> None:
    expected = "pair-" + hashlib.sha256(b"a\0b").hexdigest()[:20]
    forward = project.project_unusual_pairs(
        {"outputs": [_unusual_item("a", "b", 1, 0.2, 0.8, "x")]},
        records,
        settings={},
        top_k=5,
        notes=[],
    )
    backward = project.project_unusual_pairs(
        {"outputs": [_unusual_item("b", "a", 1, 0.2, 0.8, "x")]},
        records,
        settings={},
        top_k=5,
        notes=[],
    )
    assert forward["pairs"][0]["pair_id"] == expected
    assert backward["pairs"][0]["pair_id"] == expected


def test_pair_id_equal_across_engines(records: list[Record]) -> None:
    unusual = project.project_unusual_pairs(
        {"outputs": [_unusual_item("a", "b", 1, 0.2, 0.8, "x")]},
        records,
        settings={},
        top_k=5,
        notes=[],
    )
    wording = project.project_wording_and_meaning(
        [_wording_pair("b", "a", 1, 0.8, 0.2, "x")], records, settings={}, top_k=5, notes=[]
    )
    assert unusual["pairs"][0]["pair_id"] == wording["pairs"][0]["pair_id"]


# --- Volatile fields --------------------------------------------------------


def test_no_forbidden_key_in_projected_files(
    records: list[Record],
    unusual_result: dict[str, Any],
    wording_pairs: list[dict[str, Any]],
) -> None:
    unusual = project.project_unusual_pairs(unusual_result, records, settings={}, top_k=5, notes=[])
    wording = project.project_wording_and_meaning(
        wording_pairs, records, settings={}, top_k=5, notes=[]
    )
    for projected in (unusual, wording):
        keys = _keys(projected)
        assert not keys.intersection(FORBIDDEN_KEYS)
        text = repr(projected)
        assert "SECRET" not in text
        assert SECRET_PATH not in text
        assert "2026-10-24T" not in text


def test_projection_does_not_change_input(
    records: list[Record], unusual_result: dict[str, Any]
) -> None:
    before = copy.deepcopy(unusual_result)
    project.project_unusual_pairs(unusual_result, records, settings={}, top_k=5, notes=[])
    assert unusual_result == before


# --- Counts and notes -------------------------------------------------------


@pytest.mark.parametrize(
    ("pair_count", "top_k", "reached"),
    [(2, 2, True), (2, 3, False), (2, 0, False), (3, 2, True)],
)
def test_top_k_reached(
    records: list[Record], pair_count: int, top_k: int, reached: bool
) -> None:
    items = [_unusual_item("a", "b", n + 1, 0.2, 0.8, "x") for n in range(pair_count)]
    out = project.project_unusual_pairs(
        {"outputs": items}, records, settings={}, top_k=top_k, notes=[]
    )
    assert out["counts"]["top_k_reached"] is reached


def test_empty_result_adds_note_after_engine_notes(records: list[Record]) -> None:
    unusual = project.project_unusual_pairs(
        {"outputs": []}, records, settings={}, top_k=5, notes=["first note"]
    )
    wording = project.project_wording_and_meaning([], records, settings={}, top_k=5, notes=[])
    empty = "No candidate pairs were returned for this collection."
    assert unusual["notes"] == ["first note", empty]
    assert wording["notes"] == [empty]
    assert unusual["pairs"] == []


# --- Warnings and descriptions ----------------------------------------------


def test_filter_engine_warnings() -> None:
    warnings = [
        "Structural LSA used 5 topics.",
        "Model identity is recorded as the supplied local path; pin and record digests.",
        "Another warning.",
    ]
    assert project.filter_engine_warnings(warnings) == [
        "Structural LSA used 5 topics.",
        "Another warning.",
    ]


def test_describe_caps() -> None:
    caps = [
        {
            "name": "max_artifacts",
            "limit": 3000,
            "records_in": 3200,
            "records_used": 3000,
            "dropped_count": 200,
            "dropped_ids_sha256": "ab",
        }
    ]
    [sentence] = project.describe_caps(caps)
    for part in ("3000", "3200", "200", "max_artifacts"):
        assert part in sentence
    assert project.describe_caps([]) == []


def test_describe_drops_names_ten_ids_then_count() -> None:
    dropped = [
        {"id": f"r{n:02d}", "reason": "body_under_50_chars", "source_file": "f.md"}
        for n in range(13)
    ]
    [sentence] = project.describe_drops(dropped)
    assert "13 records were left out" in sentence
    assert "body_under_50_chars" in sentence
    assert "r09" in sentence
    assert "r10" not in sentence
    assert "and 3 more" in sentence


def test_describe_drops_one_sentence_per_reason() -> None:
    dropped = [
        {"id": "x", "reason": "empty_text", "source_file": "f.md"},
        {"id": "y", "reason": "body_under_50_chars", "source_file": "f.md"},
    ]
    sentences = project.describe_drops(dropped)
    assert len(sentences) == 2
    assert any("1 record was left out" in s for s in sentences)
    assert project.describe_drops([]) == []
