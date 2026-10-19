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
from ..structure_mapping import workflow as sme_workflow
from ..decision_patterns import algorithm as decision_patterns
from .. import discovery_workflows
from ..pitch_analysis import analyze_corpus
from ..hsi_engine import run_hsi, HSIInputError
from ..analogy_fitness import assess_analogy_fitness, AnalogyInputError, AnalogyUnavailable
from ..workflow_handlers import HANDLERS as WORKFLOW_HANDLERS, NodeRuntimeUnavailable
from ..graph_relations.runner import GraphInputError
from ..contracts import ContractError, ResultContractError, schema_for, validate_request, validate_result


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
    snapshot_id: str | None = Field(default=None, min_length=1, max_length=256)
    research_grant_id: str | None = Field(default=None, max_length=256)
    artifacts: list[ArtifactInput] = Field(min_length=2, max_length=2500)
    top_k: int = Field(default=20, ge=1, le=100)
    scoring: Literal["hybrid_2026", "legacy"] = "hybrid_2026"
    lex_weight: float = Field(default=0.5, ge=0, le=1)
    min_percentile: float = Field(default=0.9, ge=0, le=1)


class OpportunityScoutInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: str = Field(min_length=1, max_length=5000)
    scope_id: str = Field(min_length=1, max_length=256)
    snapshot_id: str | None = Field(default=None, min_length=1, max_length=256)
    artifacts: list[ArtifactInput] = Field(min_length=2, max_length=2500)
    top_k: int = Field(default=20, ge=1, le=100)
    scoring: Literal["hybrid_2026", "legacy"] = "hybrid_2026"
    lex_weight: float = Field(default=0.5, ge=0, le=1)
    min_percentile: float = Field(default=0.9, ge=0, le=1)
    dense_vectors: dict[str, list[float]] | None = None
    # Optional provenance envelope emitted by graph.prepare_artifact_bundle.
    schema_version: Literal["eureka.graph-artifact-bundle.v1"] | None = None
    capability_id: Literal["graph.prepare_artifact_bundle"] | None = None
    status: Literal["completed_projection"] | None = None
    projection: dict | None = None
    handoff: dict | None = None
    limitations: list[str] | None = None


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str = Field(min_length=1, max_length=128)
    candidate_id: str = Field(min_length=1, max_length=128)
    useful: bool
    direction_correct: bool
    already_known: bool
    note: str = Field(default="", max_length=1000)


class ResearchPlanInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str = Field(min_length=1, max_length=128)
    stage: Literal["mechanism_discovery", "inference_verification"]
    scope_id: str = Field(min_length=1, max_length=256)
    queries: list[dict] = Field(min_length=1, max_length=20)
    parent_result_id: str | None = Field(default=None, max_length=128)


class ResearchBundleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan: dict
    bundle: dict


class StructureMappingInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document: dict


class FinalizeSMEInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mapping_result: dict
    verification_plan: dict
    evidence_bundle: dict
    assessments: list[dict]


class DecisionSequenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope_id: str = Field(min_length=1, max_length=256)
    snapshot_id: str | None = Field(default=None, min_length=1, max_length=256)
    sequence_id: str = Field(min_length=1, max_length=256)
    observations: list[dict] = Field(min_length=1, max_length=2000)
    models: list[dict] = Field(min_length=2, max_length=5)


class DecisionSequenceFitInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    training_mode: Literal["exploratory_unlabeled_baum_welch"]
    seed_model: dict
    sequences: list[dict] = Field(min_length=2, max_length=500)
    model_id: str | None = Field(default=None, max_length=128)
    label: str | None = Field(default=None, max_length=256)
    max_iterations: int = Field(default=100, ge=1, le=1000)
    tolerance: float = Field(default=0.001, ge=0)


server = MCPServer("MindrianOS Eureka")
manager = JobManager()
MODEL_PATH = os.environ.get("MINDRIAN_EUREKA_RS_MODEL_PATH", "sentence-transformers/all-MiniLM-L6-v2")
MODEL_REVISION = os.environ.get("MINDRIAN_EUREKA_RS_MODEL_REVISION") or None
ENCODER = os.environ.get("MINDRIAN_EUREKA_RS_ENCODER", "sentence-transformers")
WORKFLOW_PATH = Path(__file__).resolve().parents[1] / "data" / "mos-opportunity-discovery.v1.json"
CAPABILITY_CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "capability-catalog.v1.json"
if ENCODER not in ("reference-bert", "sentence-transformers"):
    log.error("Invalid MINDRIAN_EUREKA_RS_ENCODER; using sentence-transformers")
    ENCODER = "sentence-transformers"


def _request_payload(request: ScoutRunInput) -> dict:
    artifacts = [item.model_dump(exclude_none=True) for item in request.artifacts]
    payload = {
        "objective": request.objective,
        "mode": request.mode,
        "scope_id": request.scope_id,
        "snapshot_id": request.snapshot_id,
        "research_grant_id": request.research_grant_id,
        "artifacts": artifacts,
        "scoring": request.scoring,
        "lex_weight": request.lex_weight,
        "min_percentile": request.min_percentile,
    }
    payload = {key: value for key, value in payload.items() if value is not None}
    validate_request(CAPABILITY_ID, payload)
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
    """List runnable and planned capabilities with their actual readiness."""
    try:
        return json.loads(CAPABILITY_CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.exception("Capability catalog unavailable")
        return {"schema_version": "eureka.capability-catalog.v1", "status": "unavailable", "capabilities": [], "error": str(exc)}


@server.tool()
def scout_capability(capability_id: str) -> dict:
    """Return one capability's JTBD, prerequisites, readiness, and limits."""
    catalog = scout_capabilities()
    for capability in catalog.get("capabilities", []):
        if capability.get("id") == capability_id:
            return capability
    return {"status": "not_found", "capability_id": capability_id}


@server.tool()
def scout_capability_contract(capability_id: str) -> dict:
    """Return a capability record with its packaged JSON input/output contracts.

    Use this before scout_run_workflow when the catalog entry names schema
    files. A not_published result is explicit; it must not be treated as an
    unconstrained or production-ready input contract.
    """
    capability = scout_capability(capability_id)
    if capability.get("status") == "not_found":
        return capability
    schemas = {}
    for direction in ("input", "output"):
        try:
            schemas[direction] = schema_for(capability_id, direction) or {"status": "not_published"}
        except (OSError, json.JSONDecodeError, ContractError) as exc:
            log.exception("Capability schema unavailable for %s", capability_id)
            schemas[direction] = {"status": "unavailable", "detail": str(exc)}
    return {"capability": capability, "schemas": schemas}


@server.resource("scout://capabilities")
def capabilities_resource() -> str:
    """Capability catalog for the MindrianOS host application."""
    return json.dumps(scout_capabilities(), ensure_ascii=False)


@server.tool()
def scout_host_workflow() -> dict:
    """Return the MindrianOS orchestration contract, including native host actions and approval boundaries."""
    try:
        return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    except OSError as exc:
        log.exception("MindrianOS workflow contract is unavailable")
        return {
            "status": "unavailable",
            "reason": "workflow_contract_unavailable",
            "detail": str(exc),
        }


@server.resource("scout://workflows/mos-opportunity-discovery")
def host_workflow_resource() -> str:
    """Machine-readable /m:os:eureka workflow for the MindrianOS host."""
    return json.dumps(scout_host_workflow(), ensure_ascii=False)


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
def scout_start_opportunity_signal_scout(request: OpportunityScoutInput, idempotency_key: str | None = None) -> dict:
    """Run RS and HSI over the same local snapshot and merge pair signals for review.

    It produces a candidate-pair shortlist only; it does not run Theo, evidence
    retrieval, SME adjudication, opportunity qualification, or room writes.
    """
    if idempotency_key is not None and not (1 <= len(idempotency_key) <= 128):
        raise ValueError("idempotency_key must contain 1 to 128 characters")
    validate_request("opportunity.synthesize_discovery_signals", request.model_dump(exclude_none=True))
    artifacts = [item.model_dump(exclude_none=True) for item in request.artifacts]
    payload = {
        "capability_id": "opportunity.synthesize_discovery_signals",
        "objective": request.objective, "mode": "local", "scope_id": request.scope_id,
        "snapshot_id": request.snapshot_id, "scoring": request.scoring,
        "lex_weight": request.lex_weight, "min_percentile": request.min_percentile,
        "artifacts": artifacts, "top_k": request.top_k,
        "encoder": ENCODER, "model_path": MODEL_PATH, "model_revision": MODEL_REVISION,
        "dense_vectors": request.dense_vectors,
    }
    validate_document({key: payload[key] for key in ("objective", "mode", "scope_id", "artifacts")})
    if sum(len(item["text"].encode("utf-8")) for item in artifacts) > 20 * 1024 * 1024:
        raise ValueError("Artifact bundle exceeds the 20 MiB text limit")
    if len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > 20 * 1024 * 1024:
        raise ValueError("Scout request exceeds 20 MiB")
    if request.dense_vectors is not None and set(request.dense_vectors) != {item["id"] for item in artifacts}:
        raise ValueError("dense_vectors must include exactly one vector for every artifact")
    return manager.start(payload, idempotency_key)


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


@server.tool()
def scout_sme_prepare_research(request: ResearchPlanInput) -> dict:
    """Freeze exact cross-domain discovery or inference-check queries for host approval."""
    raw = request.model_dump(exclude_none=True)
    validate_request("analogy.cross_domain_research", {"stage": "prepare_research_plan", "request": raw})
    result = sme_workflow.prepare_research_plan(**raw)
    validate_result("analogy.cross_domain_research", result)
    return result


@server.tool()
def scout_sme_validate_research_bundle(request: ResearchBundleInput) -> dict:
    """Validate returned source and query lineage; this does not verify host approval."""
    raw = request.model_dump()
    validate_request("analogy.cross_domain_research", {"stage": "validate_research_bundle", "request": raw})
    result = sme_workflow.validate_research_bundle(request.plan, request.bundle)
    validate_result("analogy.cross_domain_research", result)
    return result


@server.tool()
def scout_sme_map(request: StructureMappingInput) -> dict:
    """Run the local deterministic SME map over host-prepared, claim-linked structures."""
    payload = request.model_dump()
    validate_request("analogy.map_structure", payload)
    result = sme_workflow.map_structures(request.document)
    validate_result("analogy.map_structure", result)
    return result


@server.tool()
def scout_sme_finalize(request: FinalizeSMEInput) -> dict:
    """Attach reviewed evidence outcomes to mapping inferences; never files to a portfolio."""
    raw = request.model_dump()
    validate_request("analogy.cross_domain_research", {"stage": "finalize_assessments", "request": raw})
    result = sme_workflow.finalize_assessments(
        request.mapping_result, request.verification_plan, request.evidence_bundle, request.assessments
    )
    validate_result("analogy.cross_domain_research", result)
    return result


@server.tool()
def decision_compare_sequence_patterns(request: DecisionSequenceInput) -> dict:
    """Compare a coded decision sequence under caller-supplied HMM parameters."""
    payload = request.model_dump(exclude_none=True)
    validate_request("decision.compare_sequence_patterns", payload)
    result = decision_patterns.analyze_sequence(payload)
    validate_result("decision.compare_sequence_patterns", result)
    return result


@server.tool()
def decision_fit_sequence_patterns(request: DecisionSequenceFitInput) -> dict:
    """Exploratorily fit HMM parameters from multiple coded traces and an explicit seed.

    Requires at least two independently coded traces and 32 total observations.
    The fit is unvalidated and must not be used to assess, rank, or diagnose people.
    """
    payload = request.model_dump(exclude_none=True)
    validate_request("decision.fit_sequence_patterns", payload)
    result = decision_patterns.fit_model(payload)
    validate_result("decision.fit_sequence_patterns", result)
    return result


@server.tool()
def scout_run_workflow(capability_id: str, request: dict) -> dict:
    """Run a local, source-bounded discovery workflow stage.

    This dispatches only workflows implemented in this repository. External
    research remains host-brokered, and outputs never write to MindrianOS.
    """
    if not isinstance(request, dict):
        raise ValueError("request must be a JSON object")
    if len(json.dumps(request, ensure_ascii=False).encode("utf-8")) > 20 * 1024 * 1024:
        return {"status": "invalid_input", "capability_id": capability_id, "error": "request exceeds 20 MiB"}
    dispatch = WORKFLOW_HANDLERS
    handler = dispatch.get(capability_id)
    if handler is None:
        return {"status": "blocked_or_not_implemented", "capability_id": capability_id,
                "detail": "This capability has no runnable local workflow handler. Inspect scout_capability for its current readiness."}
    try:
        validate_request(capability_id, request)
        result = handler(request)
        try:
            validate_result(capability_id, result)
        except ResultContractError as exc:
            log.exception("Workflow %s violated its output contract", capability_id)
            return {"status": "failed", "capability_id": capability_id,
                    "reason": "output_contract_violation", "detail": str(exc)}
        return result
    except ContractError as exc:
        return {"status": "invalid_input", "capability_id": capability_id, "error": str(exc)}
    except discovery_workflows.WorkflowInputError as exc:
        return {"status": "invalid_input", "capability_id": capability_id, "error": str(exc)}
    except sme_workflow.WorkflowError as exc:
        return {"status": "invalid_input", "capability_id": capability_id, "error": str(exc)}
    except HSIInputError as exc:
        return {"status": "invalid_input", "capability_id": capability_id, "error": str(exc)}
    except GraphInputError as exc:
        return {"status": "invalid_input", "capability_id": capability_id, "error": str(exc)}
    except AnalogyInputError as exc:
        return {"status": "invalid_input", "capability_id": capability_id, "error": str(exc)}
    except AnalogyUnavailable as exc:
        return {"status": "blocked", "capability_id": capability_id, "reason": "local_model_unavailable", "detail": str(exc)}
    except NodeRuntimeUnavailable as exc:
        return {"status": "blocked", "capability_id": capability_id, "reason": "runtime_unavailable", "detail": str(exc)}
    except Exception as exc:
        log.exception("Workflow %s failed", capability_id)
        return {"status": "failed", "capability_id": capability_id, "error": str(exc)}


def _run_jason_workflow(payload: dict) -> dict:
    result = analyze_corpus(payload, legacy=bool(payload.get("legacy", False)),
                            input_bytes=json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    if result.get("errors"):
        result["status"] = "invalid_input"
    if payload.get("scope_id") is not None or payload.get("snapshot_id") is not None:
        result["scope"] = {"scope_id": payload.get("scope_id"), "snapshot_id": payload.get("snapshot_id")}
    return result


@server.tool()
def scout_compare_text_differences(request: dict) -> dict:
    """Compare supplied texts for overlap, restatement signals, and claim-level matches.

    This is Jason's descriptive differential-analysis method. A high gap is a
    paraphrase signal, never a novelty or innovation score. Any dense model must
    be provided locally through MINDRIAN_EUREKA_JASON_MODEL_PATH.
    """
    if not isinstance(request, dict):
        return {"status": "invalid_input", "error": "request must be an object"}
    try:
        encoded = json.dumps(request, ensure_ascii=False).encode("utf-8")
        if len(encoded) > 20 * 1024 * 1024:
            return {"status": "invalid_input", "error": "request exceeds 20 MiB"}
        validate_request("analysis.compare_text_differences", request)
        result = _run_jason_workflow(request)
        if not result.get("errors"):
            validate_result("analysis.compare_text_differences", result)
        return result
    except ContractError as exc:
        return {"status": "invalid_input", "capability_id": "analysis.compare_text_differences", "error": str(exc)}
    except ResultContractError as exc:
        return {"status": "failed", "capability_id": "analysis.compare_text_differences",
                "reason": "output_contract_violation", "error": str(exc)}
    except Exception as exc:
        log.exception("Jason text-difference analysis failed")
        return {"status": "failed", "error": str(exc)}


@server.tool()
def scout_find_hybrid_similarity_pairs(request: dict) -> dict:
    """Run the local HSI differential-pair method over host-supplied records."""
    if not isinstance(request, dict):
        return {"status": "invalid_input", "error": "request must be an object"}
    try:
        if len(json.dumps(request, ensure_ascii=False).encode("utf-8")) > 20 * 1024 * 1024:
            return {"status": "invalid_input", "error": "request exceeds 20 MiB"}
        validate_request("portfolio.find_hybrid_similarity_pairs", request)
        result = run_hsi(request)
        validate_result("portfolio.find_hybrid_similarity_pairs", result)
        return result
    except ContractError as exc:
        return {"status": "invalid_input", "capability_id": "portfolio.find_hybrid_similarity_pairs", "error": str(exc)}
    except ResultContractError as exc:
        return {"status": "failed", "capability_id": "portfolio.find_hybrid_similarity_pairs",
                "reason": "output_contract_violation", "error": str(exc)}
    except HSIInputError as exc:
        return {"status": "invalid_input", "capability_id": "portfolio.find_hybrid_similarity_pairs", "error": str(exc)}
    except Exception as exc:
        log.exception("HSI pair analysis failed")
        return {"status": "failed", "capability_id": "portfolio.find_hybrid_similarity_pairs", "error": str(exc)}


@server.tool()
def scout_assess_analogy_fitness(request: dict) -> dict:
    """Compare source/target SAPPhIRE structures with a local embedding model."""
    try:
        if not isinstance(request, dict) or len(json.dumps(request, ensure_ascii=False).encode("utf-8")) > 10 * 1024 * 1024:
            return {"status": "invalid_input", "capability_id": "analogy.assess_structural_fitness", "error": "request must be an object no larger than 10 MiB"}
        validate_request("analogy.assess_structural_fitness", request)
        result = assess_analogy_fitness(request)
        if result.get("status") == "completed_experimental":
            validate_result("analogy.assess_structural_fitness", result)
        return result
    except ContractError as exc:
        return {"status": "invalid_input", "capability_id": "analogy.assess_structural_fitness", "error": str(exc)}
    except ResultContractError as exc:
        return {"status": "failed", "capability_id": "analogy.assess_structural_fitness",
                "reason": "output_contract_violation", "error": str(exc)}
    except AnalogyInputError as exc:
        return {"status": "invalid_input", "capability_id": "analogy.assess_structural_fitness", "error": str(exc)}
    except AnalogyUnavailable as exc:
        return {"status": "blocked", "capability_id": "analogy.assess_structural_fitness", "reason": "local_model_unavailable", "detail": str(exc)}
    except Exception as exc:
        log.exception("Analogy fitness assessment failed")
        return {"status": "failed", "capability_id": "analogy.assess_structural_fitness", "error": str(exc)}


def main() -> None:
    manager  # initialize private local data directory before serving
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
