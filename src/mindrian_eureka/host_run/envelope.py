"""Build the result envelope of a pair screen run from a finished run folder.

The envelope holds the exact text of the small output files, so a host can check each
sha256 with plain code. The corpus file is listed by hash only, because it holds the
host text. The builder checks every listed file against `manifest.json` before it
returns, so a file that changed after the run is refused.

The module only reads the run folder. It does not write, read a clock or call a network.
It reads no file that holds times. It imports no numpy.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

from mindrian_eureka.host_run.bundle import StagedArtifact
from mindrian_eureka.host_run.contracts import CAPABILITY_ID, RESULT_SCHEMA, Approval
from mindrian_eureka.opportunity_pairs.host_handoff import host_handoff
from mindrian_eureka.run.contracts import LABEL, SUMMARY_LINE, sha256_bytes

__all__ = ["build_result"]

_MANIFEST: Final[str] = "manifest.json"
_RECORDS: Final[str] = "corpus/records.jsonl"
_MARKDOWN: Final[str] = "ranked-pairs.md"
_UNUSUAL: Final[str] = "unusual-pairs.json"
_WORDING: Final[str] = "wording-and-meaning-pairs.json"
_LISTED: Final[tuple[str, ...]] = (_RECORDS, _MARKDOWN, _UNUSUAL, _WORDING)
_ENGINES: Final[tuple[tuple[str, str], ...]] = (
    ("unusual_pairs", _UNUSUAL),
    ("wording_and_meaning", _WORDING),
)
_PERSISTENCE: Final[dict[str, str]] = {
    "job_store": (
        "This result is kept in the local job store for 30 days. Delete it with scout_delete_job."
    ),
    "derived_vectors": "not kept",
    "run_files": "The private run folder was deleted after this result was built.",
}


def _read(run_dir: Path, name: str) -> bytes:
    """Read one file of the run folder by its fixed name."""
    try:
        return (run_dir / name).read_bytes()
    except OSError:
        raise ValueError(f"{name} is missing from the run folder.") from None


def _parse(name: str, data: bytes) -> dict[str, Any]:
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ValueError(f"{name} is not valid JSON text.") from None
    if not isinstance(value, dict):
        raise ValueError(f"{name} does not hold a JSON object.")
    return value


def _listed_hashes(manifest: Mapping[str, Any]) -> dict[str, str]:
    listed: dict[str, str] = {}
    outputs = manifest.get("outputs")
    if not isinstance(outputs, list):
        raise ValueError(f"{_MANIFEST} does not list the output files.")
    for item in outputs:
        if isinstance(item, dict) and isinstance(item.get("path"), str):
            listed[item["path"]] = str(item.get("sha256", ""))
    return listed


def _checked_files(run_dir: Path, listed: Mapping[str, str]) -> dict[str, bytes]:
    """Read the four listed files and compare each with the hash in the manifest."""
    contents: dict[str, bytes] = {}
    for name in _LISTED:
        data = _read(run_dir, name)
        if name not in listed or sha256_bytes(data) != listed[name]:
            raise ValueError(f"{name} does not match the hash in {_MANIFEST}.")
        contents[name] = data
    return contents


def _file_item(path: str, data: bytes, inline: bool) -> dict[str, Any]:
    item: dict[str, Any] = {
        "path": path,
        "bytes": len(data),
        "sha256": sha256_bytes(data),
        "inline": inline,
    }
    if inline:
        try:
            item["content"] = data.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"{path} is not valid UTF-8 text.") from None
    return item


def _side(
    record_id: str, title: str, id_map: Mapping[str, StagedArtifact], position: str
) -> dict[str, str]:
    host = id_map.get(record_id)
    if host is None:
        raise ValueError(f"The {position} side of a pair has a record id that the id map lacks.")
    return {
        "artifact_id": host.artifact_id,
        "record_id": record_id,
        "source_ref": host.source_ref,
        "title": title,
    }


def _collect_pairs(
    documents: Mapping[str, Mapping[str, Any]], id_map: Mapping[str, StagedArtifact]
) -> list[dict[str, Any]]:
    """Return one output item for each distinct pair id over both engines."""
    found: dict[str, dict[str, Any]] = {}
    for engine, _ in _ENGINES:
        for pair in documents[engine].get("pairs", []):
            pair_id = pair["pair_id"]
            item = found.get(pair_id)
            if item is None:
                left, right = pair["left"], pair["right"]
                item = {
                    "id": pair_id,
                    "kind": "pair",
                    "engines": [],
                    "payload": {
                        "left": _side(left["id"], str(left.get("title", "")), id_map, "left"),
                        "right": _side(right["id"], str(right.get("title", "")), id_map, "right"),
                        "ranks": {name: None for name, _ in _ENGINES},
                    },
                }
                found[pair_id] = item
            item["engines"].append(engine)
            item["payload"]["ranks"][engine] = int(pair["rank"])

    def order(item: dict[str, Any]) -> tuple[int, int, str]:
        ranks = [rank for rank in item["payload"]["ranks"].values() if rank is not None]
        return (-len(item["engines"]), min(ranks), item["id"])

    return sorted(found.values(), key=order)


def _counts(
    manifest: Mapping[str, Any], documents: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    corpus = manifest.get("corpus")
    if not isinstance(corpus, dict):
        raise ValueError(f"{_MANIFEST} has no corpus section.")
    counts: dict[str, Any] = {
        "records_read": int(corpus["records_read"]),
        "records_used": int(corpus["records_used"]),
        "dropped": len(corpus.get("dropped", [])),
        "unusual_pairs": int(documents["unusual_pairs"]["counts"]["pairs"]),
        "wording_and_meaning_pairs": int(documents["wording_and_meaning"]["counts"]["pairs"]),
    }
    classes = {
        name: documents[name]["counts"]["pair_classes"]
        for name, _ in _ENGINES
        if "pair_classes" in documents[name]["counts"]
    }
    if len(classes) == len(_ENGINES):
        counts["pair_classes"] = classes
    return counts


def _warnings(documents: Mapping[str, Mapping[str, Any]]) -> list[str]:
    seen: dict[str, None] = {}
    for name, _ in _ENGINES:
        for note in documents[name].get("notes", []):
            seen.setdefault(str(note), None)
    return list(seen)


def build_result(
    run_dir: Path,
    *,
    id_map: Mapping[str, StagedArtifact],
    scope_id: str,
    snapshot_id: str,
    approval: Approval,
    job_id: str,
) -> dict[str, Any]:
    """Turn a finished run folder into a checked result envelope.

    Args:
        run_dir: The output folder of `run_pipeline`.
        id_map: Record id to host artifact id and source reference.
        scope_id: The scope id of the request.
        snapshot_id: The snapshot id of the request.
        approval: The approval block of the request. The engine cannot verify it.
        job_id: The job id. It appears only in the key `job_id`.

    Returns:
        A dictionary that validates against `pair-screen-output.v1.json`. The optional key
        `encoder` is a deep copy of the `encoder` block of the manifest. It is absent when
        the run folder has no such block (a folder made before plan 05-05).

    Raises:
        ValueError: A listed file is missing or does not match `manifest.json`, or a
            pair names a record id that the id map lacks. The message names a file
            or a side. It holds no path.
    """
    manifest_bytes = _read(run_dir, _MANIFEST)
    manifest = _parse(_MANIFEST, manifest_bytes)
    contents = _checked_files(run_dir, _listed_hashes(manifest))
    documents = {name: _parse(path, contents[path]) for name, path in _ENGINES}

    files = [_file_item(_MANIFEST, manifest_bytes, True)]
    files.extend(_file_item(name, contents[name], name != _RECORDS) for name in _LISTED)
    files.sort(key=lambda item: item["path"])

    outputs = _collect_pairs(documents, id_map)
    status = "completed" if outputs else "completed_empty"
    handoff = host_handoff(status, [{"id": item["id"]} for item in outputs])
    ids = [
        {"record_id": record_id, "artifact_id": host.artifact_id, "source_ref": host.source_ref}
        for record_id, host in sorted(id_map.items())
    ]
    caps = manifest["corpus"].get("caps_hit", [])
    result: dict[str, Any] = {
        "schema_version": RESULT_SCHEMA,
        "capability_id": CAPABILITY_ID,
        "status": status,
        "job_id": job_id,
        "label": LABEL,
        "summary_line": SUMMARY_LINE,
        "scope": {"scope_id": scope_id, "snapshot_id": snapshot_id},
        "approval": {
            "plan_digest": approval.plan_digest,
            "approval_ref": approval.approval_ref,
            "verified_by_engine": False,
        },
        "counts": _counts(manifest, documents),
        "caps_hit": list(caps),
        "warnings": _warnings(documents),
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "files": files,
        "id_map": ids,
        "outputs": outputs,
        "host_handoff": handoff,
        "room_write": "not_performed",
        "portfolio_write": "not_performed",
        "persistence": dict(_PERSISTENCE),
    }
    block = manifest.get("encoder")
    if isinstance(block, Mapping):
        result["encoder"] = copy.deepcopy(dict(block))
    return result
