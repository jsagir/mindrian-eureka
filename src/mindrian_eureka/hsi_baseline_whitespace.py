"""Read-only LATEST HSI baseline whitespace analysis over host supplied data.

This is an adaptation of LATEST ``compute-whitespace-gaps.py``'s deterministic
PCA fallback and hybrid-percentile gap detector. MindrianOS supplies the
authorized artifact projection, vectors, and baseline corpus; this module
performs no file access, embedding, retrieval, or graph mutation.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Any

import numpy as np

from .contracts import ContractError

_TOKEN_RE = re.compile(r"(?u)\b\w\w+\b")
_STOP = frozenset("a about an and are as at be by for from has have in into is it its of on or that the this to was were with".split())


def _empirical_percentile(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float).ravel()
    if not values.size:
        return values
    if values.size == 1:
        return np.ones(1)
    unique, inverse, counts = np.unique(values, return_inverse=True, return_counts=True)
    cumulative = np.cumsum(counts)
    return ((cumulative - counts + cumulative - 1) / 2.0)[inverse] / (values.size - 1)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    an = np.linalg.norm(a, axis=1, keepdims=True)
    bn = np.linalg.norm(b, axis=1, keepdims=True)
    if np.any(an < 1e-12) or np.any(bn < 1e-12):
        raise ContractError("embedding vectors cannot be zero")
    return (a / an) @ (b / bn).T


def _kde_logdensity(train: np.ndarray, query: np.ndarray, bandwidth: float,
                    exclude_self: bool = False) -> np.ndarray:
    n, dimensions = train.shape
    result = np.empty(query.shape[0])
    for start in range(0, len(query), 128):
        q = query[start:start + 128]
        d2 = ((q[:, None, :] - train[None, :, :]) ** 2).sum(axis=2)
        log_kernel = -0.5 * d2 / (bandwidth * bandwidth)
        if exclude_self:
            indices = np.arange(start, start + len(q))
            log_kernel[np.arange(len(q)), indices] = -np.inf
        maximum = np.max(log_kernel, axis=1, keepdims=True)
        maximum[~np.isfinite(maximum)] = 0.0
        result[start:start + len(q)] = (
            maximum[:, 0] + np.log(np.exp(log_kernel - maximum).sum(axis=1) + 1e-300)
            - math.log(max(n - int(exclude_self), 1)) - dimensions * math.log(bandwidth)
            - 0.5 * dimensions * math.log(2 * math.pi)
        )
    return result


def _nearest_distances(train: np.ndarray, query: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    distances = np.sqrt(((query[:, None, :] - train[None, :, :]) ** 2).sum(axis=2))
    indices = np.argsort(distances, axis=1, kind="stable")[:, :max(1, min(k, len(train)))]
    return np.take_along_axis(distances, indices, axis=1), indices


def _lexical_coverage(query: str, texts: list[str]) -> float | None:
    query_tokens = sorted({word for word in _TOKEN_RE.findall(str(query or "").lower()) if word not in _STOP})
    documents = [{word for word in _TOKEN_RE.findall(str(text or "").lower()) if word not in _STOP} for text in texts]
    documents = [document for document in documents if document]
    if not query_tokens or not documents:
        return None
    total = hit = 0.0
    for word in query_tokens:
        df = sum(word in document for document in documents)
        idf = math.log(1.0 + (len(documents) - df + 0.5) / (df + 0.5))
        total += idf
        if df:
            hit += idf
    return hit / total if total else None


def _gap_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "unknown"
    return f"ws-{slug}-{hashlib.md5(name.encode('utf-8')).hexdigest()[:8]}"


def analyze_baseline_whitespace(payload: dict[str, Any]) -> dict[str, Any]:
    """Rank supplied Brain/framework baselines by room-relative sparsity."""
    artifacts = payload["artifacts"]
    baselines = payload["baseline_frameworks"]
    if len(artifacts) > 2500 or len(baselines) > 1000:
        raise ContractError("analysis limit is 2500 room artifacts and 1000 baseline frameworks")
    if len({row["id"] for row in artifacts}) != len(artifacts):
        raise ContractError("artifact IDs must be unique")
    if len({row["id"] for row in baselines}) != len(baselines):
        raise ContractError("baseline framework IDs must be unique")

    def matrix(rows: list[dict[str, Any]], label: str) -> np.ndarray:
        dimensions = {len(row.get("vector", [])) for row in rows if isinstance(row.get("vector"), list)}
        if len(dimensions) > 1:
            raise ContractError("artifact and baseline vectors must use the same embedding dimension/model")
        try:
            values = np.asarray([row["vector"] for row in rows], dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise ContractError(f"{label} vectors must be rectangular numeric arrays") from exc
        if values.ndim != 2 or not values.shape[1] or values.shape[1] > 4096:
            raise ContractError(f"{label} vectors must share 1 to 4096 dimensions")
        if not np.isfinite(values).all() or np.any(np.linalg.norm(values, axis=1) < 1e-12):
            raise ContractError(f"{label} vectors must contain finite non-zero values")
        return values

    room = matrix(artifacts, "artifact")
    brain = matrix(baselines, "baseline")
    if room.shape[1] != brain.shape[1]:
        raise ContractError("artifact and baseline vectors must use the same embedding dimension/model")
    if len(room) < 3 or not len(brain):
        raise ContractError("at least 3 room artifacts and 1 baseline framework are required")
    model = payload.get("embedding_model")
    if not model:
        raise ContractError("embedding_model is required to identify the shared vector space")

    # The LATEST source falls back to deterministic PCA when UMAP is unavailable.
    combined = np.vstack((room, brain))
    centered = combined - combined.mean(axis=0, keepdims=True)
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    density_dimensions = min(int(payload.get("reducer_dimensions", 15)), len(combined) - 1, room.shape[1])
    if density_dimensions < 1:
        raise ContractError("reducer_dimensions must be positive")
    components = vt[:density_dimensions].copy()
    pivot = np.argmax(np.abs(components), axis=1)
    signs = np.sign(components[np.arange(len(components)), pivot])
    signs[signs == 0] = 1
    reduced = centered @ (components.T * signs)
    room_reduced, brain_reduced = reduced[:len(room)], reduced[len(room):]

    n_room, n_brain = len(room), len(brain)
    bandwidth_setting = payload.get("kde_bandwidth", "scott-scaled")
    factor = n_room ** (-1.0 / (density_dimensions + 4))
    if bandwidth_setting == "scott-scaled":
        bandwidth = factor * max(float(np.mean(np.std(room_reduced, axis=0))), 1e-3)
    elif bandwidth_setting == "scott":
        bandwidth = factor
    else:
        bandwidth = float(bandwidth_setting)
    if not math.isfinite(bandwidth) or bandwidth <= 0:
        raise ContractError("kde_bandwidth must be scott, scott-scaled, or a positive number")
    knn_k = int(payload.get("knn_k", 5))
    if not 1 <= knn_k <= 50:
        raise ContractError("knn_k must be between 1 and 50")
    threshold = float(payload.get("gap_percentile", 0.75))
    if not 0 <= threshold <= 1:
        raise ContractError("gap_percentile must be in [0, 1]")

    density = _kde_logdensity(room_reduced, brain_reduced, bandwidth)
    room_loo = _kde_logdensity(room_reduced, room_reduced, bandwidth, exclude_self=True)
    dists, nearest_indices = _nearest_distances(room_reduced, brain_reduced, min(knn_k, n_room))
    knn_density = 1.0 / (dists[:, -1] + 1e-10)
    max_cosine = _cosine_similarity(brain, room).max(axis=1)
    names = [str(row.get("name") or row.get("label") or row["id"]) for row in baselines]

    components = {
        "kde": 1.0 - _empirical_percentile(density),
        "knn": 1.0 - _empirical_percentile(knn_density),
        "dense": 1.0 - _empirical_percentile(max_cosine),
    }
    lexical = [_lexical_coverage(" ".join(str(b.get(k, "")) for k in ("name", "description", "summary")),
                                 [a.get("text", "") for a in artifacts]) for b in baselines]
    lexical_gap = None
    if all(value is not None for value in lexical):
        lexical_gap = 1.0 - _empirical_percentile(np.asarray(lexical, dtype=float))
        components["lexical"] = lexical_gap
    scores = np.mean(np.vstack(list(components.values())), axis=0)
    percentiles = _empirical_percentile(scores)
    order = sorted(range(n_brain), key=lambda i: (-round(float(scores[i]), 12), names[i], i))
    max_results = int(payload.get("max_results", 100))
    if not 1 <= max_results <= 500:
        raise ContractError("max_results must be between 1 and 500")

    results = []
    for i in order:
        if percentiles[i] < threshold or len(results) >= max_results:
            continue
        framework = baselines[i]
        artifact_refs = []
        for idx in nearest_indices[i, :min(3, n_room)]:
            artifact = artifacts[int(idx)]
            artifact_refs.append({"artifact_id": artifact["id"], "source_ref": artifact.get("source_ref"),
                                  "title": artifact.get("title", ""), "section": artifact.get("section", "")})
        dense_gap = float(components["dense"][i])
        lex_gap = float(lexical_gap[i]) if lexical_gap is not None else None
        results.append({
            "framework_id": framework["id"], "framework_name": names[i],
            "zone_id": _gap_id(names[i]), "gap_score": round(float(scores[i]), 4),
            "gap_percentile": round(float(percentiles[i]), 4),
            "density_score": float(density[i]), "knn_density": float(knn_density[i]),
            "nearest_room_artifacts": artifact_refs,
            "dense_cosine_to_nearest_room_artifact": round(float(max_cosine[i]), 4),
            "lexical_coverage": None if lexical[i] is None else round(float(lexical[i]), 4),
            "signal_percentiles": {key: round(float(values[i]), 4) for key, values in components.items()},
            "density_vs_room_percentile": round(float((room_loo < density[i]).mean()), 4),
            "second_signal": {"method": "dense_vs_lexical_agreement" if lexical_gap is not None else "dense_only",
                              "dense_gap_percentile": round(dense_gap, 4),
                              "lexical_gap_percentile": None if lex_gap is None else round(lex_gap, 4),
                              "confirmed": None if lex_gap is None else bool(dense_gap >= .5 and lex_gap >= .5)},
            "baseline_source_ref": framework.get("source_ref"),
            "selection_method": "hybrid_percentile_pca_fallback",
        })
    fingerprint = hashlib.sha256(__import__("json").dumps(payload, sort_keys=True, ensure_ascii=False,
                                            separators=(",", ":")).encode()).hexdigest()
    return {
        "schema_version": "eureka.hsi-baseline-whitespace.v1",
        "capability_id": "portfolio.analyze_baseline_whitespace",
        "capability_version": "0.1.0", "status": "completed_room_relative_scan",
        "scope": {"scope_id": payload.get("scope_id"), "snapshot_id": payload.get("snapshot_id")},
        "input_fingerprint": fingerprint,
        "method": {"source_method": "LATEST HSI hybrid whitespace gap detector",
                   "reducer": "deterministic_pca_fallback", "embedding_model": model,
                   "baseline_count": n_brain, "artifact_count": n_room,
                   "gap_percentile_threshold": threshold, "kde_bandwidth": bandwidth,
                   "knn_k": knn_k, "ranking_signals": list(components)},
        "gaps": results,
        "limitations": [
            "PCA fallback is used; UMAP is not run by this bounded capability.",
            "Results identify relative sparsity against the supplied baseline only; they do not establish external novelty, demand, or opportunity quality.",
            "MindrianOS must authorize the projection and baseline, resolve source references, and conduct evidence review.",
            "Input vectors and optional text were supplied by the host; Eureka performs no room access, embedding, retrieval, or graph write.",
            "Source-derived algorithm is experimental and remains subject to source/license review and corpus evaluation.",
        ],
    }
