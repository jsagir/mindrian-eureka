"""Tests for the pair screen job (host_run/execute.py) and its branch in the job manager."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import pytest
from host_run_support import SCHEMA_DIR, make_request
from jsonschema import Draft202012Validator

POSIX = sys.platform != "win32"
JOB_A = "eureka-" + "a" * 32
JOB_B = "eureka-" + "b" * 32
DIGEST = "d" * 64
REF = "gate:test-1"
FIVE_PATHS = [
    "corpus/records.jsonl",
    "manifest.json",
    "ranked-pairs.md",
    "unusual-pairs.json",
    "wording-and-meaning-pairs.json",
]
FORBIDDEN_SOURCE = (
    "room.db",
    "MindrianRooms",
    ".mindrian",
    "urllib",
    "requests",
    "socket",
    "subprocess",
    "http.client",
)


@pytest.fixture
def env(isolated_env: Path, stub_encoders: None, fake_model_dir: Path, monkeypatch: Any) -> Path:
    """A temporary home, stub encoders and a model variable that points at a fake model."""
    monkeypatch.setenv("MINDRIAN_EUREKA_RS_MODEL_PATH", str(fake_model_dir))
    return isolated_env


def _norm(**overrides: Any) -> Any:
    from mindrian_eureka.host_run.contracts import normalize_request

    approval = {"plan_digest": DIGEST, "approval_ref": REF}
    return normalize_request(make_request(approval=approval, **overrides))


def _job_request(**overrides: Any) -> dict[str, Any]:
    from mindrian_eureka.host_run.execute import build_job_request

    return build_job_request(_norm(**overrides))


def _run(data_dir: Path, job_id: str = JOB_A, **extra: Any) -> dict[str, Any]:
    from mindrian_eureka.host_run.execute import run_pair_screen_job

    result: dict[str, Any] = run_pair_screen_job(
        _job_request(), data_dir=data_dir, job_id=job_id, **extra
    )
    return result


def _validator() -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / "pair-screen-output.v1.json").read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def test_job_returns_a_valid_envelope(env: Path, tmp_path: Path) -> None:
    result = _run(tmp_path / "data")
    assert list(_validator().iter_errors(result)) == []
    assert result["status"] == "completed"
    assert result["counts"]["records_used"] == 32
    assert result["counts"]["unusual_pairs"] > 0
    assert result["counts"]["wording_and_meaning_pairs"] > 0
    sent = {item["id"]: item["source_ref"] for item in make_request()["artifacts"]}
    assert len(result["id_map"]) == 32
    for item in result["id_map"]:
        assert sent[item["artifact_id"]] == item["source_ref"]
    assert result["scope"] == {"scope_id": "room:test-scope", "snapshot_id": "snapshot:test-1"}
    assert result["job_id"] == JOB_A


def test_two_jobs_give_equal_file_hashes(env: Path, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    first = _run(data_dir, JOB_A)
    second = _run(data_dir, JOB_B)
    assert [item["path"] for item in first["files"]] == FIVE_PATHS
    assert [item["sha256"] for item in first["files"]] == [
        item["sha256"] for item in second["files"]
    ]
    assert [item.get("content") for item in first["files"]] == [
        item.get("content") for item in second["files"]
    ]
    assert first["manifest_sha256"] == second["manifest_sha256"]


def test_hashed_files_hold_no_job_or_approval_value(env: Path, tmp_path: Path) -> None:
    result = _run(tmp_path / "data")
    pattern = re.compile(r"eureka-[0-9a-f]{32}")
    for item in result["files"]:
        content = item.get("content", "")
        assert JOB_A not in content
        assert REF not in content
        assert DIGEST not in content
        assert pattern.search(content) is None


def test_run_folder_and_cache_are_gone(env: Path, tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    _run(data_dir)
    assert not (data_dir / "host-runs" / JOB_A).exists()
    for root in (data_dir, env):
        assert [p for p in root.rglob("embeddings.sqlite3")] == []
        assert [p for p in root.rglob("*") if ".staging-" in p.name] == []
    if POSIX:
        assert (data_dir.stat().st_mode & 0o777) == 0o700
        assert ((data_dir / "host-runs").stat().st_mode & 0o777) == 0o700


def test_cancel_before_the_first_stage(env: Path, tmp_path: Path) -> None:
    from mindrian_eureka.opportunity_pairs.algorithm import RunCancelled

    data_dir = tmp_path / "data"
    with pytest.raises(RunCancelled):
        _run(data_dir, cancel_check=lambda: True)
    assert not (data_dir / "host-runs" / JOB_A).exists()


def test_cancel_between_stages(env: Path, tmp_path: Path) -> None:
    from mindrian_eureka.opportunity_pairs.algorithm import RunCancelled

    calls: list[int] = []

    def cancel_check() -> bool:
        calls.append(1)
        return len(calls) >= 3

    data_dir = tmp_path / "data"
    with pytest.raises(RunCancelled):
        _run(data_dir, cancel_check=cancel_check)
    assert len(calls) >= 3
    assert not (data_dir / "host-runs" / JOB_A).exists()
    assert [p for p in data_dir.rglob("out")] == []


def test_stage_callback_sees_the_pipeline_stages(env: Path, tmp_path: Path) -> None:
    seen: list[str] = []
    _run(tmp_path / "data", stage_callback=seen.append)
    assert seen[0] == "Reading sources"
    assert seen[-1] == "Writing files"
    middle = seen[1:-1]
    assert len([name for name in middle if name.startswith("Ranking with")]) == 2


def test_missing_model_fails_clearly_and_cleans_up(
    isolated_env: Path, stub_encoders: None, tmp_path: Path
) -> None:
    data_dir = tmp_path / "data"
    with pytest.raises(Exception) as caught:
        _run(data_dir)
    assert str(caught.value).startswith("No local model found.")
    assert not (data_dir / "host-runs" / JOB_A).exists()


def test_nothing_goes_to_stdout(
    env: Path, tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    capfd.readouterr()
    _run(tmp_path / "data")
    captured = capfd.readouterr()
    assert captured.out == ""


def test_job_makes_no_network_call(env: Path, tmp_path: Path, no_network: list[object]) -> None:
    result = _run(tmp_path / "data")
    assert result["status"] == "completed"
    assert no_network == []


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(str(path.relative_to(root)).encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def test_job_never_touches_a_room_tree(env: Path, tmp_path: Path) -> None:
    import mindrian_eureka.host_run as package

    room = tmp_path / "room"
    (room / ".mindrian").mkdir(parents=True)
    (room / ".mindrian" / "state.json").write_text("{}", encoding="utf-8")
    (room / "room.db").write_bytes(b"stub-room-db")
    (room / "ROOM.md").write_text("# Room\n", encoding="utf-8")
    before = _tree_hash(room)
    _run(tmp_path / "data")
    assert _tree_hash(room) == before
    for source in sorted(Path(package.__file__).parent.glob("*.py")):
        text = source.read_text(encoding="utf-8")
        for word in FORBIDDEN_SOURCE:
            assert word not in text, f"{source.name} holds {word}"


def test_job_request_builder_and_store_accept_it(tmp_path: Path) -> None:
    from mindrian_eureka.opportunity_pairs.jobs import JobStore

    request = _job_request(top_k=15)
    assert set(request) == {
        "capability_id",
        "mode",
        "objective",
        "scope_id",
        "snapshot_id",
        "artifacts",
        "top_k",
        "approval",
    }
    assert request["capability_id"] == "opportunity.run_pair_screen"
    assert request["mode"] == "local"
    assert request["top_k"] == 15
    assert request["approval"] == {"plan_digest": DIGEST, "approval_ref": REF}
    assert all(item["corpus"] == "room" for item in request["artifacts"])
    job_id, created = JobStore(tmp_path / "s").create(request, None)
    assert created is True
    assert job_id.startswith("eureka-")


def test_build_job_request_needs_an_approval() -> None:
    from mindrian_eureka.host_run.contracts import HostRunError, normalize_request
    from mindrian_eureka.host_run.execute import build_job_request

    with pytest.raises(HostRunError) as caught:
        build_job_request(normalize_request(make_request()))
    assert caught.value.code == "approval_missing"


def test_job_id_must_be_a_safe_name(env: Path, tmp_path: Path) -> None:
    from mindrian_eureka.host_run.execute import run_pair_screen_job

    for bad in ("../escape", "a/b", "", "x" * 65, "a b"):
        with pytest.raises(ValueError):
            run_pair_screen_job(_job_request(), data_dir=tmp_path / "data", job_id=bad)
    assert not (tmp_path / "escape").exists()


def _wait(manager: Any, job_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + 120
    status: dict[str, Any] = {}
    while time.monotonic() < deadline:
        status = manager.status(job_id)
        if status["status"] in {"completed", "completed_empty", "failed", "cancelled"}:
            return status
        time.sleep(0.1)
    return status


def test_job_manager_runs_the_added_branch(env: Path, tmp_path: Path) -> None:
    from mindrian_eureka.opportunity_pairs.jobs import JobManager

    manager = JobManager(tmp_path / "jm")
    started = manager.start(_job_request())
    status = _wait(manager, started["job_id"])
    assert status["status"] == "completed"
    stored = manager.result(started["job_id"])
    assert stored["capability_id"] == "opportunity.run_pair_screen"
    assert manager.store.get(started["job_id"])["request_json"] is None
    assert not (tmp_path / "jm" / "host-runs" / started["job_id"]).exists()


def test_job_manager_marks_a_missing_model(
    isolated_env: Path, stub_encoders: None, tmp_path: Path
) -> None:
    from mindrian_eureka.opportunity_pairs.jobs import JobManager

    manager = JobManager(tmp_path / "jm")
    started = manager.start(_job_request())
    status = _wait(manager, started["job_id"])
    assert status["status"] == "failed"
    assert status["failure_code"] == "model_unavailable"


def test_jobs_py_change_is_additive() -> None:
    import mindrian_eureka.opportunity_pairs.jobs as jobs

    text = Path(jobs.__file__).read_text(encoding="utf-8")
    assert text.count("opportunity.run_pair_screen") == 1
    assert text.count("opportunity.synthesize_discovery_signals") == 1
