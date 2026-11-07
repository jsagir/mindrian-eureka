"""Tests for the result envelope of the pair screen run (host_run/envelope.py)."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from host_run_support import FROZEN_RUN, SCHEMA_DIR
from jsonschema import Draft202012Validator

UNUSUAL = "unusual-pairs.json"
WORDING = "wording-and-meaning-pairs.json"
MARKDOWN = "ranked-pairs.md"
MANIFEST = "manifest.json"
RECORDS = "corpus/records.jsonl"
INLINE_PATHS = [MANIFEST, MARKDOWN, UNUSUAL, WORDING]
ALL_PATHS = sorted([RECORDS, *INLINE_PATHS])
DIGEST = "c" * 64
JOB_ID = "eureka-" + "b" * 32


def _approval() -> Any:
    from mindrian_eureka.host_run.contracts import Approval

    return Approval(plan_digest=DIGEST, approval_ref="gate:test-1")


def _record_ids(run_dir: Path) -> list[str]:
    ids = []
    for line in (run_dir / RECORDS).read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        if item.get("record_type") == "record":
            ids.append(item["id"])
    return ids


def _id_map(run_dir: Path) -> dict[str, Any]:
    from mindrian_eureka.host_run.bundle import StagedArtifact

    return {
        record_id: StagedArtifact("host-" + record_id, "s://" + record_id)
        for record_id in _record_ids(run_dir)
    }


def _copy_run(tmp_path: Path, name: str = "run") -> Path:
    target = tmp_path / name
    shutil.copytree(FROZEN_RUN, target)
    return target


def _build(run_dir: Path, id_map: dict[str, Any] | None = None, job_id: str = JOB_ID) -> Any:
    from mindrian_eureka.host_run.envelope import build_result

    return build_result(
        run_dir,
        id_map=id_map if id_map is not None else _id_map(run_dir),
        scope_id="room:test-scope",
        snapshot_id="snapshot:test-1",
        approval=_approval(),
        job_id=job_id,
    )


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, value: Any) -> bytes:
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2).encode("utf-8")
    path.write_bytes(data)
    return data


def _empty_copy(tmp_path: Path) -> Path:
    run_dir = _copy_run(tmp_path, "empty-run")
    manifest = json.loads((run_dir / MANIFEST).read_text(encoding="utf-8"))
    listed = {item["path"]: item for item in manifest["outputs"]}
    for name in (UNUSUAL, WORDING):
        document = json.loads((run_dir / name).read_text(encoding="utf-8"))
        document["pairs"] = []
        document["counts"]["pairs"] = 0
        data = _write_json(run_dir / name, document)
        listed[name]["sha256"] = _sha(data)
        listed[name]["bytes"] = len(data)
        listed[name]["pairs"] = 0
    _write_json(run_dir / MANIFEST, manifest)
    return run_dir


def _pairs(run_dir: Path, name: str) -> list[dict[str, Any]]:
    document = json.loads((run_dir / name).read_text(encoding="utf-8"))
    pairs: list[dict[str, Any]] = document["pairs"]
    return pairs


def _validator() -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / "pair-screen-output.v1.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def test_result_validates_against_the_output_schema(tmp_path: Path) -> None:
    result = _build(_copy_run(tmp_path))
    errors = sorted(_validator().iter_errors(result), key=lambda error: list(error.path))
    assert errors == []


def test_files_list_and_inline_rules(tmp_path: Path) -> None:
    run_dir = _copy_run(tmp_path)
    result = _build(run_dir)
    files = result["files"]
    assert [item["path"] for item in files] == ALL_PATHS
    by_path = {item["path"]: item for item in files}
    assert by_path[RECORDS]["inline"] is False
    assert "content" not in by_path[RECORDS]
    for path in INLINE_PATHS:
        item = by_path[path]
        assert item["inline"] is True
        data = item["content"].encode("utf-8")
        assert item["sha256"] == _sha(data)
        assert item["bytes"] == len(data)
        assert item["content"] == (run_dir / path).read_text(encoding="utf-8")
    assert by_path[MANIFEST]["sha256"] == result["manifest_sha256"]
    manifest = json.loads((run_dir / MANIFEST).read_text(encoding="utf-8"))
    listed = {item["path"]: item for item in manifest["outputs"]}
    assert by_path[RECORDS]["sha256"] == listed[RECORDS]["sha256"]
    assert by_path[RECORDS]["bytes"] == listed[RECORDS]["bytes"]


def test_hash_mismatch_is_refused(tmp_path: Path) -> None:
    run_dir = _copy_run(tmp_path)
    id_map = _id_map(run_dir)
    target = run_dir / UNUSUAL
    data = bytearray(target.read_bytes())
    data[-3] = data[-3] ^ 0x01
    target.write_bytes(bytes(data))
    with pytest.raises(ValueError) as caught:
        _build(run_dir, id_map)
    assert UNUSUAL in str(caught.value)
    assert "/home/" not in str(caught.value)
    assert str(tmp_path) not in str(caught.value)

    missing_dir = _copy_run(tmp_path, "missing-run")
    (missing_dir / MARKDOWN).unlink()
    with pytest.raises(ValueError) as caught_missing:
        _build(missing_dir, id_map)
    assert MARKDOWN in str(caught_missing.value)
    assert str(tmp_path) not in str(caught_missing.value)


def test_outputs_are_unique_pairs_with_ranks(tmp_path: Path) -> None:
    run_dir = _copy_run(tmp_path)
    result = _build(run_dir)
    ranks: dict[str, dict[str, int]] = {}
    for engine, name in (("unusual_pairs", UNUSUAL), ("wording_and_meaning", WORDING)):
        for pair in _pairs(run_dir, name):
            ranks.setdefault(pair["pair_id"], {})[engine] = pair["rank"]
    outputs = result["outputs"]
    assert {item["id"] for item in outputs} == set(ranks)
    assert len(outputs) == len(ranks)
    assert len(outputs) == 63 + 200 - sum(1 for held in ranks.values() if len(held) == 2)
    order = ("unusual_pairs", "wording_and_meaning")
    for item in outputs:
        assert item["kind"] == "pair"
        held = ranks[item["id"]]
        assert item["engines"] == [engine for engine in order if engine in held]
        assert item["payload"]["ranks"] == {engine: held.get(engine) for engine in order}
        for side in ("left", "right"):
            part = item["payload"][side]
            assert set(part) >= {"artifact_id", "record_id", "source_ref", "title"}
            assert all(isinstance(part[key], str) for key in ("artifact_id", "record_id"))
            assert part["artifact_id"] == "host-" + part["record_id"]
            assert part["source_ref"] == "s://" + part["record_id"]
    keys = [
        (-len(item["engines"]), min(r for r in item["payload"]["ranks"].values() if r), item["id"])
        for item in outputs
    ]
    assert keys == sorted(keys)


def test_unknown_record_id_is_refused(tmp_path: Path) -> None:
    run_dir = _copy_run(tmp_path)
    id_map = _id_map(run_dir)
    first_pair = _pairs(run_dir, UNUSUAL)[0]
    del id_map[first_pair["left"]["id"]]
    with pytest.raises(ValueError):
        _build(run_dir, id_map)


def test_counts_caps_and_warnings_come_from_the_files(tmp_path: Path) -> None:
    run_dir = _copy_run(tmp_path)
    result = _build(run_dir)
    manifest = json.loads((run_dir / MANIFEST).read_text(encoding="utf-8"))
    corpus = manifest["corpus"]
    unusual = json.loads((run_dir / UNUSUAL).read_text(encoding="utf-8"))
    wording = json.loads((run_dir / WORDING).read_text(encoding="utf-8"))
    counts = result["counts"]
    assert counts["records_read"] == corpus["records_read"]
    assert counts["records_used"] == corpus["records_used"]
    assert counts["dropped"] == len(corpus["dropped"])
    assert counts["unusual_pairs"] == unusual["counts"]["pairs"]
    assert counts["wording_and_meaning_pairs"] == wording["counts"]["pairs"]
    assert result["caps_hit"] == corpus["caps_hit"]
    expected: list[str] = []
    for note in [*unusual["notes"], *wording["notes"]]:
        if note not in expected:
            expected.append(note)
    assert result["warnings"] == expected
    assert len(result["warnings"]) == len(set(result["warnings"]))


def test_scope_approval_and_labels(tmp_path: Path) -> None:
    from mindrian_eureka.run.contracts import LABEL, SUMMARY_LINE

    result = _build(_copy_run(tmp_path))
    assert result["scope"] == {"scope_id": "room:test-scope", "snapshot_id": "snapshot:test-1"}
    assert result["approval"] == {
        "plan_digest": DIGEST,
        "approval_ref": "gate:test-1",
        "verified_by_engine": False,
    }
    assert result["label"] == LABEL == "candidate, not verified"
    assert result["summary_line"] == SUMMARY_LINE
    assert result["room_write"] == "not_performed"
    assert result["portfolio_write"] == "not_performed"
    assert result["capability_id"] == "opportunity.run_pair_screen"
    assert result["schema_version"] == "eureka.pair-screen.v1"
    assert result["job_id"] == JOB_ID
    assert set(result["persistence"]) == {"job_store", "derived_vectors", "run_files"}
    assert result["persistence"]["derived_vectors"] == "not kept"


def test_host_handoff_for_a_full_and_an_empty_result(tmp_path: Path) -> None:
    full = _build(_copy_run(tmp_path))
    assert full["status"] == "completed"
    assert full["host_handoff"]["state"] == "awaiting_mindrianos_review"
    assert full["host_handoff"]["candidate_ids"] == [item["id"] for item in full["outputs"]]
    assert full["outputs"]

    empty_dir = _empty_copy(tmp_path)
    empty = _build(empty_dir)
    assert empty["status"] == "completed_empty"
    assert empty["outputs"] == []
    assert empty["host_handoff"]["state"] == "review_scope"
    assert empty["counts"]["unusual_pairs"] == 0
    assert _validator().is_valid(empty)


def test_result_is_deterministic_and_clean(tmp_path: Path) -> None:
    run_dir = _copy_run(tmp_path)
    first = _build(run_dir)
    second = _build(run_dir)
    assert first == second
    text = json.dumps(first, sort_keys=True)
    assert "/home/" not in text
    assert "/tmp/" not in text
    assert text.count(JOB_ID) == 1
    assert len(text.encode("utf-8")) < 2 * 1024 * 1024


def test_envelope_module_is_light() -> None:
    code = (
        "import sys\n"
        "import mindrian_eureka.host_run.envelope\n"
        "heavy = ['numpy', 'sklearn', 'scipy', 'torch', 'pydantic', 'mcp']\n"
        "print(sorted(name for name in heavy if name in sys.modules))\n"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert done.stdout.strip() == "[]"
