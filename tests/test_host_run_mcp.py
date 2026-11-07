"""End-to-end tests of the pair screen tools, the gate, the catalog entry and the workflow."""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

import pytest
from host_run_support import make_request
from pydantic import ValidationError

REF = "gate:test-1"
CAPABILITY = "opportunity.run_pair_screen"
INPUT_SCHEMA = "schemas/pair-screen-input.v1.json"
OUTPUT_SCHEMA = "schemas/pair-screen-output.v1.json"
WAIT_SECONDS = 180


@pytest.fixture
def host(
    isolated_env: Path,
    stub_encoders: None,
    fake_model_dir: Path,
    monkeypatch: Any,
) -> Any:
    """Return the MCP server module with an isolated job store below the temporary home."""
    from mindrian_eureka.opportunity_pairs import mcp_server
    from mindrian_eureka.opportunity_pairs.jobs import JobManager

    monkeypatch.setenv("MINDRIAN_EUREKA_RS_MODEL_PATH", str(fake_model_dir))
    manager = JobManager(isolated_env / "data")
    monkeypatch.setattr(mcp_server, "manager", manager)
    yield mcp_server
    manager.executor.shutdown(wait=True)


def plan(host: Any, request: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = host.scout_plan_pair_screen(host.PairScreenInput(**request))
    return result


def start(
    host: Any,
    request: dict[str, Any],
    digest: str | None,
    ref: str = REF,
    key: str | None = None,
) -> dict[str, Any]:
    approval = None if digest is None else {"plan_digest": digest, "approval_ref": ref}
    model = host.PairScreenInput(**request, approval=approval)
    result: dict[str, Any] = host.scout_start_pair_screen(model, key)
    return result


def wait(host: Any, job_id: str) -> dict[str, Any]:
    from mindrian_eureka.opportunity_pairs.jobs import TERMINAL

    deadline = time.monotonic() + WAIT_SECONDS
    while time.monotonic() < deadline:
        status: dict[str, Any] = host.scout_status(job_id)
        if status["status"] in TERMINAL:
            return status
        time.sleep(0.1)
    raise AssertionError("job did not finish")


def job_rows(host: Any) -> int:
    with sqlite3.connect(host.manager.store.db_path) as db:
        return int(db.execute("select count(*) from jobs").fetchone()[0])


def run_cycle(host: Any, request: dict[str, Any], key: str | None = None) -> dict[str, Any]:
    planned = plan(host, request)
    assert planned["status"] == "ready"
    started = start(host, request, planned["plan_digest"], key=key)
    assert "job_id" in started
    assert wait(host, started["job_id"])["status"] == "completed"
    result: dict[str, Any] = host.scout_result(started["job_id"])
    return result


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(str(path.relative_to(root)).encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def all_paths(root: Path) -> set[Path]:
    return set(root.rglob("*"))


def test_tools_and_models_exist(host: Any) -> None:
    from mindrian_eureka.limits import MAX_ARTIFACTS, MAX_TOP_K

    for name in (
        "PairScreenInput",
        "ApprovalInput",
        "scout_plan_pair_screen",
        "scout_start_pair_screen",
    ):
        assert hasattr(host, name), name
    for name in (
        "scout_plan",
        "scout_start",
        "scout_status",
        "scout_result",
        "scout_cancel",
        "scout_delete_job",
        "scout_record_review",
    ):
        assert callable(getattr(host, name)), name
    schema = host.PairScreenInput.model_json_schema()
    assert schema["properties"]["artifacts"]["maxItems"] == MAX_ARTIFACTS
    assert schema["properties"]["top_k"]["maximum"] == MAX_TOP_K
    assert schema["properties"]["top_k"]["default"] == MAX_TOP_K
    listing = getattr(host.server, "list_tools", None)
    if listing is None or not inspect.iscoroutinefunction(listing):
        pytest.skip("the server object has no list_tools coroutine")
    names = {tool.name for tool in asyncio.run(listing())}
    assert {"scout_plan_pair_screen", "scout_start_pair_screen"} <= names


def test_plan_returns_a_ready_plan_and_start_runs_the_job(host: Any) -> None:
    from mindrian_eureka.contracts import validate_result

    request = make_request()
    planned = plan(host, request)
    assert planned["status"] == "ready"
    started = start(host, request, planned["plan_digest"])
    assert started["job_id"]
    assert started["capability_id"] == CAPABILITY
    assert wait(host, started["job_id"])["status"] == "completed"
    result = host.scout_result(started["job_id"])
    assert result["capability_id"] == CAPABILITY
    assert result["status"] == "completed"
    assert result["host_handoff"]["next_action"] == "resolve_sources_and_select_candidates"
    assert result["room_write"] == "not_performed"
    validate_result(CAPABILITY, result)


def test_start_refusals_start_no_job(host: Any) -> None:
    from mindrian_eureka.host_run.contracts import normalize_request
    from mindrian_eureka.host_run.gate import plan_digest

    request = make_request(32)
    other = make_request(20)
    planned = plan(host, request)
    other_plan = plan(host, other)
    assert planned["status"] == other_plan["status"] == "ready"

    refused = start(host, request, None)
    assert refused["status"] == "refused"
    assert refused["reason"] == "approval_missing"

    refused = start(host, request, other_plan["plan_digest"])
    assert refused["status"] == "refused"
    assert refused["reason"] == "plan_mismatch"

    unplanned = make_request(10)
    model = host.PairScreenInput(**unplanned)
    digest = plan_digest(normalize_request(model.model_dump(exclude_none=True)))
    refused = start(host, unplanned, digest)
    assert refused["status"] == "refused"
    assert refused["reason"] == "plan_unknown"

    changed = make_request(32)
    changed["artifacts"][0]["text"] = changed["artifacts"][0]["text"] + " changed"
    refused = start(host, changed, planned["plan_digest"])
    assert refused["status"] == "refused"
    assert refused["reason"] == "plan_mismatch"

    with pytest.raises(ValidationError):
        start(host, request, planned["plan_digest"], ref="bad ref")

    assert job_rows(host) == 0


def test_expired_plan_is_refused(host: Any) -> None:
    request = make_request(12)
    planned = plan(host, request)
    receipts = host.manager.store.data_dir / "plan-receipts.sqlite3"
    with sqlite3.connect(receipts) as db:
        db.execute("update receipts set expires_at = 0")
    refused = start(host, request, planned["plan_digest"])
    assert refused["status"] == "refused"
    assert refused["reason"] == "plan_expired"
    assert job_rows(host) == 0


def test_receipt_is_single_use_and_retry_safe(host: Any) -> None:
    request = make_request(12)
    planned = plan(host, request)
    first = start(host, request, planned["plan_digest"], key="k1")
    again = start(host, request, planned["plan_digest"], key="k1")
    assert again["job_id"] == first["job_id"]
    assert job_rows(host) == 1
    other_key = start(host, request, planned["plan_digest"], key="k2")
    assert other_key["status"] == "refused"
    assert other_key["reason"] == "plan_consumed"
    wait(host, first["job_id"])

    fresh = plan(host, request)
    one = start(host, request, fresh["plan_digest"])
    assert "job_id" in one
    two = start(host, request, fresh["plan_digest"])
    assert two["status"] == "refused"
    assert two["reason"] == "plan_consumed"
    wait(host, one["job_id"])


def test_failed_job_start_releases_the_receipt(host: Any) -> None:
    request = make_request(12)
    planned = plan(host, request)
    original = host.manager.start

    def boom(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise ValueError("queue full")

    host.manager.start = boom
    try:
        with pytest.raises(ValueError):
            start(host, request, planned["plan_digest"])
    finally:
        host.manager.start = original
    started = start(host, request, planned["plan_digest"])
    assert "job_id" in started
    wait(host, started["job_id"])


def test_blocked_plan_without_a_model(host: Any, monkeypatch: Any) -> None:
    monkeypatch.delenv("MINDRIAN_EUREKA_RS_MODEL_PATH", raising=False)
    request = make_request(12)
    planned = plan(host, request)
    assert planned["status"] == "blocked"
    assert planned["reason"] == "local_model_unavailable"
    from mindrian_eureka.host_run.contracts import normalize_request
    from mindrian_eureka.host_run.gate import plan_digest

    model = host.PairScreenInput(**request)
    digest = plan_digest(normalize_request(model.model_dump(exclude_none=True)))
    refused = start(host, request, digest)
    assert refused["status"] == "refused"
    assert refused["reason"] == "plan_unknown"
    assert job_rows(host) == 0


def test_two_runs_give_equal_hashes_through_the_tools(host: Any) -> None:
    request = make_request()
    first = run_cycle(host, request)
    second = run_cycle(host, request)
    assert first["job_id"] != second["job_id"]
    assert [item["sha256"] for item in first["files"]] == [
        item["sha256"] for item in second["files"]
    ]
    assert first["manifest_sha256"] == second["manifest_sha256"]


def test_review_and_delete_work_on_the_result(host: Any) -> None:
    result = run_cycle(host, make_request())
    job_id = result["job_id"]
    candidate = result["outputs"][0]["id"]
    review = host.ReviewInput(
        job_id=job_id,
        candidate_id=candidate,
        useful=True,
        direction_correct=True,
        already_known=False,
    )
    assert host.scout_record_review(review)["saved"] is True
    assert host.scout_delete_job(job_id)["deleted"] is True
    with pytest.raises(KeyError):
        host.scout_result(job_id)


def test_only_the_data_directory_changes(host: Any, isolated_env: Path, tmp_path: Path) -> None:
    room = tmp_path / "room"
    (room / ".mindrian").mkdir(parents=True)
    (room / "room.db").write_bytes(b"room-database")
    (room / "ROOM.md").write_text("room notes", encoding="utf-8")
    (room / ".mindrian" / "state.json").write_text("{}", encoding="utf-8")
    room_before = tree_hash(room)
    before = all_paths(isolated_env)

    result = run_cycle(host, make_request())
    assert result["room_write"] == "not_performed"

    data = isolated_env / "data"
    new = all_paths(isolated_env) - before
    assert new
    for path in new:
        assert path == data or data in path.parents, str(path)
    assert tree_hash(room) == room_before
    assert list(isolated_env.rglob("embeddings.sqlite3")) == []


def test_catalog_entry_and_contract(host: Any) -> None:
    from mindrian_eureka.contracts import capability_record
    from mindrian_eureka.limits import MAX_ARTIFACTS, MAX_TOP_K

    entry = capability_record(CAPABILITY)
    assert entry is not None
    assert entry["status"] == "experimental"
    mcp = entry["routes"]["mcp"]
    assert mcp["tool"] == "scout_start_pair_screen"
    assert callable(getattr(host, mcp["tool"]))
    assert {"scout_status", "scout_result"} <= set(mcp["follow_up_tools"])
    assert entry["routes"]["cli"]["executable"] == "eureka"
    assert entry["input_schema"] == INPUT_SCHEMA
    assert entry["output_schema"] == OUTPUT_SCHEMA
    assert entry["resource_limits"]["max_artifacts"] == MAX_ARTIFACTS
    assert entry["resource_limits"]["max_top_k"] == MAX_TOP_K
    contract = host.scout_capability_contract(CAPABILITY)
    for direction in ("input", "output"):
        schema = contract["schemas"][direction]
        assert isinstance(schema, dict)
        assert "status" not in schema
    words = (entry["jtbd"] + " ".join(entry["limitations"])).lower()
    assert "candidate, not verified" in words or "cannot verify" in words
    assert re.search(r"\b(RS|HSI)\b", json.dumps(entry)) is None


def test_workflow_contract_names_the_tools(host: Any) -> None:
    workflow = host.scout_host_workflow()
    surface = workflow["execution_surfaces"]["mcp"]
    assert "scout_plan_pair_screen" in surface
    assert "scout_start_pair_screen" in surface
    stages = {stage["id"]: stage for stage in workflow["stages"]}
    assert "scout_plan_pair_screen" in stages["capability_plan"]["action"]
    assert "scout_start_pair_screen" in stages["bounded_execution"]["action"]


def test_legacy_tool_caps_unchanged_by_this_plan(host: Any) -> None:
    from mindrian_eureka.limits import MAX_ARTIFACTS, MAX_TOP_K

    schema = host.ScoutRunInput.model_json_schema()
    assert schema["properties"]["artifacts"]["maxItems"] == MAX_ARTIFACTS
    assert schema["properties"]["top_k"]["maximum"] == MAX_TOP_K
