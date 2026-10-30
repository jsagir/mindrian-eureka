"""Offline HSI pair-scoring adapter for host-supplied artifact bundles.

Uses the reviewed 2026 HSI numerical routines, but does not read room paths,
install dependencies, fetch embeddings, or write results into a room.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Any

# This adapter must never inherit a setting that permits the reference module
# to install packages during import.
os.environ["HSI_NO_AUTO_INSTALL"] = "1"

import numpy as np

from . import hsi_reference as reference
from .limits import MAX_ARTIFACTS, MAX_TOP_K
from .opportunity_pairs.encoders import SentenceTransformerEncoder


class HSIInputError(ValueError):
    pass


def _cosine(vectors: np.ndarray) -> np.ndarray:
    return np.clip(reference.cosine_matrix(np.asarray(vectors, dtype=float)), 0.0, 1.0)


def run_hsi(document: dict[str, Any]) -> dict[str, Any]:
    artifacts = document.get("artifacts") if isinstance(document, dict) else None
    if not isinstance(artifacts, list) or not 2 <= len(artifacts) <= MAX_ARTIFACTS:
        raise HSIInputError(f"artifacts must contain 2..{MAX_ARTIFACTS} source-linked records")
    normalized = []
    seen = set()
    for index, raw in enumerate(artifacts):
        if not isinstance(raw, dict):
            raise HSIInputError(f"artifacts[{index}] must be an object")
        artifact_id, text = raw.get("id"), raw.get("text")
        source_ref = raw.get("source_ref") or raw.get("url") or raw.get("path")
        if not isinstance(artifact_id, str) or not artifact_id.strip() or artifact_id in seen:
            raise HSIInputError(f"artifacts[{index}] needs a unique, non-empty id")
        if not isinstance(text, str) or not text.strip() or len(text) > 1_000_000:
            raise HSIInputError(f"artifacts[{index}].text must contain 1..1000000 characters")
        if not isinstance(source_ref, str) or not source_ref.strip():
            raise HSIInputError(f"artifacts[{index}] needs source_ref, url, or path")
        seen.add(artifact_id)
        raw_bytes = text.encode("utf-8")
        normalized.append({"id": artifact_id, "text": text.strip(), "title": str(raw.get("title", artifact_id)),
                           "section": str(raw.get("section", "")), "path": source_ref,
                           "content_hash": hashlib.sha256(raw_bytes).hexdigest()})
    text_bytes = sum(len(row["text"].encode("utf-8")) for row in normalized)
    if text_bytes > 20 * 1024 * 1024:
        raise HSIInputError("artifact text exceeds 20 MiB")

    lexical_mode = document.get("lexical", "hybrid")
    ranking = document.get("ranking", "percentile")
    top_k = document.get("top_k", 20)
    min_percentile = document.get("min_percentile", 0.0)
    if lexical_mode not in {"hybrid", "lsa", "bm25"} or ranking not in {"percentile", "legacy"}:
        raise HSIInputError("lexical must be hybrid|lsa|bm25 and ranking must be percentile|legacy")
    if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= MAX_TOP_K:
        raise HSIInputError(f"top_k must be an integer from 1 to {MAX_TOP_K}")
    if isinstance(min_percentile, bool) or not isinstance(min_percentile, (int, float)) or not 0 <= float(min_percentile) <= 1:
        raise HSIInputError("min_percentile must be a number from 0 to 1")

    texts = [row["text"] for row in normalized]
    lsa = reference.compute_lsa_similarity(texts, seed=42)
    bm25 = reference.compute_bm25_similarity(texts)
    lexical_fusion = "equal_spread_average" if lexical_mode == "hybrid" else "none"
    if lexical_mode == "hybrid":
        lexical = reference.fuse_lexical_hybrid(lsa, bm25)
    else:
        lexical = lsa if lexical_mode == "lsa" else bm25
    semantic_method = None
    dense = document.get("dense_vectors")
    encoder = None
    if dense is not None:
        if not isinstance(dense, dict) or set(dense) != seen:
            raise HSIInputError("dense_vectors must map every artifact id exactly once")
        vectors = []
        width = None
        for artifact in normalized:
            vector = dense[artifact["id"]]
            if not isinstance(vector, list) or not vector or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) for v in vector):
                raise HSIInputError(f"dense vector for {artifact['id']} must be a finite numeric array")
            if width is not None and width != len(vector):
                raise HSIInputError("dense vectors must have equal dimensions")
            width = len(vector)
            vectors.append(vector)
        semantic = _cosine(np.asarray(vectors, dtype=float))
        semantic_method = "host-supplied-precomputed-vectors"
    else:
        model_path = os.environ.get("MINDRIAN_EUREKA_HSI_MODEL_PATH")
        if model_path:
            encoder = SentenceTransformerEncoder(model_path, allow_download=False)
            semantic = _cosine(encoder.encode(texts))
            semantic_method = f"local-sentence-transformer:{model_path}"
        else:
            # Explicitly degraded; this compares two lexical representations.
            semantic = bm25
            lexical = lsa
            # No fusion happens in the proxy: the lexical leg is LSA alone.
            lexical_fusion = "none"
            semantic_method = "lexical-only-bm25-proxy"

    computed_at = datetime.now(timezone.utc).isoformat()
    pairs, spectral = reference.compute_hsi_matrix(
        normalized, lsa, semantic, threshold=None if ranking == "percentile" else 0.30,
        lexical_matrix=lexical, bm25_matrix=bm25 if semantic_method != "lexical-only-bm25-proxy" else None,
        ranking=ranking, top_k=top_k, min_percentile=float(min_percentile), computed_at=computed_at,
    )
    return {
        "schema_version": "eureka.hsi-result.v1", "capability_id": "portfolio.find_hybrid_similarity_pairs",
        "status": "completed_degraded_lexical_only" if semantic_method == "lexical-only-bm25-proxy" else "completed_experimental",
        "scope": {"scope_id": document.get("scope_id"), "snapshot_id": document.get("snapshot_id")},
        "metadata": {"artifact_count": len(normalized), "pair_count": len(normalized) * (len(normalized) - 1) // 2,
                     "reported_pair_count": len(pairs), "lexical_method": lexical_mode, "semantic_method": semantic_method,
                     "lexical_fusion": lexical_fusion,
                     "ranking": ranking, "spectral_profiles": spectral, "generated_at": computed_at},
        "artifacts": [{"id": row["id"], "title": row["title"], "source_ref": row["path"], "content_hash": row["content_hash"]} for row in normalized],
        "hsi_pairs": pairs,
        "interpretation": "Pair rankings are within-corpus investigation leads. HSI scores and the spectral proxy do not measure opportunity quality, novelty, commercial value, or breakthrough probability.",
        "warnings": (["Dense semantic embeddings were unavailable; the comparison used LSA and BM25, both lexical signals."] if semantic_method == "lexical-only-bm25-proxy" else []) + ["External novelty research was not performed.", "Human review is required before an opportunity claim or graph filing."],
    }
