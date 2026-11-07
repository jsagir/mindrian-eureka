"""Durable local HSI + RS signal-synthesis workflow.

This combines two independent retrieval signals into a review shortlist. It
does not qualify opportunities or infer that a pair should be combined.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any, Callable

from .hsi_engine import run_hsi
from .limits import MAX_ARTIFACTS
from .opportunity_pairs.algorithm import RunCancelled
from .opportunity_pairs.runner import run_document

log = logging.getLogger(__name__)


def run_signal_synthesis(request: dict[str, Any], *, data_dir, job_id: str,
                         cancel_check: Callable[[], bool] | None = None,
                         stage_callback: Callable[[str], None] | None = None) -> dict[str, Any]:
    """Run RS and HSI locally, then merge by artifact pair without score fusion."""
    artifacts = request["artifacts"]
    if len(artifacts) > MAX_ARTIFACTS:
        raise ValueError(f"multi-engine scout supports at most {MAX_ARTIFACTS} artifacts")
    if cancel_check and cancel_check():
        raise RuntimeError("Run cancelled")
    if stage_callback:
        stage_callback("rs-cross-domain-pair-discovery")
    rs = run_document(
        request, encoder_name=request["encoder"], model_path=request["model_path"],
        allow_model_download=False, top_k=request.get("top_k", 20), job_id=job_id,
        model_revision=request.get("model_revision"), cache_path=data_dir / "embeddings.sqlite3",
        cancel_check=cancel_check, stage_callback=stage_callback,
    )
    if rs.get("status") not in {"completed", "completed_empty"}:
        return {"schema_version": "eureka.discovery-signals.v1", "capability_id": "opportunity.synthesize_discovery_signals",
                "status": rs.get("status", "failed"), "scope": rs.get("scope"), "rs_result": rs,
                "outputs": [], "warnings": ["RS did not complete; HSI was not run."]}
    if cancel_check and cancel_check():
        raise RuntimeError("Run cancelled")
    if stage_callback:
        stage_callback("hsi-hybrid-similarity-pairs")
    hsi_input = {"scope_id": request.get("scope_id"), "snapshot_id": rs.get("scope", {}).get("snapshot_id"),
                 "artifacts": artifacts, "top_k": request.get("top_k", 20), "ranking": "percentile"}
    if request.get("dense_vectors") is not None:
        hsi_input["dense_vectors"] = request["dense_vectors"]
    hsi = run_hsi(hsi_input)
    if cancel_check and cancel_check():
        raise RunCancelled("Run cancelled after the current HSI matrix calculation")
    rs_by_pair: dict[tuple[str, str], dict] = {}
    for row in rs.get("outputs", []):
        payload = row.get("payload", {})
        left, right = payload.get("left", {}), payload.get("right", {})
        a, b = left.get("artifact_id"), right.get("artifact_id")
        if a and b:
            rs_by_pair[tuple(sorted((a, b)))] = row
    hsi_by_pair: dict[tuple[str, str], dict] = {}
    for row in hsi.get("hsi_pairs", []):
        a, b = row.get("left_id"), row.get("right_id")
        if a and b:
            hsi_by_pair[tuple(sorted((a, b)))] = row
    index = {row["id"]: row for row in artifacts}
    pair_keys = sorted(set(rs_by_pair) | set(hsi_by_pair))
    outputs = []
    for rank, pair in enumerate(pair_keys, 1):
        rs_row, hsi_row = rs_by_pair.get(pair), hsi_by_pair.get(pair)
        digest = hashlib.sha256("\0".join(pair).encode("utf-8")).hexdigest()[:16]
        outputs.append({
            "id": f"discovery-pair-{digest}", "kind": "cross_engine_pair_signal", "rank": rank,
            "payload": {
                "left": {"artifact_id": pair[0], "title": index[pair[0]].get("title", ""), "source_ref": index[pair[0]].get("source_ref") or index[pair[0]].get("url") or index[pair[0]].get("path")},
                "right": {"artifact_id": pair[1], "title": index[pair[1]].get("title", ""), "source_ref": index[pair[1]].get("source_ref") or index[pair[1]].get("url") or index[pair[1]].get("path")},
                "signals": {
                    "rs": ({"rank": rs_row.get("rank"), "structural_similarity": rs_row.get("payload", {}).get("structural_similarity"), "semantic_similarity": rs_row.get("payload", {}).get("semantic_similarity"), "direction": rs_row.get("payload", {}).get("direction"), "direction_meaning": rs_row.get("payload", {}).get("direction_meaning")} if rs_row else None),
                    "hsi": ({"rank": hsi_row.get("rank"), "hsi_score": hsi_row.get("hsi_score"), "hsi_percentile": hsi_row.get("hsi_percentile"), "surprise_type": hsi_row.get("surprise_type"), "surprise_type_meaning": hsi_row.get("surprise_type_meaning"), "source_trail": hsi_row.get("source_trail")} if hsi_row else None),
                    "method_signal_count": int(rs_row is not None) + int(hsi_row is not None),
                    "best_within_engine_rank": min([r for r in (rs_row.get("rank") if rs_row else None, hsi_row.get("rank") if hsi_row else None) if isinstance(r, int)] or [None]),
                },
                "source_evidence": {
                    "rs": rs_row.get("review_context") if rs_row else None,
                    "hsi": hsi_row.get("source_trail") if hsi_row else None,
                },
                "direction": rs_row.get("payload", {}).get("direction") if rs_row else "unknown",
                "interpretation": "Pair-level discovery signal. No technical, commercial, or biological complementarity has been established.",
                "next_host_actions": ["Resolve both source records", "Use /mos:find-connections for a user-selected pair", "Develop evidence and counterevidence through the approved research broker", "Send a structurally framed transfer to SME only if a mechanism mapping is proposed"],
            },
        })
    outputs.sort(key=lambda row: (
        -row["payload"]["signals"]["method_signal_count"],
        row["payload"]["signals"]["best_within_engine_rank"] if row["payload"]["signals"]["best_within_engine_rank"] is not None else 10**9,
        row["id"],
    ))
    for rank, row in enumerate(outputs, 1):
        row["rank"] = rank
    status = "completed" if outputs else "completed_empty"
    return {
        "schema_version": "eureka.discovery-signals.v1", "capability_id": "opportunity.synthesize_discovery_signals",
        "status": status, "job_id": job_id, "scope": rs.get("scope"), "outputs": outputs,
        "method_details": {"input_objective": request.get("objective", ""), "mode": request.get("mode"),
                           "encoder": rs.get("method_details", {}).get("encoder", {}),
                           "engines": ["RS cross-domain pair discovery", "HSI hybrid similarity differential"]},
        "engine_runs": {
            "rs": {"status": rs.get("status"), "candidate_count": len(rs_by_pair), "method_details": rs.get("method_details")},
            "hsi": {"status": hsi.get("status"), "candidate_count": len(hsi_by_pair), "metadata": hsi.get("metadata")},
        },
        "candidate_count": len(outputs),
        "ranking_basis": "method_signal_count desc, then best within-engine rank asc, then stable id; scores are not combined",
        "warnings": list(rs.get("warnings", [])) + list(hsi.get("warnings", [])) + [
            "The shortlist is a union of the two engines' top-k retrieval candidates; no scores were combined.",
            "No remote sources, Theo case review, graph traversal, SME map, or opportunity qualification ran in this job.",
        ],
        "portfolio_write": "not_performed",
    }
