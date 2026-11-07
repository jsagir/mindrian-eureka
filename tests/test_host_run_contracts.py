"""Tests for the host run request rules, the refusal shape and the two published schemas."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
from typing import Any

import pytest
from host_run_support import SCHEMA_DIR, make_request
from jsonschema import Draft202012Validator
from mindrian_eureka.limits import MAX_ARTIFACTS, MAX_TOP_K

LABEL = "candidate, not verified"
SUMMARY_LINE = "All results are candidates, not verified. They are leads for human review."
DIGEST = "a" * 64


def _load(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _short_artifacts(count: int) -> list[dict[str, Any]]:
    return [
        {
            "id": f"item-{index}",
            "source_ref": f"syn://{index}",
            "title": f"Item {index}",
            "text": f"Synthetic text number {index}",
        }
        for index in range(count)
    ]


def _refused(raw: Any) -> Any:
    from mindrian_eureka.host_run.contracts import HostRunError, normalize_request

    with pytest.raises(HostRunError) as caught:
        normalize_request(raw)
    return caught.value


def test_valid_request_normalizes() -> None:
    from mindrian_eureka.host_run.contracts import NormalizedRequest, normalize_request

    request = normalize_request(make_request())
    assert isinstance(request, NormalizedRequest)
    assert len(request.artifacts) == 32
    assert request.top_k == 15
    assert request.approval is None
    for artifact in request.artifacts:
        assert artifact.text_sha256 == hashlib.sha256(artifact.text.encode("utf-8")).hexdigest()


def test_top_k_defaults_to_the_limit() -> None:
    from mindrian_eureka.host_run.contracts import normalize_request

    raw = make_request()
    del raw["top_k"]
    assert normalize_request(raw).top_k == MAX_TOP_K


@pytest.mark.parametrize("key", ["objective", "scope_id", "snapshot_id", "artifacts"])
def test_each_missing_required_key_is_refused(key: str) -> None:
    raw = make_request()
    del raw[key]
    assert _refused(raw).code == "bad_request"


def test_unknown_key_is_refused() -> None:
    raw = make_request(room_path="/home/secret/place")
    error = _refused(raw)
    assert error.code == "bad_request"
    assert "room_path" in error.message
    assert "/home/secret/place" not in error.message
    assert "/home/secret/place" not in error.fix


def test_artifact_count_rules() -> None:
    from mindrian_eureka.host_run.contracts import normalize_request

    assert _refused(make_request(count=1)).code == "bad_request"
    error = _refused(make_request(artifacts=_short_artifacts(MAX_ARTIFACTS + 1)))
    assert error.code == "too_many_artifacts"
    assert "snapshots" in error.fix
    accepted = normalize_request(make_request(artifacts=_short_artifacts(MAX_ARTIFACTS)))
    assert len(accepted.artifacts) == MAX_ARTIFACTS


def test_top_k_rules() -> None:
    from mindrian_eureka.host_run.contracts import normalize_request

    for bad in (0, MAX_TOP_K + 1, 1.5, True):
        assert _refused(make_request(top_k=bad)).code == "bad_request"
    assert normalize_request(make_request(top_k=MAX_TOP_K)).top_k == MAX_TOP_K


def test_external_corpus_is_refused() -> None:
    from mindrian_eureka.host_run.contracts import normalize_request

    raw = make_request(count=3)
    raw["artifacts"][0]["corpus"] = "external"
    assert _refused(raw).code == "external_corpus_refused"
    raw["artifacts"][0]["corpus"] = "room"
    assert len(normalize_request(raw).artifacts) == 3


def test_sha256_must_match_the_text() -> None:
    from mindrian_eureka.host_run.contracts import normalize_request

    raw = make_request(count=3)
    raw["artifacts"][1]["sha256"] = "0" * 64
    error = _refused(raw)
    assert error.code == "artifact_hash_mismatch"
    assert raw["artifacts"][1]["id"] in error.message
    right = hashlib.sha256(raw["artifacts"][1]["text"].encode("utf-8")).hexdigest()
    raw["artifacts"][1]["sha256"] = right
    assert len(normalize_request(raw).artifacts) == 3
    raw["artifacts"][1]["sha256"] = right.upper()
    assert len(normalize_request(raw).artifacts) == 3


def test_duplicate_and_colliding_ids() -> None:
    raw = make_request(count=3)
    raw["artifacts"][1]["id"] = raw["artifacts"][0]["id"]
    assert _refused(raw).code == "duplicate_artifact_id"

    raw = make_request(count=3)
    raw["artifacts"][0]["id"] = "a/b"
    raw["artifacts"][1]["id"] = "a_b"
    error = _refused(raw)
    assert error.code == "id_collision"
    assert "a/b" in error.message
    assert "a_b" in error.message

    raw = make_request(count=3)
    raw["artifacts"][0]["id"] = "..."
    assert _refused(raw).code == "bad_request"


def test_bundle_size_rule() -> None:
    big = "x" * (11 * 1024 * 1024)
    raw = make_request(count=2)
    raw["artifacts"][0]["text"] = big
    raw["artifacts"][1]["text"] = big
    assert _refused(raw).code == "bundle_too_large"
    # 21 texts of 1,000,000 characters stay under the record limit but pass the total limit.
    many = _short_artifacts(21)
    for item in many:
        item["text"] = "y" * 1_000_000
    assert _refused(make_request(artifacts=many)).code == "bundle_too_large"


def test_approval_block_shape() -> None:
    from mindrian_eureka.host_run.contracts import normalize_request

    good = {"plan_digest": DIGEST, "approval_ref": "gate:abc-123"}
    request = normalize_request(make_request(count=3, approval=good))
    assert request.approval is not None
    assert request.approval.plan_digest == DIGEST
    assert request.approval.approval_ref == "gate:abc-123"

    bad_values = [
        {"plan_digest": "abc", "approval_ref": "gate:1"},
        {"plan_digest": "A" * 64, "approval_ref": "gate:1"},
        {"plan_digest": DIGEST, "approval_ref": "has space"},
        {"plan_digest": DIGEST, "approval_ref": "line\nbreak"},
        {"plan_digest": DIGEST, "approval_ref": "a" * 129},
    ]
    for bad in bad_values:
        assert _refused(make_request(count=3, approval=bad)).code == "approval_bad_reference"
    extra = dict(good, note="x")
    assert _refused(make_request(count=3, approval=extra)).code == "bad_request"


def test_refusal_dictionary_shape() -> None:
    from mindrian_eureka.host_run.contracts import REASONS, HostRunError

    secret = "Quartz lanterns drift beyond the orchard wall"
    bad_requests: list[Any] = [
        "not a dict",
        make_request(room_path="/home/x"),
        make_request(count=1),
        make_request(artifacts=_short_artifacts(MAX_ARTIFACTS + 1)),
        make_request(top_k=0),
    ]
    external = make_request(count=3)
    external["artifacts"][0]["corpus"] = "external"
    external["artifacts"][0]["text"] = secret
    bad_requests.append(external)
    mismatch = make_request(count=3)
    mismatch["artifacts"][0]["text"] = secret
    mismatch["artifacts"][0]["sha256"] = "0" * 64
    bad_requests.append(mismatch)
    collision = make_request(count=3)
    collision["artifacts"][0]["id"] = "a/b"
    collision["artifacts"][1]["id"] = "a_b"
    collision["artifacts"][0]["text"] = secret
    bad_requests.append(collision)
    bad_requests.append(make_request(count=3, approval={"plan_digest": "x", "approval_ref": "y"}))

    for raw in bad_requests:
        error = _refused(raw)
        assert error.code in REASONS
        refusal = error.as_refusal()
        assert set(refusal) == {"status", "reason", "message", "fix", "label", "room_write"}
        assert refusal["status"] == "refused"
        assert refusal["reason"] == error.code
        assert refusal["label"] == LABEL
        assert refusal["room_write"] == "not_performed"
        shown = json.dumps(refusal)
        assert secret not in shown
        assert "/home/" not in shown
        assert "/tmp/" not in shown
    assert len(REASONS) == 15
    with pytest.raises(ValueError):
        HostRunError("not_a_code", "message", "fix")


def test_input_schema_is_valid_and_closed() -> None:
    schema = _load("pair-screen-input.v1.json")
    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == "eureka.pair-screen-input.v1"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"objective", "scope_id", "snapshot_id", "artifacts"}
    assert schema["properties"]["artifacts"]["maxItems"] == MAX_ARTIFACTS
    assert schema["properties"]["artifacts"]["minItems"] == 2
    assert schema["properties"]["top_k"]["maximum"] == MAX_TOP_K
    assert schema["$defs"]["ArtifactInput"]["properties"]["corpus"]["enum"] == ["room"]

    validator = Draft202012Validator(schema)
    sample = {
        "objective": "Find pairs",
        "scope_id": "room:a",
        "snapshot_id": "snap:1",
        "top_k": 20,
        "artifacts": _short_artifacts(3),
        "approval": {"plan_digest": DIGEST, "approval_ref": "gate:1"},
    }
    assert not list(validator.iter_errors(sample))

    external = copy.deepcopy(sample)
    external["artifacts"][0]["corpus"] = "external"
    extra = dict(sample, room_path="/x")
    too_deep = dict(sample, top_k=MAX_TOP_K + 1)
    one = dict(sample, artifacts=_short_artifacts(1))
    for bad in (external, extra, too_deep, one):
        assert list(validator.iter_errors(bad))


def _minimal_result() -> dict[str, Any]:
    return {
        "schema_version": "eureka.pair-screen.v1",
        "capability_id": "opportunity.run_pair_screen",
        "status": "completed",
        "job_id": "job-1",
        "label": LABEL,
        "summary_line": SUMMARY_LINE,
        "scope": {"scope_id": "room:a", "snapshot_id": "snap:1"},
        "approval": {
            "plan_digest": DIGEST,
            "approval_ref": "gate:1",
            "verified_by_engine": False,
        },
        "counts": {
            "records_read": 3,
            "records_used": 3,
            "dropped": 0,
            "unusual_pairs": 1,
            "wording_and_meaning_pairs": 1,
        },
        "caps_hit": [],
        "warnings": [],
        "manifest_sha256": "b" * 64,
        "files": [
            {
                "path": "manifest.json",
                "bytes": 10,
                "sha256": "c" * 64,
                "inline": True,
                "content": "{}",
            },
            {"path": "pairs.csv", "bytes": 99, "sha256": "d" * 64, "inline": False},
        ],
        "id_map": [{"record_id": "artifacts/a", "artifact_id": "a", "source_ref": "syn://a"}],
        "outputs": [
            {
                "id": "pair-1",
                "kind": "pair",
                "engines": ["unusual_pairs", "wording_and_meaning"],
                "payload": {
                    "left": {
                        "artifact_id": "a",
                        "record_id": "artifacts/a",
                        "source_ref": "syn://a",
                        "title": "A",
                    },
                    "right": {
                        "artifact_id": "b",
                        "record_id": "artifacts/b",
                        "source_ref": "syn://b",
                        "title": "B",
                    },
                    "ranks": {"unusual_pairs": 1, "wording_and_meaning": None},
                },
            }
        ],
        "host_handoff": {"state": "not_filed", "owner": "host"},
        "room_write": "not_performed",
        "portfolio_write": "not_performed",
        "persistence": {
            "job_store": "local",
            "derived_vectors": "local",
            "run_files": "local",
        },
    }


def test_output_schema_is_valid_and_closed() -> None:
    schema = _load("pair-screen-output.v1.json")
    Draft202012Validator.check_schema(schema)
    assert schema["$id"] == "eureka.pair-screen.v1"
    assert schema["additionalProperties"] is False
    validator = Draft202012Validator(schema)
    assert not list(validator.iter_errors(_minimal_result()))

    performed = _minimal_result()
    performed["room_write"] = "performed"
    no_scope = _minimal_result()
    del no_scope["scope"]
    verified = _minimal_result()
    verified["approval"]["verified_by_engine"] = True
    no_content = _minimal_result()
    del no_content["files"][0]["content"]
    content_without_inline = _minimal_result()
    content_without_inline["files"][1]["content"] = "x"
    extra = _minimal_result()
    extra["unexpected"] = 1
    for bad in (performed, no_scope, verified, no_content, content_without_inline, extra):
        assert list(validator.iter_errors(bad))


def test_package_imports_stay_light() -> None:
    code = (
        "import sys\n"
        "import mindrian_eureka.host_run.contracts\n"
        "import mindrian_eureka.host_run.bundle\n"
        "heavy = {'numpy','sklearn','scipy','torch','pydantic','mcp','sentence_transformers'}\n"
        "print(sorted(set(sys.modules) & heavy))\n"
    )
    source = str(SCHEMA_DIR.parents[2])
    env = dict(os.environ, PYTHONPATH=source)
    done = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False, env=env
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip() == "[]"
