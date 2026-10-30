"""Reverse-Salient pair ranking with an explicit, replaceable semantic encoder.

The structural signal and reference normalization follow the source analysis of
"Algorithmic Generation of Reverse Salient Solutions". The modern encoder is an
explicit variant, not a claim of bit-for-bit reproduction of its BERT pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
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
    method_signals: dict | None = None


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
        # Stable descending order: equal values keep the lower term index first,
        # as in the original source (sorted, reverse, first 7).
        top = [index for index, _ in sorted(enumerate(component), key=lambda pair: pair[1], reverse=True)[:7]]
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


_RS_STOPWORDS = set((
    "a about above after again all also am an and any are as at be because been before being below between both but by can could did do does doing down during each few for from further had has having he her here hers him his how i if in into is it its just may me more most my no nor not of off on once only or other our out over own same she should so some such than that the their them then there these they this those through to too under until up very was we were what when where which while who whom why will with would you your"
).split())
_RS_TOKEN_RE = re.compile(r"[^\W_]{2,}", re.UNICODE)


def _rs_tokens(text: str) -> list[str]:
    return [token for token in _RS_TOKEN_RE.findall((text or "").lower()) if token not in _RS_STOPWORDS]


def _capped_vocabulary(df: dict[str, int], max_features: int) -> list[tuple[str, int]]:
    """Select the BM25 vocabulary under a cap and return (term, df) pairs.

    At or under the cap every term is kept. Over the cap, terms with df == 1
    go first (they cannot link 2 documents), then the most common terms; the
    rarest shared terms are kept. The result is ordered by (-df, term), the
    same column order as before, so floating-point sums do not move when the
    kept set is unchanged.
    """
    if len(df) <= max_features:
        kept = list(df)
    else:
        kept = [term for term, count in df.items() if count >= 2]
        if len(kept) > max_features:
            kept = sorted(kept, key=lambda t: (df[t], t))[:max_features]
    return [(t, df[t]) for t in sorted(kept, key=lambda t: (-df[t], t))]


def _bm25_cosine(texts: Sequence[str], *, k1: float = 1.5, b: float = 0.75, max_features: int = 5000) -> np.ndarray:
    """LATEST RS 2026 deterministic BM25-weighted document cosine signal.

    Over the vocabulary cap, df == 1 terms go first, then the most common
    terms. The rarest shared terms are kept, whatever their spelling.
    """
    docs = [_rs_tokens(text) for text in texts]
    n = len(docs)
    df: dict[str, int] = {}
    for doc in docs:
        for term in set(doc):
            df[term] = df.get(term, 0) + 1
    ranked = _capped_vocabulary(df, max_features)
    index = {term: i for i, (term, _) in enumerate(ranked)}
    if not index:
        return np.eye(n, dtype=np.float64)
    idf = np.array([np.log(1.0 + (n - count + 0.5) / (count + 0.5)) for _, count in ranked])
    lengths = np.array([len(doc) for doc in docs], dtype=np.float64)
    avg_length = float(lengths.mean()) or 1.0
    weighted = np.zeros((n, len(index)), dtype=np.float64)
    for row, doc in enumerate(docs):
        counts: dict[int, int] = {}
        for term in doc:
            if term in index:
                col = index[term]
                counts[col] = counts.get(col, 0) + 1
        for col, tf in counts.items():
            denom = tf + k1 * (1.0 - b + b * lengths[row] / avg_length)
            weighted[row, col] = idf[col] * tf * (k1 + 1.0) / denom
    norms = np.linalg.norm(weighted, axis=1)
    norms[norms == 0.0] = 1.0
    weighted /= norms[:, None]
    return np.clip(weighted @ weighted.T, 0.0, 1.0)


def _zscore_pairs(matrix: np.ndarray) -> np.ndarray:
    values = np.asarray(matrix, dtype=np.float64)
    if len(values) < 2:
        return np.zeros_like(values)
    upper = values[np.triu_indices(len(values), k=1)]
    deviation = float(upper.std())
    if deviation < 1e-12:
        return np.zeros_like(values)
    return (values - float(upper.mean())) / deviation


def _percentile_ranks(matrix: np.ndarray, eligible: np.ndarray | None = None) -> np.ndarray:
    values = np.nan_to_num(np.asarray(matrix, dtype=np.float64))
    n = len(values)
    out = np.zeros((n, n), dtype=np.float64)
    if n < 2:
        return out
    i, j = np.triu_indices(n, k=1)
    if eligible is not None:
        mask = eligible[i, j]
        i, j = i[mask], j[mask]
    selected = values[i, j]
    if not len(selected):
        return out
    if len(selected) == 1:
        out[i, j] = 1.0
        return out + out.T
    order = np.argsort(selected, kind="mergesort")
    sorted_values = selected[order]
    unique, inverse, counts = np.unique(sorted_values, return_inverse=True, return_counts=True)
    cumulative = np.cumsum(counts)
    average_rank = (cumulative - counts + cumulative - 1) / 2.0
    ranks = np.empty(len(selected), dtype=np.float64)
    ranks[order] = average_rank[inverse]
    out[i, j] = ranks / (len(selected) - 1)
    return out + out.T


def rank_pairs_hybrid_2026(
    artifacts: Sequence[Artifact], structural: np.ndarray, semantic: np.ndarray, *,
    top_k: int = 20, cross_corpus_only: bool = False, lex_weight: float = 0.5,
    min_percentile: float = 0.90,
) -> list[PairCandidate]:
    """Latest RS hybrid ranker: LSA/BM25 structure versus dense signal, z-gap percentile."""
    if not 0.0 <= lex_weight <= 1.0:
        raise ValueError("lex_weight must be between 0 and 1")
    if not 0.0 <= min_percentile <= 1.0:
        raise ValueError("min_percentile must be between 0 and 1")
    n = len(artifacts)
    if structural.shape != (n, n) or semantic.shape != (n, n):
        raise ValueError("Similarity matrices must be square and match the artifact count")
    texts = [artifact.model_text for artifact in artifacts]
    lexical = _bm25_cosine(texts)
    structural_z = (1.0 - lex_weight) * _zscore_pairs(structural) + lex_weight * _zscore_pairs(lexical)
    dense_z = _zscore_pairs(semantic)
    signed_gap = dense_z - structural_z
    abs_gap = np.abs(signed_gap)
    eligible = np.ones((n, n), dtype=bool)
    if cross_corpus_only:
        eligible = np.array([[a.corpus != b.corpus for b in artifacts] for a in artifacts], dtype=bool)
    i, j = np.triu_indices(n, k=1)
    if int(eligible[i, j].sum()) < 10:
        return []
    percentiles = _percentile_ranks(abs_gap, eligible)
    keep = eligible[i, j] & (percentiles[i, j] >= min_percentile)
    i, j = i[keep], j[keep]
    order = sorted(range(len(i)), key=lambda k: (-float(abs_gap[i[k], j[k]]), artifacts[i[k]].id, artifacts[j[k]].id))[:top_k]
    output: list[PairCandidate] = []
    for pos in order:
        left, right = int(i[pos]), int(j[pos])
        delta = float(signed_gap[left, right])
        direction = "structural_transfer" if delta > 0 else "semantic_implementation"
        output.append(PairCandidate(
            left=artifacts[left], right=artifacts[right],
            structural_similarity=float(structural[left, right]),
            semantic_similarity=float(semantic[left, right]), signed_difference=delta,
            disagreement=abs(delta),
            interpretation=("dense semantic signal exceeds lexical structural signal; inspect for related meaning expressed through different topic vocabulary" if delta > 0 else "lexical structural signal exceeds dense semantic signal; inspect for shared vocabulary used with different meanings"),
            direction=direction,
            method_signals={"scoring": "hybrid_2026", "bm25_similarity": float(lexical[left, right]), "structural_z": float(structural_z[left, right]), "dense_z": float(dense_z[left, right]), "hybrid_signed_gap": delta, "gap_percentile": float(percentiles[left, right])},
        ))
    return output


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    array = np.asarray(matrix, dtype=np.float64)
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    if np.any(norms <= np.finfo(float).eps) or not np.isfinite(array).all():
        raise ValueError("Semantic embeddings must be finite and non-zero")
    return array / norms
