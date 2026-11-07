"""Logic behind the two pair screen tools of the MCP server.

`plan_pair_screen` checks a request and returns a plan, or a typed refusal. It starts
nothing. `start_pair_screen` checks the start against a live plan receipt, starts one
durable job and returns the job id, or a typed refusal. A refusal starts no job.

This module is plain Python. It imports no numpy, no model library and no MCP library.
The job manager is passed in by the caller.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final, Protocol

from mindrian_eureka.host_run.contracts import (
    CAPABILITY_ID,
    LABEL,
    HostRunError,
    normalize_request,
)
from mindrian_eureka.host_run.execute import build_job_request
from mindrian_eureka.host_run.gate import PlanReceipts, check_start
from mindrian_eureka.host_run.plan import build_plan

__all__ = ["plan_pair_screen", "start_pair_screen"]

_MAX_KEY_CHARS: Final[int] = 128
_NEXT: Final[str] = (
    "Poll scout_status with the job id until the status is final, then call scout_result."
)


class _Manager(Protocol):
    """The part of the job manager that the start function uses."""

    store: Any

    def start(self, request: dict[str, Any], idempotency_key: str | None = None) -> dict[str, Any]:
        """Start a durable job."""
        ...


def plan_pair_screen(
    raw: Any,
    *,
    data_dir: Path | str,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> dict[str, Any]:
    """Check a request and return its plan. Nothing starts and nothing is ranked.

    Args:
        raw: The request from the host, as a plain dictionary.
        data_dir: The Eureka data directory.
        env: The environment for the model search. The default is `os.environ`.
        home: The home folder for the model search. The default is `Path.home()`.

    Returns:
        A ready plan with a digest, a blocked plan, or a refusal dictionary.
    """
    try:
        request = normalize_request(raw)
        receipts = PlanReceipts(data_dir)
        return build_plan(request, receipts, data_dir=data_dir, env=env, home=home)
    except HostRunError as error:
        return dict(error.as_refusal())


def start_pair_screen(
    raw: Any, idempotency_key: str | None, *, manager: _Manager
) -> dict[str, Any]:
    """Start one durable job for a request that has a matching, live and unused plan.

    The function claims the plan receipt before it starts the job. When the job manager
    raises, the receipt is released (unless it was a retry) and the error is raised again.

    Args:
        raw: The request from the host, with an `approval` block.
        idempotency_key: A key of 1 to 128 characters that makes a retry safe, or None.
        manager: The job manager. Its `store.data_dir` holds the receipt store.

    Returns:
        The started job dictionary with the job id, or a refusal dictionary.

    Raises:
        Exception: Any error of `manager.start`, after the receipt was released.
    """
    if idempotency_key is not None and not 1 <= len(idempotency_key) <= _MAX_KEY_CHARS:
        return dict(
            HostRunError(
                "bad_request",
                "The idempotency key must hold 1 to 128 characters.",
                "Send a key of 1 to 128 characters, or no key.",
            ).as_refusal()
        )
    try:
        request = normalize_request(raw)
        receipts = PlanReceipts(manager.store.data_dir)
        claim = check_start(request, receipts, idempotency_key)
    except HostRunError as error:
        return dict(error.as_refusal())
    try:
        started = manager.start(build_job_request(request), idempotency_key)
    except BaseException:
        if not claim.retry:
            receipts.release(claim.receipt_id)
        raise
    receipts.attach_job(claim.receipt_id, started["job_id"])
    approval = request.approval
    return {
        **started,
        "capability_id": CAPABILITY_ID,
        "label": LABEL,
        "room_write": "not_performed",
        "approval": {
            "approval_ref": approval.approval_ref if approval is not None else None,
            "verified_by_engine": False,
        },
        "next": _NEXT,
    }
