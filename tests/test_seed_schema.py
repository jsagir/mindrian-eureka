"""Tests for the closed schema of the room seed (Phase 2.3, plan 02)."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from mindrian_eureka.run.contracts import LABEL
from mindrian_eureka.seed.contracts import (
    MODEL_BOUNDARY,
    SCORE_NOTE,
    SEED_SCHEMA,
    STATEMENT_BASIS,
    STATEMENT_METHOD,
)

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "src" / "mindrian_eureka" / "data" / "schemas" / "room-seed.v1.json"
HASH = "a" * 64
PAIR_1 = "pair-" + "1" * 20
PAIR_2 = "pair-" + "2" * 20


def schema() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return data


def errors(document: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema())
    return [error.message for error in validator.iter_errors(document)]


def _statement() -> dict[str, Any]:
    return {
        "text": "Hypothesis to review: One and Two may belong in one room.",
        "fields": {"tech_a": "One", "tech_b": "Two", "reading": "A reading."},
        "critic": "pending",
        "banked": False,
        "label": LABEL,
        "method": STATEMENT_METHOD,
        "basis": STATEMENT_BASIS,
    }


def _record(name: str, role: str) -> dict[str, Any]:
    return {
        "record_id": name,
        "title": name,
        "role": role,
        "evidence_file": f"evidence/{name}-12345678.md",
        "evidence_sha256": HASH,
    }


def _source(name: str) -> dict[str, Any]:
    return {"record_id": name, "source_ref": f"{name}.csv#1", "source_file": f"{name}.csv",
            "text_sha256": HASH}


def _pair(pair_id: str, left: str, right: str) -> dict[str, Any]:
    return {
        "pair_id": pair_id,
        "left_id": left,
        "right_id": right,
        "engines": [
            {
                "engine": "unusual_pairs",
                "rank": 1,
                "wording_similarity": 0.1,
                "meaning_similarity": 0.5,
                "rank_score": 0.9,
                "reading": "A reading.",
            }
        ],
    }


def _entry(pair_id: str, left: str, right: str) -> dict[str, Any]:
    return {
        "entry_id": pair_id,
        "pair_id": pair_id,
        "left_id": left,
        "right_id": right,
        "review_status": "proposed",
        "statement": _statement(),
    }


def base_document() -> dict[str, Any]:
    return {
        "schema_version": SEED_SCHEMA,
        "label": LABEL,
        "scope_id": "eureka-run-" + "a" * 16,
        "snapshot_id": HASH,
        "manifest_sha256": HASH,
        "engine_versions": {"name": "mindrian-eureka", "version": "1.0.0", "engines": {}},
        "seed_writer": {"name": "mindrian-eureka", "version": "1.0.0"},
        "known": {
            "legal-ip": [
                {"record_id": "a", "column": "status", "held_in": "carried", "value": "Active"},
                {"record_id": "a", "column": "abstract", "held_in": "record_text"},
                {"record_id": "a", "column": "funding", "held_in": "export_only"},
            ]
        },
        "feed_next": {
            "legal-ip": [
                {"record_id": "a", "column": "options", "reason": "blank in this export"},
                {"record_id": "a", "item": "patents", "source": "SynthDB",
                 "reason": "not in this export; held in SynthDB"},
            ]
        },
        "suggested_sections": ["legal-ip"],
        "score_note": SCORE_NOTE,
        "model_boundary": MODEL_BOUNDARY,
    }


def valid_pair_document() -> dict[str, Any]:
    document = base_document()
    document.update(
        seed_kind="pair",
        selection={"pair_ids": [PAIR_1]},
        records=[_record("a", "pair_member"), _record("b", "pair_member")],
        source_refs=[_source("a"), _source("b")],
        pairs=[_pair(PAIR_1, "a", "b")],
        bank_entries=[_entry(PAIR_1, "a", "b")],
    )
    return document


def valid_cluster_document() -> dict[str, Any]:
    document = base_document()
    entry = _entry(PAIR_2, "a", "c")
    entry["neighbour_id"] = "c"
    entry["pair_class"] = "cross"
    document.update(
        seed_kind="cluster",
        selection={
            "spine_record_id": "a",
            "degree": 3,
            "min_degree": 3,
            "pair_ids": [PAIR_1, PAIR_2],
        },
        records=[
            _record("a", "spine"),
            {**_record("b", "neighbour"), "outcome_class": "open",
             "carried": {"status": "Active"}, "text_source": "sidecar"},
            _record("c", "neighbour"),
        ],
        source_refs=[_source("a"), _source("b"), _source("c")],
        pairs=[_pair(PAIR_1, "a", "b"), _pair(PAIR_2, "a", "c")],
        bank_entries=[_entry(PAIR_1, "a", "b"), entry],
    )
    return document


def test_schema_is_valid_and_closed() -> None:
    Draft202012Validator.check_schema(schema())
    assert schema()["$id"] == SEED_SCHEMA
    assert schema()["additionalProperties"] is False
    assert LABEL not in SCHEMA_PATH.read_text(encoding="utf-8")


def test_valid_documents_pass() -> None:
    assert errors(valid_pair_document()) == []
    assert errors(valid_cluster_document()) == []


def _drop(key: str) -> Any:
    def change(document: dict[str, Any]) -> None:
        del document[key]
    return change


def _set(path: tuple[str | int, ...], value: Any) -> Any:
    def change(document: dict[str, Any]) -> None:
        node: Any = document
        for step in path[:-1]:
            node = node[step]
        node[path[-1]] = value
    return change


def _known_value(document: dict[str, Any]) -> None:
    document["known"]["legal-ip"][2]["value"] = "x"


def _carried_without_value(document: dict[str, Any]) -> None:
    del document["known"]["legal-ip"][0]["value"]


def _feed_both(document: dict[str, Any]) -> None:
    document["feed_next"]["legal-ip"][0]["item"] = "patents"


def _feed_item_no_source(document: dict[str, Any]) -> None:
    del document["feed_next"]["legal-ip"][1]["source"]


def _bad_section(document: dict[str, Any]) -> None:
    document["known"]["Legal IP"] = document["known"].pop("legal-ip")


def _pair_with_spine(document: dict[str, Any]) -> None:
    document["selection"]["spine_record_id"] = "a"


def _pair_with_two_ids(document: dict[str, Any]) -> None:
    document["selection"]["pair_ids"] = [PAIR_1, PAIR_2]


INVALID_PAIR = [
    ("missing label", _drop("label")),
    ("seed kind room", _set(("seed_kind",), "room")),
    ("feed item with column and item", _feed_both),
    ("feed item with item and no source", _feed_item_no_source),
    ("known item export only with a value", _known_value),
    ("known item carried without a value", _carried_without_value),
    ("unknown top level key", _set(("room_id",), "x")),
    ("critic passed", _set(("bank_entries", 0, "statement", "critic"), "passed")),
    ("banked true", _set(("bank_entries", 0, "statement", "banked"), True)),
    ("review status accepted", _set(("bank_entries", 0, "review_status"), "accepted")),
    ("bad schema version", _set(("schema_version",), "eureka.room-seed.v2")),
    ("bad scope id", _set(("scope_id",), "room-1")),
    ("bad hash", _set(("manifest_sha256",), "XYZ")),
    ("bad section name", _bad_section),
    ("pair seed with a spine id", _pair_with_spine),
    ("pair seed with two pair ids", _pair_with_two_ids),
    ("bad pair id", _set(("pairs", 0, "pair_id"), "pair-1")),
    ("evidence file outside the folder", _set(("records", 0, "evidence_file"), "../x.md")),
    ("unknown role", _set(("records", 0, "role"), "owner")),
    ("unknown key in a record", _set(("records", 0, "email"), "x")),
    ("unknown engine", _set(("pairs", 0, "engines", 0, "engine"), "other")),
    ("unknown writer", _set(("seed_writer", "name"), "other")),
]


@pytest.mark.parametrize("name,change", INVALID_PAIR, ids=[name for name, _ in INVALID_PAIR])
def test_invalid_pair_documents_fail(name: str, change: Any) -> None:
    document = valid_pair_document()
    change(document)
    assert errors(document), name


def _cluster_no_spine(document: dict[str, Any]) -> None:
    del document["selection"]["spine_record_id"]


def _cluster_no_degree(document: dict[str, Any]) -> None:
    del document["selection"]["degree"]


def _cluster_extra_key(document: dict[str, Any]) -> None:
    document["selection"]["note"] = "x"


INVALID_CLUSTER = [
    ("cluster selection without the spine", _cluster_no_spine),
    ("cluster selection without the degree", _cluster_no_degree),
    ("cluster selection with an unknown key", _cluster_extra_key),
]


@pytest.mark.parametrize("name,change", INVALID_CLUSTER, ids=[name for name, _ in INVALID_CLUSTER])
def test_invalid_cluster_documents_fail(name: str, change: Any) -> None:
    document = valid_cluster_document()
    change(document)
    assert errors(document), name


def test_the_helper_documents_are_independent() -> None:
    first = valid_pair_document()
    second = copy.deepcopy(first)
    second["known"].clear()
    assert first["known"]


def test_schema_file_is_package_data() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r"package-data\]\s*\nmindrian_eureka = \[(.*?)\]", text, re.S)
    assert match is not None
    assert '"data/schemas/*.json"' in match.group(1)
    assert SCHEMA_PATH.parent.name == "schemas"
    assert SCHEMA_PATH.match("*/data/schemas/*.json")
