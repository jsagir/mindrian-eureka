"""Tests for the plan digest, the single-use receipt store and the start check."""

from __future__ import annotations

import copy
import os
import sqlite3
import stat
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pytest
from host_run_support import SCHEMA_DIR, make_request

POSIX = sys.platform != "win32"
FILE_NAME = "plan-receipts.sqlite3"
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def _request(count: int = 32, **overrides: Any) -> Any:
    from mindrian_eureka.host_run.contracts import normalize_request

    return normalize_request(make_request(count, **overrides))


def _digest(raw: dict[str, Any]) -> str:
    from mindrian_eureka.host_run.contracts import normalize_request
    from mindrian_eureka.host_run.gate import plan_digest

    return plan_digest(normalize_request(raw))


def _receipts(tmp_path: Path, now: list[float] | None = None) -> Any:
    from mindrian_eureka.host_run.gate import PlanReceipts

    clock = now if now is not None else [1_000_000.0]
    return PlanReceipts(tmp_path / "data", clock=lambda: clock[0])


def _rows(tmp_path: Path) -> list[tuple[Any, ...]]:
    connection = sqlite3.connect(tmp_path / "data" / FILE_NAME)
    try:
        return connection.execute(
            "SELECT receipt_id, plan_digest, scope_id, snapshot_id, created_at, expires_at,"
            " consumed_at, approval_ref, idempotency_key, job_id FROM receipts"
            " ORDER BY receipt_id"
        ).fetchall()
    finally:
        connection.close()


def test_digest_is_stable_and_hex() -> None:
    from mindrian_eureka.host_run.gate import plan_digest

    request = _request()
    first = plan_digest(request)
    assert len(first) == 64
    assert first == first.lower()
    int(first, 16)
    assert plan_digest(request) == first


@pytest.mark.parametrize(
    "field", ["objective", "scope_id", "snapshot_id", "top_k", "id", "source_ref", "title", "text"]
)
def test_digest_follows_every_planned_field(field: str) -> None:
    base = make_request()
    changed = copy.deepcopy(base)
    if field == "top_k":
        changed["top_k"] = 7
    elif field in ("objective", "scope_id", "snapshot_id"):
        changed[field] = base[field] + " changed"
    else:
        changed["artifacts"][3][field] = base["artifacts"][3][field] + " changed"
    assert _digest(changed) != _digest(base)


def test_digest_ignores_order_and_approval() -> None:
    base = make_request()
    reordered = copy.deepcopy(base)
    reordered["artifacts"].reverse()
    approved = copy.deepcopy(base)
    approved["approval"] = {"plan_digest": DIGEST_A, "approval_ref": "ref:1"}
    assert _digest(reordered) == _digest(base)
    assert _digest(approved) == _digest(base)


def test_receipts_file_is_private_and_holds_no_text(tmp_path: Path) -> None:
    from mindrian_eureka.host_run.gate import plan_digest

    receipts = _receipts(tmp_path)
    request = _request()
    receipts.record_plan(plan_digest(request), request.scope_id, request.snapshot_id)
    path = tmp_path / "data" / FILE_NAME
    assert path.is_file()
    if POSIX:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert stat.S_IMODE(path.parent.stat().st_mode) == 0o700
    data = path.read_bytes()
    for artifact in request.artifacts:
        assert artifact.text[:40].encode("utf-8") not in data
        assert artifact.source_ref.encode("utf-8") not in data
    assert request.objective.encode("utf-8") not in data
    assert sorted(item.name for item in path.parent.iterdir()) == [FILE_NAME]


def test_claim_happy_path_then_consumed(tmp_path: Path) -> None:
    from mindrian_eureka.host_run.contracts import HostRunError
    from mindrian_eureka.host_run.gate import Claim

    receipts = _receipts(tmp_path)
    receipts.record_plan(DIGEST_A, "scope", "snap")
    claim = receipts.claim(DIGEST_A, "gate:one", None)
    assert isinstance(claim, Claim)
    assert claim.retry is False
    with pytest.raises(HostRunError) as caught:
        receipts.claim(DIGEST_A, "gate:one", None)
    assert caught.value.code == "plan_consumed"
    assert caught.value.fix


def test_claim_unknown_and_expired(tmp_path: Path) -> None:
    from mindrian_eureka.host_run.contracts import PLAN_TTL_SECONDS, HostRunError

    now = [1_000_000.0]
    receipts = _receipts(tmp_path, now)
    with pytest.raises(HostRunError) as unknown:
        receipts.claim(DIGEST_A, "gate:one", None)
    assert unknown.value.code == "plan_unknown"

    receipts.record_plan(DIGEST_A, "scope", "snap")
    receipts.record_plan(DIGEST_B, "scope", "snap")
    now[0] += PLAN_TTL_SECONDS - 1
    assert receipts.claim(DIGEST_A, "gate:one", None).retry is False
    now[0] += 2
    with pytest.raises(HostRunError) as expired:
        receipts.claim(DIGEST_B, "gate:one", None)
    assert expired.value.code == "plan_expired"


def test_claim_retry_with_the_same_key(tmp_path: Path) -> None:
    from mindrian_eureka.host_run.contracts import PLAN_TTL_SECONDS, HostRunError

    now = [1_000_000.0]
    receipts = _receipts(tmp_path, now)
    receipts.record_plan(DIGEST_A, "scope", "snap")
    first = receipts.claim(DIGEST_A, "gate:one", "k1")
    again = receipts.claim(DIGEST_A, "gate:one", "k1")
    assert first.retry is False
    assert again.retry is True
    assert again.receipt_id == first.receipt_id
    with pytest.raises(HostRunError) as other_key:
        receipts.claim(DIGEST_A, "gate:one", "k2")
    assert other_key.value.code == "plan_consumed"
    with pytest.raises(HostRunError) as other_ref:
        receipts.claim(DIGEST_A, "gate:two", "k1")
    assert other_ref.value.code == "plan_consumed"
    now[0] += PLAN_TTL_SECONDS + 10
    late = receipts.claim(DIGEST_A, "gate:one", "k1")
    assert late.retry is True
    assert late.receipt_id == first.receipt_id


def test_new_plan_call_opens_a_new_receipt(tmp_path: Path) -> None:
    from mindrian_eureka.host_run.contracts import HostRunError

    receipts = _receipts(tmp_path)
    receipts.record_plan(DIGEST_A, "scope", "snap")
    first = receipts.claim(DIGEST_A, "gate:one", None)
    with pytest.raises(HostRunError):
        receipts.claim(DIGEST_A, "gate:one", None)
    receipts.record_plan(DIGEST_A, "scope", "snap")
    second = receipts.claim(DIGEST_A, "gate:two", None)
    assert second.receipt_id != first.receipt_id
    assert len(_rows(tmp_path)) == 2


def test_release_makes_the_receipt_claimable_again(tmp_path: Path) -> None:
    receipts = _receipts(tmp_path)
    receipts.record_plan(DIGEST_A, "scope", "snap")
    claim = receipts.claim(DIGEST_A, "gate:one", "k1")
    receipts.release(claim.receipt_id)
    row = _rows(tmp_path)[0]
    assert row[6:9] == (None, None, None)
    again = receipts.claim(DIGEST_A, "gate:one", "k1")
    assert again.retry is False
    assert again.receipt_id == claim.receipt_id


def test_attach_job_and_audit_row(tmp_path: Path) -> None:
    receipts = _receipts(tmp_path)
    receipts.record_plan(DIGEST_A, "scope-x", "snap-y")
    claim = receipts.claim(DIGEST_A, "gate:one", "k1")
    receipts.attach_job(claim.receipt_id, "eureka-abc")
    rows = _rows(tmp_path)
    assert len(rows) == 1
    row = rows[0]
    assert row[1] == DIGEST_A
    assert row[2] == "scope-x"
    assert row[3] == "snap-y"
    assert row[6] is not None
    assert row[7] == "gate:one"
    assert row[8] == "k1"
    assert row[9] == "eureka-abc"


def test_purge_removes_old_rows(tmp_path: Path) -> None:
    from mindrian_eureka.host_run.contracts import RECEIPT_RETENTION_SECONDS

    now = [1_000_000.0]
    receipts = _receipts(tmp_path, now)
    receipts.record_plan(DIGEST_A, "scope", "snap")
    now[0] += RECEIPT_RETENTION_SECONDS - 5
    receipts.record_plan(DIGEST_B, "scope", "snap")
    assert len(_rows(tmp_path)) == 2
    now[0] += 10
    _receipts(tmp_path, now)
    rows = _rows(tmp_path)
    assert [row[1] for row in rows] == [DIGEST_B]


def test_check_start_refusals(tmp_path: Path) -> None:
    from mindrian_eureka.host_run.contracts import HostRunError
    from mindrian_eureka.host_run.gate import Claim, check_start, plan_digest

    receipts = _receipts(tmp_path)
    other = _request(10)
    receipts.record_plan(plan_digest(other), other.scope_id, other.snapshot_id)

    with pytest.raises(HostRunError) as missing:
        check_start(_request(), receipts, None)
    assert missing.value.code == "approval_missing"
    assert missing.value.fix

    wrong = {"plan_digest": plan_digest(other), "approval_ref": "ref:1"}
    with pytest.raises(HostRunError) as mismatch:
        check_start(_request(approval=wrong), receipts, None)
    assert mismatch.value.code == "plan_mismatch"
    assert plan_digest(other) not in mismatch.value.message
    assert plan_digest(other)[:12] in mismatch.value.message

    request = _request()
    right = {"plan_digest": plan_digest(request), "approval_ref": "ref:1"}
    with pytest.raises(HostRunError) as unknown:
        check_start(_request(approval=right), receipts, None)
    assert unknown.value.code == "plan_unknown"

    receipts.record_plan(plan_digest(request), request.scope_id, request.snapshot_id)
    claim = check_start(_request(approval=right), receipts, None)
    assert isinstance(claim, Claim)
    assert claim.retry is False


def test_check_start_after_a_changed_bundle(tmp_path: Path) -> None:
    from mindrian_eureka.host_run.contracts import HostRunError
    from mindrian_eureka.host_run.gate import check_start, plan_digest

    receipts = _receipts(tmp_path)
    planned = _request()
    receipts.record_plan(plan_digest(planned), planned.scope_id, planned.snapshot_id)
    changed = make_request()
    changed["artifacts"][0]["text"] += " extra"
    changed["approval"] = {"plan_digest": plan_digest(planned), "approval_ref": "ref:1"}
    from mindrian_eureka.host_run.contracts import normalize_request

    with pytest.raises(HostRunError) as caught:
        check_start(normalize_request(changed), receipts, None)
    assert caught.value.code == "plan_mismatch"


def test_concurrent_claims_give_one_winner(tmp_path: Path) -> None:
    from mindrian_eureka.host_run.contracts import HostRunError
    from mindrian_eureka.host_run.gate import PlanReceipts

    receipts = PlanReceipts(tmp_path / "data")
    receipts.record_plan(DIGEST_A, "scope", "snap")
    barrier = threading.Barrier(2)
    outcomes: list[str] = []
    lock = threading.Lock()

    def worker(label: str) -> None:
        mine = PlanReceipts(tmp_path / "data")
        barrier.wait()
        try:
            mine.claim(DIGEST_A, label, None)
            result = "won"
        except HostRunError as exc:
            result = exc.code
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=worker, args=(f"gate:{n}",)) for n in (1, 2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ["plan_consumed", "won"]


def test_module_import_is_light() -> None:
    code = (
        "import sys\n"
        "import mindrian_eureka.host_run.gate\n"
        "import mindrian_eureka.host_run.plan\n"
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
