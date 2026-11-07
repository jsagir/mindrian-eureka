"""What a host sees over MCP for each refusal code of the pair screen run.

The contract page holds one table cell per code: refused, tool error or blocked.
Each case here calls the tool through `server.call_tool`, the path of a real host, and pins
the cell. A tool error is raised by the argument check before the engine code runs.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest
from host_run_support import make_request

PLAN = "scout_plan_pair_screen"
START = "scout_start_pair_screen"
REF = "gate:reach-1"


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


def call(host: Any, tool: str, request: dict[str, Any], key: str | None = None) -> tuple[str, str]:
    """Call a tool as a host does. Return the class of the answer and its reason."""
    arguments: dict[str, Any] = {"request": request}
    if key is not None:
        arguments["idempotency_key"] = key
    try:
        out = asyncio.run(host.server.call_tool(tool, arguments))
    except Exception:
        return ("tool error", "")
    if isinstance(out, tuple):
        out = out[0]
    answer = out if isinstance(out, dict) else json.loads(out[0].text)
    return (str(answer.get("status")), str(answer.get("reason", "")))


def digest_of(host: Any, request: dict[str, Any]) -> str:
    from mindrian_eureka.host_run.contracts import normalize_request
    from mindrian_eureka.host_run.gate import plan_digest

    model = host.PairScreenInput(**request)
    return plan_digest(normalize_request(model.model_dump(exclude_none=True)))


def approved(request: dict[str, Any], digest: str, ref: str = REF) -> dict[str, Any]:
    return {**request, "approval": {"plan_digest": digest, "approval_ref": ref}}


def test_over_mcp_the_plan_call_answers_ready(host: Any) -> None:
    assert call(host, PLAN, make_request(12)) == ("ready", "")


@pytest.mark.parametrize(
    ("name", "mutate", "expected"),
    [
        ("blank objective", lambda r: r.update(objective="   "), ("refused", "bad_request")),
        (
            "id with no usable character",
            lambda r: r["artifacts"][0].update(id="..."),
            ("refused", "bad_request"),
        ),
        ("missing key", lambda r: r.pop("scope_id"), ("tool error", "")),
        ("unknown key", lambda r: r.update(bogus=1), ("tool error", "")),
        (
            "lone surrogate in the text",
            lambda r: r["artifacts"][0].update(text="\ud800 lone"),
            ("tool error", ""),
        ),
        (
            "lone surrogate in the objective",
            lambda r: r.update(objective="\ud800"),
            ("tool error", ""),
        ),
        (
            "more than 3000 artifacts",
            lambda r: r.update(artifacts=r["artifacts"] * 251),
            ("tool error", ""),
        ),
        (
            "one text above 1000000 characters",
            lambda r: r["artifacts"][0].update(text="x" * 1_000_001),
            ("tool error", ""),
        ),
        (
            "duplicate id",
            lambda r: r["artifacts"][1].update(id=r["artifacts"][0]["id"]),
            ("refused", "duplicate_artifact_id"),
        ),
        (
            "id collision after the sanitizer",
            lambda r: (
                r["artifacts"][0].update(id="a b"),
                r["artifacts"][1].update(id="a_b"),
            ),
            ("refused", "id_collision"),
        ),
        (
            "wrong sha256",
            lambda r: r["artifacts"][0].update(sha256="0" * 64),
            ("refused", "artifact_hash_mismatch"),
        ),
        (
            "external corpus",
            lambda r: r["artifacts"][0].update(corpus="external"),
            ("refused", "external_corpus_refused"),
        ),
    ],
)
def test_plan_call_cell(host: Any, name: str, mutate: Any, expected: tuple[str, str]) -> None:
    request = make_request(12)
    mutate(request)
    assert call(host, PLAN, request) == expected, name


def test_total_text_above_20_mib_is_refused(host: Any) -> None:
    request = make_request(12)
    request["artifacts"] = [
        {"id": f"big-{index}", "source_ref": f"ref-{index}", "text": "x" * 1_000_000}
        for index in range(21)
    ]
    assert call(host, PLAN, request) == ("refused", "bundle_too_large")


def test_start_call_cells(host: Any) -> None:
    request = make_request(12)
    other = make_request(10)
    assert call(host, PLAN, request) == ("ready", "")
    digest = digest_of(host, request)

    assert call(host, START, request) == ("refused", "approval_missing")
    assert call(host, START, approved(request, "zz")) == ("tool error", "")
    assert call(host, START, approved(request, digest, "bad ref")) == ("tool error", "")
    assert call(host, START, approved(request, digest), key="k" * 129) == (
        "refused",
        "bad_request",
    )
    assert call(host, START, approved(other, digest_of(host, other))) == (
        "refused",
        "plan_unknown",
    )
    assert call(host, START, approved(other, digest)) == ("refused", "plan_mismatch")

    receipts = host.manager.store.data_dir / "plan-receipts.sqlite3"
    with sqlite3.connect(receipts) as db:
        db.execute("update receipts set expires_at = 0")
    assert call(host, START, approved(request, digest)) == ("refused", "plan_expired")


def test_consumed_receipt_is_refused(host: Any) -> None:
    request = make_request(12)
    assert call(host, PLAN, request) == ("ready", "")
    digest = digest_of(host, request)
    assert call(host, START, approved(request, digest))[0] == "queued"
    assert call(host, START, approved(request, digest, "gate:reach-2")) == (
        "refused",
        "plan_consumed",
    )


def test_blocked_plans_come_back_as_blocked(host: Any, monkeypatch: Any) -> None:
    short = make_request(12)
    for item in short["artifacts"]:
        item["text"] = "hi"
    assert call(host, PLAN, short) == ("blocked", "too_few_usable_records")
    monkeypatch.delenv("MINDRIAN_EUREKA_RS_MODEL_PATH", raising=False)
    assert call(host, PLAN, make_request(12)) == ("blocked", "local_model_unavailable")


def test_each_plan_call_mints_one_start(host: Any) -> None:
    request = make_request(12)
    digest = digest_of(host, request)
    assert call(host, PLAN, request) == ("ready", "")
    assert call(host, PLAN, request) == ("ready", "")
    first = call(host, START, approved(request, digest, "gate:reach-a"))
    second = call(host, START, approved(request, digest, "gate:reach-b"))
    third = call(host, START, approved(request, digest, "gate:reach-c"))
    assert first[0] == "queued"
    assert second[0] == "queued"
    assert third == ("refused", "plan_consumed")
