"""Reverse-Salient pair ranking with an explicit, replaceable semantic encoder.

The structural signal and reference normalization follow the source analysis of
"Algorithmic Generation of Reverse Salient Solutions". The modern encoder is an
explicit variant, not a claim of bit-for-bit reproduction of its BERT pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class RunCancelled(Exception):
    """Raised when the host/user cancels a running capability job."""


@dataclass(frozen=True)
class Artifact:
    id: str
    title: str
    text: str
    source_ref: str | None = None
    corpus: str = "room"

    @property
    def model_text(self) -> str:
        return f"{self.title}\n\n{self.text}".strip()


@dataclass(frozen=True)
class PairCandidate:
    left: Artifact
    right: Artifact
    structural_similarity: float
    semantic_similarity: float
    signed_difference: float
    disagreement: float
    interpretation: str
    direction: str


class SemanticEncoder(Protocol):
    name: str
    version: str

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Return one finite, non-zero vector per input text."""


def structural_similarity(texts: Sequence[str], *, topics: int = 80, cancel_check=None) -> tuple[np.ndarray, dict]:
    """Reproduce source LSA topic-keyword membership and L1-distance signal.

    Small corpora use the largest valid topic count (a documented robustness
    adaptation); the source's 80-topic setting is retained whenever possible.
    """
    if len(texts) < 2:
        raise ValueError("At least two non-empty artifacts are required")
    vectorizer = TfidfVectorizer(
        stop_words="english", max_features=2000, max_df=0.5, smooth_idf=True
    )
    tfidf = vectorizer.fit_transform(texts)
    terms = vectorizer.get_feature_names_out()
    max_components = min(tfidf.shape[0] - 1, tfidf.shape[1] - 1, topics)
    if max_components < 1:
        raise ValueError("Corpus has too little vocabulary variation for structural scoring")

    svd = TruncatedSVD(
        n_components=max_components,
        algorithm="randomized",
        n_iter=10,
        random_state=256,
    )
    svd.fit(tfidf)
    topic_terms: list[set[str]] = []
    for component in svd.components_:
        top = np.argsort(component)[-7:][::-1]
        topic_terms.append({str(terms[i]) for i in top})

    membership = np.zeros((len(texts), len(topic_terms)), dtype=np.float64)
    for row, text in enumerate(texts):
        if cancel_check and cancel_check():
            raise RunCancelled("Run cancelled during structural profile construction")
        # The reference pipeline counts raw whitespace tokens. Punctuation is
        # intentionally not stripped before membership matching.
        for token in text.split():
            for column, vocabulary in enumerate(topic_terms):
                if token in vocabulary:
                    membership[row, column] += 1.0

    totals = membership.sum(axis=1, keepdims=True)
    empty_rows = np.flatnonzero(totals[:, 0] == 0).tolist()
    # Preserve valid zero rows without NaN; expose them as a warning because their
    # structural profile contains no selected topic terms.
    normalized = np.divide(membership, totals, out=np.zeros_like(membership), where=totals != 0)
    distances = np.zeros((len(texts), len(texts)), dtype=np.float64)
    for i in range(len(texts) - 1):
        if cancel_check and cancel_check():
            raise RunCancelled("Run cancelled during structural pair scoring")
        row = np.abs(normalized[i + 1:] - normalized[i]).sum(axis=1)
        distances[i, i + 1:] = row
        distances[i + 1:, i] = row
    inverted = distances.max() - distances
    spread = float(inverted.max() - inverted.min())
    if spread <= np.finfo(float).eps:
        raise ValueError("Structural similarity has no variation across this corpus")
    similarity = ((inverted - (inverted.max() + inverted.min()) / 2.0) / spread) + 0.5
    return similarity, {
        "method": "tfidf_svd_top7_topic_keyword_membership_l1",
        "requested_topics": topics,
        "actual_topics": max_components,
        "topic_keyword_count": 7,
        "random_state": 256,
        "empty_topic_profile_rows": empty_rows,
        "small_corpus_topic_adaptation": max_components != topics,
    }


def reference_semantic_similarity(
    texts: Sequence[str], embeddings: Sequence[np.ndarray]
) -> tuple[np.ndarray, dict]:
    """Pairwise mean segment cosine, as described for the original BERT signal."""
    if len(texts) != len(embeddings):
        raise ValueError("Need one segment-embedding matrix per artifact")
    n = len(texts)
    matrix = np.zeros((n, n), dtype=np.float64)
    for i, left in enumerate(embeddings):
        if left.ndim != 2 or left.shape[0] == 0:
            raise ValueError(f"Artifact {i} has no semantic segments")
        left = _normalize_rows(left)
        for j in range(i, n):
            right = _normalize_rows(embeddings[j])
            if left.shape[1] != right.shape[1] or right.shape[0] == 0:
                raise ValueError("Semantic segment embedding dimensions do not match")
            score = float((left @ right.T).mean())
            matrix[i, j] = matrix[j, i] = score
    center = float(matrix.mean())
    scale = float(np.max(np.abs(matrix - center)))
    if scale <= np.finfo(float).eps:
        raise ValueError("Semantic similarity has no variation across this corpus")
    normalized = ((matrix - center) / scale) + 0.5
    return normalized, {"normalization": "source_global_mean_max_abs", "center": center, "scale": scale}


def modern_semantic_similarity(embeddings: np.ndarray) -> tuple[np.ndarray, dict]:
    """Cosine similarity over one normalized document vector per artifact."""
    if embeddings.ndim != 2 or embeddings.shape[0] < 2:
        raise ValueError("Need a matrix of at least two document embeddings")
    normalized = _normalize_rows(embeddings)
    cosine = cosine_similarity(normalized)
    center = float(cosine.mean())
    scale = float(np.max(np.abs(cosine - center)))
    if scale <= np.finfo(float).eps:
        raise ValueError("Semantic similarity has no variation across this corpus")
    result = ((cosine - center) / scale) + 0.5
    return result, {"normalization": "global_mean_max_abs", "center": center, "scale": scale}


def rank_pairs(
    artifacts: Sequence[Artifact], structural: np.ndarray, semantic: np.ndarray, *,
    top_k: int = 20, cross_corpus_only: bool = False,
) -> list[PairCandidate]:
    """Rank unique unordered pairs by absolute signal disagreement."""
    if structural.shape != semantic.shape or structural.shape != (len(artifacts), len(artifacts)):
        raise ValueError("Similarity matrices must be square and match the artifact count")
    if top_k < 0:
        raise ValueError("top_k cannot be negative")
    n = len(artifacts)
    upper_i, upper_j = np.triu_indices(n, k=1)
    if cross_corpus_only:
        cross = np.fromiter(
            (artifacts[i].corpus != artifacts[j].corpus for i, j in zip(upper_i, upper_j)),
            dtype=bool, count=len(upper_i),
        )
        upper_i, upper_j = upper_i[cross], upper_j[cross]
    disagreements = np.abs(semantic[upper_i, upper_j] - structural[upper_i, upper_j])
    if len(disagreements) > top_k:
        selected = np.argpartition(disagreements, -top_k)[-top_k:] if top_k else np.array([], dtype=int)
        selected = sorted(selected.tolist(), key=lambda k: (-float(disagreements[k]), artifacts[upper_i[k]].id, artifacts[upper_j[k]].id))
        indices = selected
    else:
        indices = sorted(range(len(disagreements)), key=lambda k: (-float(disagreements[k]), artifacts[upper_i[k]].id, artifacts[upper_j[k]].id))
    candidates: list[PairCandidate] = []
    for pair_index in indices:
        i, j = int(upper_i[pair_index]), int(upper_j[pair_index])
        delta = float(semantic[i, j] - structural[i, j])
        interpretation = (
            "semantic similarity exceeds structural similarity; inspect for related meaning expressed through different topic vocabulary"
            if delta > 0
            else "structural similarity exceeds semantic similarity; inspect for shared topic vocabulary used with different meanings"
        )
        candidates.append(PairCandidate(
            left=artifacts[i], right=artifacts[j],
            structural_similarity=float(structural[i, j]),
            semantic_similarity=float(semantic[i, j]),
            signed_difference=delta,
            disagreement=abs(delta),
            interpretation=interpretation,
            direction="structural_transfer" if delta > 0 else "semantic_implementation",
        ))
    return candidates


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    array = np.asarray(matrix, dtype=np.float64)
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    if np.any(norms <= np.finfo(float).eps) or not np.isfinite(array).all():
        raise ValueError("Semantic embeddings must be finite and non-zero")
    return array / norms
