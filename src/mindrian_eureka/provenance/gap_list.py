"""Emit the list of candidates that carry a provenance gap mark (Phase 3, HOST-02).

The graph-derive replay behind five partner candidates cannot be rebuilt from this repo. The
machine record `evaluations/graph-derive-replay/record.v1.json` states that outcome. This module
reads the record, checks the pair-count identity and emits the list for the host as byte-stable
JSON or plain text.

The module is offline and deterministic. It reads one record file, writes to stdout and stderr
only, reads no room, calls no model and reads no clock. The room mark is a host-owned write that
needs approval. Eureka writes nothing to a room.

Exit codes: 0 for success, 1 for an arithmetic failure or a golden mismatch, 2 for bad input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import jsonschema

LIST_SCHEMA_VERSION = "eureka.provenance-gap-list.v1"
LABEL = "candidate, not verified"
MARK = "provenance gap"
HAND_OFF_SENTENCE = "The room mark is a host-owned write that needs approval."

_PACKAGE_DIR = Path(__file__).resolve().parents[1]
_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_DIR = _PACKAGE_DIR / "data" / "schemas"
DEFAULT_RECORD = _ROOT / "evaluations" / "graph-derive-replay" / "record.v1.json"
GOLDEN_NAME = "gap-list.v1.json"

MARK_TEXT = (
    "Provenance gap. The replay that found this candidate cannot be reproduced from stored files: "
    "the output file it cites (derive_results.json, 2026-10-21) was not found, and no script was "
    "kept. The candidate stays a lead, candidate, not verified. The similarity behind it is a "
    "screening signal, not a verified relationship."
)
CITES = "derive_results.json (2026-10-21)"
HOST_ACTION = (
    "Add this mark to the opportunity in the room after the navigator approves the write. "
    "Eureka writes nothing to a room."
)


class GapListError(Exception):
    """A record is unreadable, fails its schema or fails the pair-count identity."""


class _BadInput(GapListError):
    """The input cannot be used. The command exits with code 2."""


def _schema(name: str) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((_SCHEMA_DIR / name).read_text(encoding="utf-8"))
    return loaded


def _validate(doc: Any, schema_name: str, what: str) -> None:
    validator = jsonschema.Draft202012Validator(_schema(schema_name))
    errors = sorted(validator.iter_errors(doc), key=lambda e: [str(p) for p in e.absolute_path])
    if errors:
        first = errors[0]
        place = ".".join(str(p) for p in first.absolute_path) or "top level"
        message = first.message.splitlines()[0][:160]
        raise _BadInput(f"{what} fails its schema at {place}: {message}")


def _read_record_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        raise _BadInput("record file not found; pass --record") from None
    except OSError:
        raise _BadInput("record file cannot be read") from None


def _parse_record(record_bytes: bytes) -> dict[str, Any]:
    try:
        record = json.loads(record_bytes)
    except ValueError:
        raise _BadInput("record file is not valid JSON") from None
    _validate(record, "provenance-gap-record.v1.json", "record")
    assert isinstance(record, dict)
    return record


def load_record(path: Path) -> dict[str, Any]:
    """Read a record file, parse it and validate it against the record schema."""
    return _parse_record(_read_record_bytes(Path(path)))


def verify_arithmetic(record: dict[str, Any]) -> None:
    """Check that every pair count equals n * (n - 1) / 2. Raise GapListError if not."""
    pairs_to_check: list[tuple[str, int, int]] = []
    for entry in record["identity_checks"]:
        pairs_to_check.append(("identity check", entry["n"], entry["pairs"]))
    replay = record["replay"]
    pairs_to_check.append(("replay figures", replay["claims_cited"], replay["pairs_cited"]))
    proof = record["count_proof"]
    pairs_to_check.append(("count proof", proof["stored_vectors"], proof["all_pairs"]))
    for what, n, total in pairs_to_check:
        if n * (n - 1) // 2 != total:
            raise GapListError(f"pair count mismatch in {what}: {n} items give {n * (n - 1) // 2}")


def build_list(record: dict[str, Any], record_bytes: bytes) -> dict[str, Any]:
    """Build the gap list document from a validated record."""
    replay = record["replay"]
    return {
        "schema_version": LIST_SCHEMA_VERSION,
        "label": LABEL,
        "outcome": record["outcome"],
        "room_mark": record["room_mark"],
        "verdict": record["verdict"],
        "record_sha256": hashlib.sha256(record_bytes).hexdigest(),
        "replay": {
            "name": replay["name"],
            "date_cited": replay["date_cited"],
            "claims_cited": replay["claims_cited"],
            "pairs_cited": replay["pairs_cited"],
            "similarity_floor_cited": replay["similarity_floor_cited"],
            "edge_type_cited": replay["edge_type_cited"],
            "embedding_model_cited": replay["embedding_model_cited"],
            "output_file_cited": replay["output_file_cited"],
            "artifact_found": replay["artifact_found"],
        },
        "items": [
            {
                "opportunity_id": item["opportunity_id"],
                "mark": MARK,
                "mark_text": MARK_TEXT,
                "cites": CITES,
                "host_action": HOST_ACTION,
            }
            for item in record["items"]
        ],
        "closes_when": list(record["closes_when"]),
        "write_boundary": record["write_boundary"],
    }


def render_json(doc: dict[str, Any]) -> bytes:
    """Return the list as byte-stable JSON: sorted keys, 2 space indent, UTF-8, one newline."""
    return (json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def render_text(doc: dict[str, Any]) -> str:
    """Return the list as plain text, one block for each candidate."""
    lines = [
        f"Candidates to mark with a {MARK} ({doc['label']})",
        f"Outcome: {doc['outcome']}. Room mark: {doc['room_mark']}.",
        "",
    ]
    for item in doc["items"]:
        lines.append(f"{item['opportunity_id']}: {item['mark']}")
        lines.append(f"  {item['mark_text']}")
        lines.append(f"  Cites: {item['cites']}")
        lines.append(f"  Host action: {item['host_action']}")
        lines.append("")
    lines.append("This gap closes when one of these holds:")
    for entry in doc["closes_when"]:
        lines.append(f"  * {entry}")
    lines.append("")
    lines.append(HAND_OFF_SENTENCE)
    lines.append(doc["write_boundary"])
    lines.append(f"Label: {doc['label']}")
    return "\n".join(lines) + "\n"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="emit-provenance-gap-list",
        description="Emit the list of candidates that carry a provenance gap mark.",
    )
    parser.add_argument("--record", type=Path, default=DEFAULT_RECORD, help="machine record file")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--check", action="store_true", help="compare the JSON with the golden")
    parser.add_argument("--golden", type=Path, default=None, help="golden file for --check")
    return parser


def _fail(message: str, code: int) -> int:
    sys.stderr.write(message + "\n")
    return code


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        record_bytes = _read_record_bytes(args.record)
        record = _parse_record(record_bytes)
    except _BadInput as exc:
        return _fail(str(exc), 2)
    try:
        verify_arithmetic(record)
    except GapListError as exc:
        return _fail(str(exc), 1)
    doc = build_list(record, record_bytes)
    json_bytes = render_json(doc)
    if args.check:
        golden_path = args.golden or args.record.parent / GOLDEN_NAME
        try:
            golden_bytes = golden_path.read_bytes()
        except OSError:
            return _fail("golden file cannot be read", 2)
        sys.stderr.write("sha256 " + hashlib.sha256(json_bytes).hexdigest() + "\n")
        if golden_bytes != json_bytes:
            return _fail("golden mismatch: the list differs from the golden file", 1)
        return 0
    out = json_bytes if args.format == "json" else render_text(doc).encode("utf-8")
    sys.stdout.buffer.write(out)
    sys.stdout.buffer.flush()
    sys.stderr.write("sha256 " + hashlib.sha256(out).hexdigest() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
