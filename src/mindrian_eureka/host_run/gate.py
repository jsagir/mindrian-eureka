"""The approval gate of the host pair screen run.

A host makes a plan, shows it to a person, and later starts the run with an approval block
that names the digest of the plan. Eureka cannot prove that a person approved. It can make
the order plan, approval, start mechanical, bind the start to the exact planned bundle,
and keep an audit row.

This module is plain Python. It imports no numpy, pydantic or mcp.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mindrian_eureka.host_run.contracts import (
    CAPABILITY_ID,
    PLAN_TTL_SECONDS,
    RECEIPT_RETENTION_SECONDS,
    HostRunError,
    NormalizedRequest,
)

__all__ = ["RECEIPT_FILE_NAME", "Claim", "PlanReceipts", "check_start", "plan_digest"]

RECEIPT_FILE_NAME: Final[str] = "plan-receipts.sqlite3"
_DIR_MODE: Final[int] = 0o700
_FILE_MODE: Final[int] = 0o600
_SHOWN_DIGEST_CHARS: Final[int] = 12
_BUSY_TIMEOUT_SECONDS: Final[int] = 30

_CREATE_TABLE: Final[str] = (
    "CREATE TABLE IF NOT EXISTS receipts ("
    " receipt_id INTEGER PRIMARY KEY AUTOINCREMENT,"
    " plan_digest TEXT NOT NULL,"
    " scope_id TEXT NOT NULL,"
    " snapshot_id TEXT NOT NULL,"
    " created_at REAL NOT NULL,"
    " expires_at REAL NOT NULL,"
    " consumed_at REAL,"
    " approval_ref TEXT,"
    " idempotency_key TEXT,"
    " job_id TEXT)"
)
_CREATE_INDEX: Final[str] = (
    "CREATE INDEX IF NOT EXISTS receipts_digest ON receipts (plan_digest, receipt_id)"
)


def plan_digest(request: NormalizedRequest) -> str:
    """Return the digest that binds a start to a plan.

    The digest covers the capability, the objective, the scope, the snapshot, `top_k` and
    every artifact (id, source reference, title and text hash), sorted by id. It does not
    cover the approval block.

    Args:
        request: A checked request.

    Returns:
        The sha256 of the canonical JSON basis, as 64 lowercase hex characters.
    """
    basis = {
        "capability_id": CAPABILITY_ID,
        "objective": request.objective,
        "scope_id": request.scope_id,
        "snapshot_id": request.snapshot_id,
        "top_k": request.top_k,
        "artifacts": [
            {
                "id": artifact.id,
                "source_ref": artifact.source_ref,
                "title": artifact.title,
                "text_sha256": artifact.text_sha256,
            }
            for artifact in sorted(request.artifacts, key=lambda item: item.id)
        ],
    }
    text = json.dumps(basis, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Claim:
    """The result of a successful claim of a receipt.

    Attributes:
        receipt_id: The id of the receipt row.
        retry: True when the same approval and idempotency key claimed this receipt before.
    """

    receipt_id: int
    retry: bool


class PlanReceipts:
    """A private store of plan receipts. It holds digests, ids and times only.

    Each receipt lives `PLAN_TTL_SECONDS`, is claimed once, and is kept as an audit row for
    `RECEIPT_RETENTION_SECONDS`. The store never holds artifact text.
    """

    def __init__(
        self, data_dir: Path | str, *, clock: Callable[[], float] = time.time
    ) -> None:
        """Open the store and remove rows past the retention time.

        Args:
            data_dir: The Eureka data directory. It is made with mode 0700 when absent.
            clock: A function that returns the time in seconds. It is injected by tests.
        """
        self._clock = clock
        directory = Path(data_dir)
        directory.mkdir(mode=_DIR_MODE, parents=True, exist_ok=True)
        self._path = directory / RECEIPT_FILE_NAME
        with closing(self._connect()) as connection:
            connection.execute(_CREATE_TABLE)
            connection.execute(_CREATE_INDEX)
        try:
            os.chmod(self._path, _FILE_MODE)
        except OSError:
            pass
        with closing(self._connect()) as connection:
            connection.execute(
                "DELETE FROM receipts WHERE created_at < ?",
                (self._clock() - RECEIPT_RETENTION_SECONDS,),
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._path, timeout=_BUSY_TIMEOUT_SECONDS, isolation_level=None
        )
        return connection

    def record_plan(self, digest: str, scope_id: str, snapshot_id: str) -> float:
        """Add a receipt for a plan.

        Args:
            digest: The plan digest.
            scope_id: The scope id of the request.
            snapshot_id: The snapshot id of the request.

        Returns:
            The expiry time of the receipt, in seconds.
        """
        now = self._clock()
        expires_at = now + PLAN_TTL_SECONDS
        with closing(self._connect()) as connection:
            connection.execute(
                "INSERT INTO receipts (plan_digest, scope_id, snapshot_id, created_at,"
                " expires_at) VALUES (?, ?, ?, ?, ?)",
                (digest, scope_id, snapshot_id, now, expires_at),
            )
        return expires_at

    def claim(self, digest: str, approval_ref: str | None, idempotency_key: str | None) -> Claim:
        """Use a receipt once.

        Args:
            digest: The plan digest of the start request.
            approval_ref: The approval reference of the host. Stored for audit.
            idempotency_key: A key that makes a retry safe, or None.

        Returns:
            The claim. `retry` is True when the same approval and key claimed it before.

        Raises:
            HostRunError: Code `plan_unknown`, `plan_expired` or `plan_consumed`.
        """
        now = self._clock()
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                claim = self._claim_in_transaction(
                    connection, digest, approval_ref, idempotency_key, now
                )
            except BaseException:
                connection.execute("ROLLBACK")
                raise
            connection.execute("COMMIT")
        return claim

    @staticmethod
    def _claim_in_transaction(
        connection: sqlite3.Connection,
        digest: str,
        approval_ref: str | None,
        idempotency_key: str | None,
        now: float,
    ) -> Claim:
        known = connection.execute(
            "SELECT 1 FROM receipts WHERE plan_digest = ? LIMIT 1", (digest,)
        ).fetchone()
        if known is None:
            raise HostRunError(
                "plan_unknown",
                "No plan was made for this request.",
                "Call the plan tool first, show the plan, get the approval, then start.",
            )
        if idempotency_key:
            same = connection.execute(
                "SELECT receipt_id FROM receipts WHERE plan_digest = ? AND consumed_at IS NOT NULL"
                " AND idempotency_key = ? AND approval_ref IS ? ORDER BY receipt_id DESC LIMIT 1",
                (digest, idempotency_key, approval_ref),
            ).fetchone()
            if same is not None:
                return Claim(receipt_id=int(same[0]), retry=True)
        live = connection.execute(
            "SELECT receipt_id, consumed_at FROM receipts WHERE plan_digest = ?"
            " AND expires_at >= ? ORDER BY receipt_id DESC",
            (digest, now),
        ).fetchall()
        if not live:
            raise HostRunError(
                "plan_expired",
                "The plan is older than 24 hours.",
                "Call the plan tool again, show the new plan and get a new approval.",
            )
        free = [row for row in live if row[1] is None]
        if not free:
            raise HostRunError(
                "plan_consumed",
                "The approval for this plan was already used.",
                "Call the plan tool again and get a new approval, "
                "or retry with the same idempotency key.",
            )
        receipt_id = int(free[0][0])
        connection.execute(
            "UPDATE receipts SET consumed_at = ?, approval_ref = ?, idempotency_key = ?"
            " WHERE receipt_id = ?",
            (now, approval_ref, idempotency_key or None, receipt_id),
        )
        return Claim(receipt_id=receipt_id, retry=False)

    def release(self, receipt_id: int) -> None:
        """Make a claimed receipt claimable again, for a start that failed before the job.

        Args:
            receipt_id: The id from the `Claim`.
        """
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE receipts SET consumed_at = NULL, approval_ref = NULL,"
                " idempotency_key = NULL, job_id = NULL WHERE receipt_id = ?",
                (receipt_id,),
            )
            connection.execute("COMMIT")

    def attach_job(self, receipt_id: int, job_id: str) -> None:
        """Store the job id on the receipt row.

        Args:
            receipt_id: The id from the `Claim`.
            job_id: The id of the job that the start made.
        """
        with closing(self._connect()) as connection:
            connection.execute(
                "UPDATE receipts SET job_id = ? WHERE receipt_id = ?", (job_id, receipt_id)
            )


def check_start(
    request: NormalizedRequest, receipts: PlanReceipts, idempotency_key: str | None
) -> Claim:
    """Check that a start request has a matching, live and unused plan, and claim it.

    Args:
        request: A checked start request.
        receipts: The receipt store.
        idempotency_key: A key that makes a retry safe, or None.

    Returns:
        The claim of the receipt.

    Raises:
        HostRunError: Code `approval_missing`, `plan_mismatch`, `plan_unknown`,
            `plan_expired` or `plan_consumed`. A refusal starts nothing.
    """
    approval = request.approval
    if approval is None:
        raise HostRunError(
            "approval_missing",
            "The start request has no approval block.",
            "Send the approval block with the digest of the plan and the reference "
            "of the approval.",
        )
    digest = plan_digest(request)
    if approval.plan_digest != digest:
        raise HostRunError(
            "plan_mismatch",
            "The request differs from the planned request. "
            f"The approval names plan {approval.plan_digest[:_SHOWN_DIGEST_CHARS]}, "
            f"this request is plan {digest[:_SHOWN_DIGEST_CHARS]}.",
            "Send the same request that was planned, or call the plan tool again "
            "for this request.",
        )
    return receipts.claim(digest, approval.approval_ref, idempotency_key)
