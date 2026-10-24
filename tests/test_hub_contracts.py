"""Tests for the hub contracts: constants, folder test, deep links, JavaScript writer."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from mindrian_eureka.hub import contracts
from mindrian_eureka.hub.contracts import (
    DASH_CHARS,
    HUB_CONFIG,
    HUB_MANIFEST_SCHEMA,
    NEIGHBORHOOD_TINTS,
    deep_link,
    has_dash,
    has_internal_name,
    is_hub_folder,
    js_assignment,
)
from mindrian_eureka.run.contracts import MANIFEST_SCHEMA

SRC = Path(__file__).resolve().parents[1] / "src" / "mindrian_eureka" / "hub"
SHORT_CODES = re.compile(r"\b(R[S]|H[S]I)\b")


# --- constants --------------------------------------------------------------


def test_schema_ids_and_file_names() -> None:
    assert contracts.HUB_MANIFEST_SCHEMA == "eureka.hub-manifest.v1"
    assert contracts.HUB_DATA_SCHEMA == "eureka.hub-data.v1"
    assert contracts.HUB_ENVELOPE_SCHEMA == "eureka.hub-envelope.v1"
    assert contracts.HUB_SUMMARY_SCHEMA == "eureka.hub-summary.v1"
    assert contracts.OUTPUT_HUB_HTML == "hub.html"
    assert contracts.OUTPUT_HUB_DATA == "hub-data.js"
    assert contracts.OUTPUT_HUB_COPY == "hub-copy.js"
    assert contracts.OUTPUT_HUB_MANIFEST == "hub-manifest.json"
    assert contracts.DEFAULT_HUB_OUT == "eureka-hub"
    assert contracts.VIEW_NAMES == ("bank", "graph", "catalogue")
    assert contracts.ENGINE_UNUSUAL == "unusual_pairs"
    assert contracts.ENGINE_WORDING == "wording_and_meaning"


def test_face_and_lockup_files() -> None:
    assert dict(contracts.FACE_FILES) == {
        "Handover": "assets/faces/theo-handover.svg",
        "Limit": "assets/faces/theo-limit.svg",
        "Boundary": "assets/faces/theo-boundary.svg",
        "Rest": "assets/faces/theo-rest.svg",
    }
    assert contracts.LOCKUP_FILE == "assets/brand/mos-lockup-paper-v2.svg"


def test_limits() -> None:
    assert dict(HUB_CONFIG) == {
        "bank_page": 25,
        "catalogue_page": 50,
        "panel_text_chars": 600,
        "find_max": 8,
        "tour_max": 16,
        "graph_min_records": 15,
    }
    with pytest.raises(TypeError):
        HUB_CONFIG["bank_page"] = 1  # type: ignore[index]
    assert contracts.NOSCRIPT_PAIRS_PER_ENGINE == 50
    assert contracts.NOSCRIPT_RECORDS == 200
    assert (contracts.WIDTH_MIN, contracts.WIDTH_MAX, contracts.WIDTH_CROSSING) == (0.15, 0.5, 1.6)


def test_colours() -> None:
    assert len(NEIGHBORHOOD_TINTS) == 21
    assert len(set(NEIGHBORHOOD_TINTS)) == 21
    assert all(re.fullmatch(r"#[0-9a-f]{6}", tint) for tint in NEIGHBORHOOD_TINTS)
    assert contracts.DIM_COLOR == "#d8d4c8"
    # The four tints under 3:1 on paper (UI-SPEC 4) are dropped.
    for dropped in ("#c8a52a", "#9a9a3c", "#7aa35c", "#c48a3a"):
        assert dropped not in NEIGHBORHOOD_TINTS


# --- helpers ----------------------------------------------------------------


def test_dash_chars_and_helpers() -> None:
    assert DASH_CHARS == chr(8211) + chr(8212)
    assert has_dash("a" + chr(8212) + "b")
    assert has_dash("a" + chr(8211) + "b")
    assert not has_dash("a - b, a-b")


@pytest.mark.parametrize(
    "text",
    [
        "R" + "S result",
        "the H" + "SI score",
        "see r" + "s_corpus_exclude",
        "uses h" + "si_reference",
        "from hsi_reference.py",
        "module.py",
    ],
)
def test_internal_names_found(text: str) -> None:
    assert has_internal_name(text)


@pytest.mark.parametrize(
    "text",
    [
        "The wording-and-meaning engine used its built-in exclude list.",
        "Pairs, unusual-pairs engine",
        "Read the file ranked-pairs.md and hub-data.js",
        "Rsum and Hsin are not codes",
        "",
    ],
)
def test_internal_names_not_found(text: str) -> None:
    assert not has_internal_name(text)


@pytest.mark.parametrize("name", ["contracts.py", "deck.py", "reader.py"])
def test_hub_source_files_hold_no_dash_and_no_short_code(name: str) -> None:
    path = SRC / name
    if not path.exists():
        pytest.skip(f"{name} is written by a later task")
    text = path.read_text(encoding="utf-8")
    assert not has_dash(text)
    assert SHORT_CODES.search(text) is None


# --- is_hub_folder ----------------------------------------------------------


def _folder(base: Path, name: str, schema: object) -> Path:
    folder = base / name
    folder.mkdir()
    (folder / "hub-manifest.json").write_text(json.dumps({"schema_version": schema}))
    return folder


def test_is_hub_folder_true(tmp_path: Path) -> None:
    assert is_hub_folder(_folder(tmp_path, "hub", HUB_MANIFEST_SCHEMA))


def test_is_hub_folder_false_for_run_folder(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "manifest.json").write_text(json.dumps({"schema_version": MANIFEST_SCHEMA}))
    assert not is_hub_folder(run)
    assert not is_hub_folder(_folder(tmp_path, "other", MANIFEST_SCHEMA))


def test_is_hub_folder_false_for_empty_missing_and_broken(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    assert not is_hub_folder(empty)
    assert not is_hub_folder(tmp_path / "missing")
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / "hub-manifest.json").write_text("{not json")
    assert not is_hub_folder(broken)
    listy = tmp_path / "listy"
    listy.mkdir()
    (listy / "hub-manifest.json").write_text("[1, 2]")
    assert not is_hub_folder(listy)


# --- deep_link --------------------------------------------------------------


@pytest.mark.parametrize(
    ("record_id", "expected"),
    [
        ("doc01", "#doc01"),
        ("bank", "#record:bank"),
        ("graph", "#record:graph"),
        ("catalogue", "#record:catalogue"),
        ("hub-results", "#record:hub-results"),
        ("hub-", "#record:hub-"),
        ("banks", "#banks"),
        ("my-hub-x", "#my-hub-x"),
        ("bank-controls", "#record:bank-controls"),
        ("graph-stage", "#record:graph-stage"),
        ("catalogue-list", "#record:catalogue-list"),
        ("record:bank", "#record:record:bank"),
        ("record:record:bank", "#record:record:record:bank"),
    ],
)
def test_deep_link(record_id: str, expected: str) -> None:
    assert deep_link(record_id) == expected


# --- js_assignment ----------------------------------------------------------

PREFIX = "window.HUB = "
HOSTILE = "a{b}c&d" + chr(0x2028) + "e" + chr(0x2029) + "</script><img onerror=x>"


def _body(data: bytes, prefix: str = PREFIX) -> str:
    text = data.decode("utf-8")
    assert text.startswith(prefix)
    assert text.endswith(";\n")
    return text[len(prefix) : -2]


def test_js_assignment_round_trip_and_escapes() -> None:
    value = {"k": HOSTILE, HOSTILE: [1, 2.5, None, True], "plain": "x"}
    data = js_assignment("HUB", value)
    text = data.decode("utf-8")
    assert "&" not in text
    assert chr(0x2028) not in text
    assert chr(0x2029) not in text
    assert "</script" not in text
    # Only the structural braces remain: one object, so one pair.
    assert text.count("{") == 1
    assert text.count("}") == 1
    assert json.loads(_body(data)) == value


def test_js_assignment_keeps_escaped_quotes_and_backslashes() -> None:
    value = {"k": 'say "hi" \\ {x}', "z": 'end"'}
    data = js_assignment("HUB", value)
    assert json.loads(_body(data)) == value
    assert "{x}" not in data.decode()


def test_js_assignment_is_deterministic_and_ends_with_one_lf() -> None:
    value = {"b": 1.23456789, "a": [3, 1]}
    first = js_assignment("HUB", value)
    assert first == js_assignment("HUB", {"a": [3, 1], "b": 1.23456789})
    assert first.endswith(b";\n")
    assert not first.endswith(b"\n\n")
    assert b"\r" not in first


def test_js_assignment_digits() -> None:
    value = {"x": 0.123456789}
    assert json.loads(_body(js_assignment("HUB", value))) == {"x": 0.123457}
    assert json.loads(_body(js_assignment("HUB", value, digits=None))) == value


@pytest.mark.parametrize("name", ["", "hub", "HUB X", "1HUB", "HUB;alert(1)", "window.HUB"])
def test_js_assignment_refuses_bad_names(name: str) -> None:
    with pytest.raises(ValueError):
        js_assignment(name, {})


def test_js_assignment_refuses_nan() -> None:
    with pytest.raises(ValueError):
        js_assignment("HUB", {"x": float("nan")})
