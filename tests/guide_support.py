"""Replay record contract for the reproduction guide.

The guide docs/reproduce-the-jhtv-method.md holds one marked block that states the outcome
of the graph-derive replay. This module defines where the outcome is read from and how the
block text is built from it. No other file is a source of the replay outcome.

This module holds no test function.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from test_release_gate_record import parse_front_matter

ROOT = Path(__file__).resolve().parents[1]
REPLAY_RECORD_PATH = ROOT / "docs" / "jhtv-replay-record.md"
RECORD_SENTENCE = "Record: docs/jhtv-replay-record.md."

BEGIN = "<!-- replay-outcome:begin -->"
END = "<!-- replay-outcome:end -->"

CITED_CLAIMS = 2130
CITED_PAIRS = 2267385

OUTCOMES = ("provenance_gap", "replayed")
ROOM_MARKS = ("done", "pending_approval")

PENDING_TEXT = (
    "Replay outcome: not recorded yet. Phase 3 has not produced its result, "
    "so this guide makes no claim about the replay. This is not a verified statement."
)


def read_replay_record(path: Path = REPLAY_RECORD_PATH) -> dict[str, Any] | None:
    """Read the front matter of the replay record.

    Args:
        path: The record file.

    Returns:
        The front matter as a dict, or None when the file does not exist.

    Raises:
        ValueError: The `outcome` key is missing or is not a known outcome.
    """
    if not path.exists():
        return None
    front = parse_front_matter(path.read_text(encoding="utf-8"))
    outcome = front.get("outcome")
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome must be one of {OUTCOMES}, got {outcome!r}")
    return front


def _count(record: dict[str, Any], key: str) -> int:
    value = record.get(key)
    if not isinstance(value, str) or not value.isdigit():
        raise ValueError(f"{key} must be a whole number in the replay record")
    return int(value)


def replay_statement(record: dict[str, Any]) -> str:
    """Build the one-paragraph replay statement from a record.

    Args:
        record: The front matter of the replay record.

    Returns:
        The statement as one paragraph on one line.

    Raises:
        ValueError: The outcome is unknown, a key is missing, or the two run hashes differ.
    """
    outcome = record.get("outcome")
    if outcome == "provenance_gap":
        mark = record.get("room_mark")
        if mark not in ROOM_MARKS:
            raise ValueError(f"room_mark must be one of {ROOM_MARKS}, got {mark!r}")
        if mark == "done":
            mark_sentence = "The provenance-gap mark is made in the room."
        else:
            mark_sentence = "The provenance-gap mark in the room waits for a host approval step."
        return (
            "Replay outcome: provenance gap. "
            f"The replay of 2026-10-21 ({CITED_CLAIMS:,} claims and {CITED_PAIRS:,} pairs) "
            "has no script and no result file, so it cannot be reproduced. "
            "Five candidates, OPP-027 to OPP-031, cite it. "
            f"{mark_sentence} "
            "Each of these candidates stays a candidate, not verified. "
            f"{RECORD_SENTENCE}"
        )
    if outcome == "replayed":
        if record.get("two_run_hashes_equal") != "true":
            raise ValueError("two_run_hashes_equal must be true for a replayed outcome")
        claims = _count(record, "claims")
        pairs = _count(record, "pairs")
        if claims == CITED_CLAIMS and pairs == CITED_PAIRS:
            counts = "The counts are equal."
        else:
            counts = (
                f"The counts differ: claims {claims:,} against {CITED_CLAIMS:,} "
                f"and pairs {pairs:,} against {CITED_PAIRS:,}."
            )
        return (
            "Replay outcome: replayed. "
            "A recorded script rebuilds the replay, and two runs give the same output hashes. "
            f"The rebuilt replay has {claims:,} claims and {pairs:,} pairs. "
            f"The cited replay has {CITED_CLAIMS:,} claims and {CITED_PAIRS:,} pairs. "
            f"{counts} "
            "The replay result is a candidate, not verified. "
            f"{RECORD_SENTENCE}"
        )
    raise ValueError(f"unknown outcome {outcome!r}")


def replay_block(text: str) -> str:
    """Return the text between the replay markers, stripped.

    Args:
        text: The guide text.

    Returns:
        The stripped block text.

    Raises:
        ValueError: A marker is missing or repeated, or the begin marker is not first.
    """
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError("each replay marker must appear exactly once")
    start = text.index(BEGIN)
    stop = text.index(END)
    if start > stop:
        raise ValueError("the begin marker must come before the end marker")
    return text[start + len(BEGIN) : stop].strip()
