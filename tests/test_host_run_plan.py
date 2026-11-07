"""Tests for the plan builder of the host pair screen run."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from host_run_support import make_request

LABEL = "candidate, not verified"
READY_KEYS = {
    "schema_version",
    "status",
    "label",
    "capability_id",
    "plan_digest",
    "expires_at",
    "scope_id",
    "snapshot_id",
    "objective",
    "top_k",
    "counts",
    "engines",
    "model",
    "outputs_expected",
    "network",
    "writes",
    "approval_required",
    "how_to_approve",
    "stages",
    "warnings",
    "host_handoff",
}
MODEL_VARIABLE = "MINDRIAN_EUREKA_RS_MODEL_PATH"


def _plan(tmp_path: Path, raw: dict[str, Any]) -> tuple[dict[str, Any], Any, Path]:
    from mindrian_eureka.host_run.contracts import normalize_request
    from mindrian_eureka.host_run.gate import PlanReceipts
    from mindrian_eureka.host_run.plan import build_plan

    data_dir = tmp_path / "data"
    receipts = PlanReceipts(data_dir)
    plan = build_plan(normalize_request(raw), receipts, data_dir=data_dir)
    return plan, receipts, data_dir


def _receipt_rows(data_dir: Path) -> int:
    path = data_dir / "plan-receipts.sqlite3"
    if not path.exists():
        return 0
    connection = sqlite3.connect(path)
    try:
        return int(connection.execute("SELECT COUNT(*) FROM receipts").fetchone()[0])
    finally:
        connection.close()


@pytest.fixture
def with_model(
    isolated_env: Path, fake_model_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    monkeypatch.setenv(MODEL_VARIABLE, str(fake_model_dir))
    return fake_model_dir


def test_ready_plan_keys_and_content(tmp_path: Path, with_model: Path) -> None:
    from mindrian_eureka.host_run.contracts import (
        CAPABILITY_ID,
        PLAN_SCHEMA,
        normalize_request,
    )
    from mindrian_eureka.host_run.gate import plan_digest
    from mindrian_eureka.run.contracts import (
        UNUSUAL_PAIRS_CAPABILITY,
        UNUSUAL_PAIRS_NAME,
        WORDING_AND_MEANING_CAPABILITY,
        WORDING_AND_MEANING_NAME,
    )

    raw = make_request()
    plan, _, _ = _plan(tmp_path, raw)
    request = normalize_request(raw)
    assert set(plan) == READY_KEYS
    assert plan["status"] == "ready"
    assert plan["schema_version"] == PLAN_SCHEMA
    assert plan["label"] == LABEL
    assert plan["capability_id"] == CAPABILITY_ID
    assert plan["plan_digest"] == plan_digest(request)
    assert plan["expires_at"].endswith("Z")
    assert plan["scope_id"] == raw["scope_id"]
    assert plan["snapshot_id"] == raw["snapshot_id"]
    assert plan["objective"] == raw["objective"]
    assert plan["top_k"] == raw["top_k"]
    text_bytes = sum(len(item["text"].encode("utf-8")) for item in raw["artifacts"])
    assert plan["counts"] == {
        "artifacts": 32,
        "text_bytes": text_bytes,
        "records_usable": 32,
        "records_dropped": 0,
    }
    assert plan["engines"] == [
        {"name": UNUSUAL_PAIRS_NAME, "capability_id": UNUSUAL_PAIRS_CAPABILITY},
        {"name": WORDING_AND_MEANING_NAME, "capability_id": WORDING_AND_MEANING_CAPABILITY},
    ]
    assert plan["model"]["found"] is True
    assert isinstance(plan["model"]["origin"], str)
    assert plan["outputs_expected"] == [
        "unusual-pairs.json",
        "wording-and-meaning-pairs.json",
        "ranked-pairs.md",
        "manifest.json",
    ]
    assert plan["network"].startswith("denied")
    assert set(plan["writes"]) == {
        "room",
        "portfolio",
        "job_store",
        "derived_vectors",
        "plan_receipt",
    }
    assert plan["writes"]["room"] == "none"
    assert plan["writes"]["portfolio"] == "none"
    assert plan["approval_required"] is True
    assert plan["host_handoff"]["state"] == "awaiting_approval"
    assert plan["host_handoff"]["approval_required"] is True


def test_plan_counts_dropped_records(tmp_path: Path, with_model: Path) -> None:
    raw = make_request()
    raw["artifacts"][5]["text"] = "too short"
    plan, _, _ = _plan(tmp_path, raw)
    assert plan["status"] == "ready"
    assert plan["counts"]["records_dropped"] == 1
    assert plan["counts"]["records_usable"] == 31
    assert any("Dropped 1" in line for line in plan["warnings"])


def test_plan_blocks_on_too_few_usable_records(tmp_path: Path, with_model: Path) -> None:
    raw = make_request(2)
    raw["artifacts"][1]["text"] = "too short"
    plan, _, _ = _plan(tmp_path, raw)
    assert plan["status"] == "blocked"
    assert plan["reason"] == "too_few_usable_records"
    assert plan["message"]
    assert plan["fix"]
    assert "plan_digest" not in plan
    assert plan["host_handoff"]["state"] == "blocked"
    assert plan["host_handoff"]["next_action"] == "fix_and_plan_again"


def test_plan_blocks_when_the_model_is_missing(tmp_path: Path, isolated_env: Path) -> None:
    from mindrian_eureka.models import model_fix_text

    plan, _, _ = _plan(tmp_path, make_request())
    assert plan["status"] == "blocked"
    assert plan["reason"] == "local_model_unavailable"
    assert plan["fix"] == model_fix_text()
    assert "plan_digest" not in plan
    assert "searched" not in json.dumps(plan)


def test_blocked_plan_records_no_receipt(
    tmp_path: Path, isolated_env: Path, fake_model_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, _, data_dir = _plan(tmp_path, make_request())
    assert plan["reason"] == "local_model_unavailable"
    assert _receipt_rows(data_dir) == 0

    monkeypatch.setenv(MODEL_VARIABLE, str(fake_model_dir))
    raw = make_request(2)
    raw["artifacts"][1]["text"] = "too short"
    plan, _, data_dir = _plan(tmp_path / "second", raw)
    assert plan["reason"] == "too_few_usable_records"
    assert _receipt_rows(data_dir) == 0


def test_ready_plan_records_one_receipt_that_can_be_claimed(
    tmp_path: Path, with_model: Path
) -> None:
    from mindrian_eureka.host_run.contracts import HostRunError, normalize_request
    from mindrian_eureka.host_run.gate import check_start

    raw = make_request()
    plan, receipts, data_dir = _plan(tmp_path, raw)
    assert _receipt_rows(data_dir) == 1
    start = dict(raw, approval={"plan_digest": plan["plan_digest"], "approval_ref": "ref:1"})
    claim = check_start(normalize_request(start), receipts, None)
    assert claim.retry is False
    with pytest.raises(HostRunError) as caught:
        check_start(normalize_request(start), receipts, None)
    assert caught.value.code == "plan_consumed"


def test_plan_holds_no_text_path_or_model_path(
    tmp_path: Path, isolated_env: Path, with_model: Path
) -> None:
    raw = make_request()
    plan, _, _ = _plan(tmp_path, raw)
    flat = json.dumps(plan, ensure_ascii=False)
    for item in raw["artifacts"]:
        assert item["text"][:40] not in flat
    for forbidden in (str(isolated_env), str(with_model), str(tmp_path), "/home/", "/tmp/"):
        assert forbidden not in flat
    assert "searched" not in flat


def test_plan_leaves_no_staging_folder(
    tmp_path: Path, isolated_env: Path, fake_model_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan, _, data_dir = _plan(tmp_path, make_request())
    assert plan["status"] == "blocked"
    assert sorted(item.name for item in data_dir.iterdir()) == ["plan-receipts.sqlite3"]

    monkeypatch.setenv(MODEL_VARIABLE, str(fake_model_dir))
    plan, _, data_dir = _plan(tmp_path / "second", make_request())
    assert plan["status"] == "ready"
    assert sorted(item.name for item in data_dir.iterdir()) == ["plan-receipts.sqlite3"]


def test_plan_is_stable_apart_from_expiry(tmp_path: Path, with_model: Path) -> None:
    raw = make_request()
    first, _, _ = _plan(tmp_path / "one", raw)
    second, _, _ = _plan(tmp_path / "two", raw)
    first.pop("expires_at")
    second.pop("expires_at")
    assert first == second


def test_plan_warns_on_a_small_collection(tmp_path: Path, with_model: Path) -> None:
    plan, _, _ = _plan(tmp_path, make_request(5))
    assert plan["status"] == "ready"
    assert plan["counts"]["records_usable"] == 5
    assert any("10" in line for line in plan["warnings"])


def test_plan_makes_no_network_call(
    tmp_path: Path, with_model: Path, no_network: list[object]
) -> None:
    plan, _, _ = _plan(tmp_path, make_request())
    assert plan["status"] == "ready"
    assert no_network == []


def test_plan_does_not_load_the_model(tmp_path: Path, with_model: Path) -> None:
    # The fake model folder has no real weights. A model load would fail.
    plan, _, _ = _plan(tmp_path, make_request())
    assert plan["status"] == "ready"
