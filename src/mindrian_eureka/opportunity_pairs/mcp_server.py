"""Local MCP facade for the cross-domain opportunity-pair capability.

The server reads only artifact text supplied by the host. It does not accept
filesystem paths, fetch research, or change MindrianOS room/portfolio state.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from . import CAPABILITY_ID, CAPABILITY_VERSION
from .jobs import JobManager
from .runner import validate_document


logging.basicConfig(stream=sys.stderr, level=os.environ.get("MINDRIAN_EUREKA_LOG_LEVEL", "WARNING"))
log = logging.getLogger("mindrian_eureka.mcp")

try:
    from mcp.server import MCPServer
except ImportError:  # compatibility with the installed 1.x SDK line
    from mcp.server.fastmcp import FastMCP as MCPServer


class ArtifactInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=256)
    source_ref: str = Field(min_length=1, max_length=2048)
    title: str = Field(default="", max_length=2000)
    text: str = Field(min_length=1, max_length=1_000_000)
    corpus: Literal["room", "external"] = "room"
    media_type: str | None = Field(default=None, max_length=128)
    sha256: str | None = Field(default=None, pattern=r"^[a-fA-F0-9]{64}$")


class ScoutRunInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: str = Field(min_length=1, max_length=5000)
    mode: Literal["local", "external", "hybrid"] = "local"
    scope_id: str = Field(min_length=1, max_length=256)
    research_grant_id: str | None = Field(default=None, max_length=256)
    artifacts: list[ArtifactInput] = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=20, ge=1, le=100)


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str = Field(min_length=1, max_length=128)
    candidate_id: str = Field(min_length=1, max_length=128)
    useful: bool
    direction_correct: bool
    already_known: bool
    note: str = Field(default="", max_length=1000)


server = MCPServer("MindrianOS Eureka")
manager = JobManager()
MODEL_PATH = os.environ.get("MINDRIAN_EUREKA_RS_MODEL_PATH", "sentence-transformers/all-MiniLM-L6-v2")
MODEL_REVISION = os.environ.get("MINDRIAN_EUREKA_RS_MODEL_REVISION") or None
ENCODER = os.environ.get("MINDRIAN_EUREKA_RS_ENCODER", "sentence-transformers")
if ENCODER not in ("reference-bert", "sentence-transformers"):
    log.error("Invalid MINDRIAN_EUREKA_RS_ENCODER; using sentence-transformers")
    ENCODER = "sentence-transformers"


def _request_payload(request: ScoutRunInput) -> dict:
    artifacts = [item.model_dump(exclude_none=True) for item in request.artifacts]
    payload = {
        "objective": request.objective,
        "mode": request.mode,
        "scope_id": request.scope_id,
        "research_grant_id": request.research_grant_id,
        "artifacts": artifacts,
    }
    validate_document(payload)
    text_bytes = sum(len(item["text"].encode("utf-8")) for item in artifacts)
    if text_bytes > 20 * 1024 * 1024:
        raise ValueError("Artifact bundle exceeds the 20 MiB text limit")
    return {
        **payload,
        "encoder": ENCODER,
        "model_path": MODEL_PATH,
        "model_revision": MODEL_REVISION,
        "top_k": request.top_k,
    }


@server.tool()
def scout_capabilities() -> dict:
    """List available Eureka capabilities and their JTBD descriptions."""
    manifest_path = Path(__file__).resolve().parents[3] / "capabilities" / CAPABILITY_ID / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError:
        manifest = {
            "id": CAPABILITY_ID,
            "name": "Find Cross-Domain Opportunity Pairs",
            "version": CAPABILITY_VERSION,
            "status": "experimental",
        }
    return {"capabilities": [manifest]}


@server.resource("scout://capabilities")
def capabilities_resource() -> str:
    """Capability catalog for the MindrianOS host application."""
    return json.dumps(scout_capabilities(), ensure_ascii=False)


@server.tool()
def scout_plan(request: ScoutRunInput) -> dict:
    """Validate the requested scope and explain the local analysis plan without running it."""
    if request.mode in ("external", "hybrid") and not request.research_grant_id:
        return {"status": "blocked", "reason": "approved research_grant_id is required for external material"}
    payload = _request_payload(request)
    room_count = sum(item["corpus"] == "room" for item in payload["artifacts"])
    external_count = sum(item["corpus"] == "external" for item in payload["artifacts"])
    return {
        "status": "ready",
        "capability_id": CAPABILITY_ID,
        "mode": request.mode,
        "scope_id": request.scope_id,
        "room_artifacts": room_count,
        "external_artifacts": external_count,
        "candidate_limit": request.top_k,
        "encoder": {"name": ENCODER, "model": MODEL_PATH, "revision": MODEL_REVISION},
        "network": "denied by this server; external evidence must already be in the host-approved bundle",
        "stages": ["validate bundle", "compute structural signal", "compute semantic signal", "rank unique pairs", "return source-linked candidates"],
        "expected_output": "ranked candidate pairs with both similarities, signed direction, provenance, and bounded review context",
    }


@server.tool()
def scout_start(request: ScoutRunInput, idempotency_key: str | None = None) -> dict:
    """Start a bounded local RS run over only the host-supplied artifact bundle."""
    payload = _request_payload(request)
    if request.mode in ("external", "hybrid") and not request.research_grant_id:
        raise ValueError("External and hybrid runs require the host's approved research_grant_id")
    if idempotency_key is not None and not (1 <= len(idempotency_key) <= 128):
        raise ValueError("idempotency_key must contain 1 to 128 characters")
    result = manager.start(payload, idempotency_key)
    log.info("Started job %s for scoped request", result["job_id"])
    return result


@server.tool()
def scout_status(job_id: str) -> dict:
    """Get job state, stage progress, and state-change history."""
    return manager.status(job_id)


@server.tool()
def scout_result(job_id: str) -> dict:
    """Retrieve the result envelope, or the current state if the run is not finished."""
    return manager.result(job_id)


@server.tool()
def scout_cancel(job_id: str) -> dict:
    """Cancel queued work or request cooperative cancellation of a running job."""
    return manager.cancel(job_id)


@server.tool()
def scout_record_review(review: ReviewInput) -> dict:
    """Record a human judgment for one surfaced pair; ratings do not alter ranking automatically."""
    return manager.store.record_review(
        review.job_id, review.candidate_id, useful=review.useful,
        direction_correct=review.direction_correct, already_known=review.already_known,
        note=review.note,
    )


@server.tool()
def scout_review_summary(job_id: str | None = None) -> dict:
    """Summarize human review data for evaluation; this does not imply automatic learning."""
    return manager.store.review_summary(job_id)


@server.tool()
def scout_evaluation_report() -> dict:
    """Compare human ratings by encoder/mode and show the task snapshots reviewed."""
    return manager.store.evaluation_report()


@server.tool()
def scout_delete_job(job_id: str) -> dict:
    """Delete a completed or failed job, its saved request/result, and its judgments."""
    return {"job_id": job_id, "deleted": manager.store.delete(job_id)}


@server.tool()
def scout_clear_embedding_cache() -> dict:
    """Delete all cached derived vectors from the local Eureka data directory."""
    from .cache import EmbeddingCache

    cache = EmbeddingCache(manager.store.data_dir / "embeddings.sqlite3")
    removed = cache.clear()
    return {"deleted_embeddings": removed}


def main() -> None:
    manager  # initialize private local data directory before serving
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
