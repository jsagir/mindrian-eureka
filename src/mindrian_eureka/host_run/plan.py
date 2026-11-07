"""The plan of a host pair screen run.

`build_plan` tells the host what a run will read, write and rank before anything starts. It
stages the bundle in a throwaway folder, runs the corpus builder (no model), finds the local
model without loading it, and records a receipt for a ready plan. A plan holds no artifact
text, no absolute path and no model path.

This module is plain Python. It imports no numpy, pydantic or mcp.
"""

from __future__ import annotations

import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from mindrian_eureka import models
from mindrian_eureka.host_run.bundle import stage_bundle
from mindrian_eureka.host_run.contracts import (
    CAPABILITY_ID,
    PLAN_SCHEMA,
    NormalizedRequest,
)
from mindrian_eureka.host_run.gate import PlanReceipts, plan_digest
from mindrian_eureka.limits import MAX_ARTIFACTS
from mindrian_eureka.run.contracts import (
    LABEL,
    UNUSUAL_PAIRS_CAPABILITY,
    UNUSUAL_PAIRS_NAME,
    WORDING_AND_MEANING_CAPABILITY,
    WORDING_AND_MEANING_NAME,
    EurekaError,
)
from mindrian_eureka.run.corpus import build_corpus

__all__ = ["build_plan"]

_DIR_MODE: Final[int] = 0o700
_OWNER: Final[str] = "mindrianos"
_OUTPUTS: Final[tuple[str, ...]] = (
    "unusual-pairs.json",
    "wording-and-meaning-pairs.json",
    "ranked-pairs.md",
    "manifest.json",
)
_STAGES: Final[tuple[str, ...]] = (
    "validate bundle",
    "build clean corpus",
    "rank with the unusual-pairs engine",
    "rank with the wording-and-meaning engine",
    "write hashed files and manifest",
    "return the result",
)
_NETWORK: Final[str] = "denied; the run is offline and makes no network call"
_WRITES: Final[dict[str, str]] = {
    "room": "none",
    "portfolio": "none",
    "job_store": "a result record kept for 30 days; delete it with scout_delete_job",
    "derived_vectors": "not kept",
    "plan_receipt": "digest and times only, kept 24 hours",
}
_HOW_TO_APPROVE: Final[str] = (
    "Show this plan to the person, get the approval, then call the start tool with the same "
    "request plus the approval block (the plan digest and the approval reference)."
)
_MODEL_MISSING: Final[str] = "No local model was found. Eureka does not download models."
_GENERIC_ORIGIN: Final[str] = "local model source"
_SMALL_COLLECTION: Final[int] = 10


def _blocked(
    request: NormalizedRequest, reason: str, message: str, fix: str
) -> dict[str, Any]:
    return {
        "schema_version": PLAN_SCHEMA,
        "status": "blocked",
        "label": LABEL,
        "capability_id": CAPABILITY_ID,
        "reason": reason,
        "message": message,
        "fix": fix,
        "scope_id": request.scope_id,
        "snapshot_id": request.snapshot_id,
        "host_handoff": {
            "state": "blocked",
            "owner": _OWNER,
            "next_action": "fix_and_plan_again",
        },
    }


def _clean_origin(origin: str | None) -> str:
    """Return the source category of the model, with no path in it."""
    if not origin or "/" in origin or "\\" in origin:
        return _GENERIC_ORIGIN
    return origin


def _scrub(text: str, folder: Path) -> str:
    """Remove the throwaway folder path from a text."""
    return text.replace(str(folder), "<staging>")


def _iso_utc(seconds: float) -> str:
    moment = datetime.fromtimestamp(seconds, tz=UTC)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def build_plan(
    request: NormalizedRequest,
    receipts: PlanReceipts,
    *,
    data_dir: Path | str,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> dict[str, Any]:
    """Build the plan of a run. Nothing is ranked and nothing is written to a room.

    Args:
        request: A checked request.
        receipts: The receipt store. A ready plan adds one receipt.
        data_dir: The Eureka data directory. A throwaway folder is made under it and
            removed before the function returns.
        env: The environment for the model search. The default is `os.environ`.
        home: The home folder for the model search. The default is `Path.home()`.

    Returns:
        A ready plan with the digest, counts and expected outputs, or a blocked plan with
        the reason `too_few_usable_records` or `local_model_unavailable`. A blocked plan
        records no receipt.
    """
    digest = plan_digest(request)
    base = Path(data_dir)
    base.mkdir(mode=_DIR_MODE, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base, prefix="plan-") as folder_name:
        folder = Path(folder_name)
        staged = stage_bundle(request, folder / "run")
        try:
            corpus = build_corpus(
                staged.input_dir, mapping=staged.mapping, max_artifacts=MAX_ARTIFACTS
            )
        except EurekaError as exc:
            return _blocked(
                request,
                "too_few_usable_records",
                _scrub(exc.message, folder),
                _scrub(exc.fix or "Send more artifacts with longer text.", folder),
            )
        warnings = [_scrub(line, folder) for line in corpus.warnings]
        usable = len(corpus.records)
        dropped = len(corpus.dropped)
    if usable < _SMALL_COLLECTION and not any(str(_SMALL_COLLECTION) in line for line in warnings):
        warnings.append(
            f"Only {usable} usable records. A collection of {_SMALL_COLLECTION} or more "
            "gives more useful candidates."
        )
    resolution = models.discover_model(None, env=env, home=home)
    if not resolution.ok:
        return _blocked(
            request, "local_model_unavailable", _MODEL_MISSING, models.model_fix_text()
        )
    expires_at = receipts.record_plan(digest, request.scope_id, request.snapshot_id)
    text_bytes = sum(len(artifact.text.encode("utf-8")) for artifact in request.artifacts)
    return {
        "schema_version": PLAN_SCHEMA,
        "status": "ready",
        "label": LABEL,
        "capability_id": CAPABILITY_ID,
        "plan_digest": digest,
        "expires_at": _iso_utc(expires_at),
        "scope_id": request.scope_id,
        "snapshot_id": request.snapshot_id,
        "objective": request.objective,
        "top_k": request.top_k,
        "counts": {
            "artifacts": len(request.artifacts),
            "text_bytes": text_bytes,
            "records_usable": usable,
            "records_dropped": dropped,
        },
        "engines": [
            {"name": UNUSUAL_PAIRS_NAME, "capability_id": UNUSUAL_PAIRS_CAPABILITY},
            {"name": WORDING_AND_MEANING_NAME, "capability_id": WORDING_AND_MEANING_CAPABILITY},
        ],
        "model": {"found": True, "origin": _clean_origin(resolution.origin)},
        "outputs_expected": list(_OUTPUTS),
        "network": _NETWORK,
        "writes": dict(_WRITES),
        "approval_required": True,
        "how_to_approve": _HOW_TO_APPROVE,
        "stages": list(_STAGES),
        "warnings": warnings,
        "host_handoff": {
            "state": "awaiting_approval",
            "owner": _OWNER,
            "next_action": "present_plan_and_obtain_approval",
            "approval_required": True,
        },
    }
