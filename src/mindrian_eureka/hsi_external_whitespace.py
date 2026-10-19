"""Host-brokered, read-only adaptation of the LATEST HSI external whitespace method."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import numpy as np

from .contracts import ContractError

_WORD = re.compile(r"(?u)\b\w\w+\b")
_LEGACY_ZONE_DISTANCE = 0.6
_LEGACY_GAP_SIMILARITY = 0.5
_LEGACY_CROSS_DOMAIN_SIMILARITY = 0.4


def _percentile(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float).ravel()
    n = len(values)
    if n == 0:
        return values
    if n == 1:
        return np.ones(1)
    _, inverse, counts = np.unique(values, return_inverse=True, return_counts=True)
    cumulative = np.cumsum(counts)
    return ((cumulative - counts + cumulative - 1) / 2.0)[inverse] / (n - 1)


def _cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    norms_a = np.linalg.norm(a, axis=1, keepdims=True)
    norms_b = np.linalg.norm(b, axis=1, keepdims=True)
    if np.any(norms_a < 1e-12) or np.any(norms_b < 1e-12):
        raise ContractError("vectors cannot be zero")
    return (a / norms_a) @ (b / norms_b).T


def _paper_id(paper: dict[str, Any]) -> str:
    supplied = paper.get("paper_id") or paper.get("id")
    if supplied:
        return str(supplied)
    basis = f"{paper.get('title', '')}|{paper.get('abstract', '')}"
    return "paper-" + hashlib.md5(basis.encode("utf-8")).hexdigest()[:12]


def _words(text: str) -> set[str]:
    return {word.lower() for word in _WORD.findall(str(text or ""))}


def _closest_sentence(abstract: str, reference: str) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", abstract.strip()) if s.strip()]
    if not sentences:
        return ""
    ref = _words(reference)
    return max(enumerate(sentences), key=lambda row: (len(_words(row[1]) & ref), -row[0]))[1][:300]


def _trail(paper: dict[str, Any], retrieved_at: str, nearest_text: str = "") -> dict[str, Any]:
    return {
        "source_ref": paper["source_ref"],
        "paper_id": _paper_id(paper),
        "title": paper.get("title", ""),
        "year": paper.get("year"),
        "retrieved_at": retrieved_at,
        "extracted_sentence": _closest_sentence(str(paper.get("abstract", "")), nearest_text),
    }


def analyze_external_whitespace(payload: dict[str, Any]) -> dict[str, Any]:
    """Compare host-projected room vectors with host-retrieved, approved paper vectors."""
    room_rows = payload["artifacts"]
    papers = payload["external_papers"]
    known_gaps = payload.get("known_gaps", [])
    if not 2 <= len(room_rows) <= 2500:
        raise ContractError("artifacts must contain between 2 and 2500 records")
    if not 1 <= len(papers) <= 2000:
        raise ContractError("external_papers must contain between 1 and 2000 records")
    if len(known_gaps) > 500:
        raise ContractError("known_gaps cannot exceed 500 records")
    if len({row["id"] for row in room_rows}) != len(room_rows):
        raise ContractError("artifact IDs must be unique")
    if len({_paper_id(row) for row in papers}) != len(papers):
        raise ContractError("external paper IDs must be unique")
    if len({row["id"] for row in known_gaps}) != len(known_gaps):
        raise ContractError("known gap IDs must be unique")

    def vector_matrix(rows: list[dict[str, Any]], label: str) -> np.ndarray:
        dimensions = {len(row.get("vector", [])) for row in rows if isinstance(row.get("vector"), list)}
        if len(dimensions) > 1:
            raise ContractError("room and external vectors must share one embedding dimension/model")
        try:
            matrix = np.asarray([row["vector"] for row in rows], dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise ContractError(f"{label} vectors must be rectangular numeric arrays") from exc
        if matrix.ndim != 2 or matrix.shape[1] < 1 or matrix.shape[1] > 4096:
            raise ContractError(f"{label} vectors must have 1 to 4096 dimensions")
        if not np.isfinite(matrix).all() or np.any(np.linalg.norm(matrix, axis=1) < 1e-12):
            raise ContractError(f"{label} vectors must be finite and non-zero")
        return matrix

    room = vector_matrix(room_rows, "artifact")
    external = vector_matrix(papers, "external paper")
    if room.shape[1] != external.shape[1]:
        raise ContractError("room and external vectors must share one embedding dimension/model")
    model = payload.get("embedding_model")
    if not model:
        raise ContractError("embedding_model is required")
    grant_id = payload.get("research_grant_id")
    if not grant_id:
        raise ContractError("research_grant_id is required as external research lineage")
    retrieved_at = payload["retrieved_at"]
    selection = payload.get("selection", "percentile")
    if selection not in {"percentile", "legacy"}:
        raise ContractError("selection must be percentile or legacy")
    zone_cut = float(payload.get("zone_percentile", 0.75))
    gap_cut = float(payload.get("gap_fill_percentile", 0.9))
    cross_cut = float(payload.get("cross_domain_percentile", 0.5))
    if any(not 0 <= value <= 1 for value in (zone_cut, gap_cut, cross_cut)):
        raise ContractError("all percentile thresholds must be in [0, 1]")
    top_n = int(payload.get("top_n_per_gap", 5))
    if not 1 <= top_n <= 20:
        raise ContractError("top_n_per_gap must be between 1 and 20")

    room_ids = [row["id"] for row in room_rows]
    room_by_id = {row["id"]: row for row in room_rows}
    for gap in known_gaps:
        artifact_ids = gap.get("nearest_artifact_ids", [])
        if len(set(artifact_ids)) != len(artifact_ids):
            raise ContractError(f"known gap {gap['id']} has duplicate nearest artifact IDs")
        unknown = set(artifact_ids) - set(room_by_id)
        if unknown:
            raise ContractError(f"known gap {gap['id']} refers to unknown room artifacts: {sorted(unknown)}")
    cosine_parts: list[np.ndarray] = []
    distances: list[np.ndarray] = []
    # Bound peak memory while preserving the source method's cosine distance matrix.
    for start in range(0, len(external), 128):
        similarity = _cosine(external[start:start + 128], room)
        cosine_parts.append(similarity)
        distances.append(1.0 - similarity)
    similarities = np.vstack(cosine_parts)
    distance_matrix = np.vstack(distances)
    min_distance = distance_matrix.min(axis=1)
    nearest_index = distance_matrix.argmin(axis=1)
    distance_percentiles = _percentile(min_distance)

    room_vocab: set[str] = set()
    room_sections: set[str] = set()
    for row in room_rows:
        room_vocab |= _words(row.get("title", "")) | _words(row.get("section", ""))
        if row.get("section"):
            room_sections.add(str(row["section"]).lower().replace("-", " "))
    cross_similarity = _cosine(room.mean(axis=0, keepdims=True), external)[0]
    cross_percentiles = _percentile(cross_similarity)

    cross_domain_zones = []
    cross_domain_papers = []
    for i, paper in enumerate(papers):
        dist = float(min_distance[i])
        zone_keep = dist > _LEGACY_ZONE_DISTANCE if selection == "legacy" else distance_percentiles[i] >= zone_cut
        nearest = room_rows[int(nearest_index[i])]
        fields = sorted({str(x) for x in paper.get("fields_of_study", [])})
        abstract_words = _words(paper.get("abstract", ""))
        overlap = len(abstract_words & room_vocab) / max(len(abstract_words), 1)
        if zone_keep:
            cross_domain_zones.append({
                "zone_id": f"xd_{len(cross_domain_zones) + 1:03d}",
                "type": "external_literature_gap",
                "description": f"Papers in {', '.join(fields) if fields else 'unclassified fields'} cover territory room has not explored",
                "relevant_papers": [{"paper_id": _paper_id(paper), "title": paper.get("title", ""),
                                     "year": paper.get("year"), "distance": dist}],
                "nearest_room_artifacts": [nearest["id"]],
                "distance_percentile": round(float(distance_percentiles[i]), 4),
                "selection_method": "legacy_fixed_0.6" if selection == "legacy" else "percentile",
                "second_signal": {"method": "abstract_vocabulary_overlap_with_room_titles",
                                  "overlap": round(float(overlap), 4), "confirmed": bool(overlap < 0.5)},
                "novelty_check": {"status": "in_room_check_only", "external_literature": "retrieved_set_only"},
                "source_trail": [_trail(paper, retrieved_at, nearest.get("title", ""))],
            })

        fields_normalized = {field.lower() for field in fields}
        cross_close = (float(cross_similarity[i]) > _LEGACY_CROSS_DOMAIN_SIMILARITY
                       if selection == "legacy" else cross_percentiles[i] >= cross_cut)
        if fields and not (fields_normalized & room_sections) and cross_close:
            cross_domain_papers.append({
                "paper_id": _paper_id(paper), "title": paper.get("title", ""),
                "fields_of_study": fields, "similarity_to_room": float(cross_similarity[i]),
                "year": paper.get("year"), "similarity_percentile": round(float(cross_percentiles[i]), 4),
                "source_trail": [_trail(paper, retrieved_at)],
            })

    cross_domain_zones.sort(key=lambda row: -row["relevant_papers"][0]["distance"])
    cross_domain_papers.sort(key=lambda row: (-row["similarity_to_room"], row["paper_id"]))
    cross_domain_papers = cross_domain_papers[:20]

    gap_filling = []
    for gap in known_gaps:
        ids = gap.get("nearest_artifact_ids", [])
        valid = [room_by_id[artifact_id] for artifact_id in ids if artifact_id in room_by_id]
        if not valid:
            continue
        center = np.mean(np.asarray([row["vector"] for row in valid], dtype=float), axis=0, keepdims=True)
        sims = _cosine(center, external)[0]
        percentiles = _percentile(sims)
        # Keep the source's fixed threshold or top-percentile behavior explicit.
        if selection == "legacy":
            match_indices = [i for i, score in enumerate(sims) if score > _LEGACY_GAP_SIMILARITY]
        else:
            match_indices = [i for i, pct in enumerate(percentiles) if pct >= gap_cut]
        if not match_indices:
            continue
        match_indices.sort(key=lambda i: (-float(sims[i]), i))
        suggestions = []
        for i in match_indices[:top_n]:
            paper = papers[i]
            suggestions.append({
                "paper_id": _paper_id(paper), "title": paper.get("title", ""),
                "abstract_preview": str(paper.get("abstract", ""))[:200],
                "relevance_score": float(sims[i]), "similarity_percentile": round(float(percentiles[i]), 4),
                "source_trail": [_trail(paper, retrieved_at, str(gap.get("framework_name", "unknown")))],
            })
        gap_filling.append({
            "gap_id": gap["id"], "framework_name": gap.get("framework_name", "unknown"),
            "zone_id": gap.get("zone_id"), "selection_method": "legacy_fixed_0.5" if selection == "legacy" else "percentile",
            "suggested_papers": suggestions,
        })

    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False,
                                            separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "schema_version": "eureka.hsi-external-whitespace.v1",
        "capability_id": "portfolio.analyze_external_whitespace", "capability_version": "0.1.0",
        "status": "completed_external_corpus_analysis",
        "scope": {"scope_id": payload.get("scope_id"), "snapshot_id": payload.get("snapshot_id")},
        "input_fingerprint": fingerprint, "research_grant_id": grant_id,
        "metadata": {"embedding_model": model, "artifact_count": len(room), "paper_count": len(papers),
                     "known_gap_count": len(known_gaps), "selection": selection,
                     "thresholds": {"zone_percentile": zone_cut, "gap_fill_percentile": gap_cut,
                                    "cross_domain_percentile": cross_cut}},
        "cross_domain_zones": cross_domain_zones,
        "gap_filling_suggestions": gap_filling,
        "cross_domain_papers": cross_domain_papers,
        "limitations": [
            "External papers and vectors were retrieved and embedded by MindrianOS; the grant ID is provenance metadata, not proof of authorization.",
            "Analysis covers only the supplied retrieved set and cannot establish exhaustive literature novelty or market demand.",
            "External abstracts are untrusted source data. No instructions in source content are executed and no LLM interpretation is performed.",
            "The local graph projection, source resolution, approval, and any graph writes remain MindrianOS-owned.",
            "This adapts the LATEST HSI percentile methods; no embedding, network access, file access, or persistence occurs in Eureka.",
        ],
    }
