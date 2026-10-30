"""Tests for the equal-spread fusion of the LSA and BM25 lexical legs.

Synthetic matrices only, not a finding. The raw average 0.5 * (lsa + bm25) gives
the vote to the leg with the larger spread on a corpus. The fusion gives each leg
half the vote. Test 1 runs the same assertion on the fused matrix (passes) and on
the raw average (fails), so it proves the defect and the fix together.
"""

from __future__ import annotations

import numpy as np
import pytest
from mindrian_eureka.hsi_engine import run_hsi
from mindrian_eureka.hsi_reference import fuse_lexical_hybrid

N_DOCS = 16
SEED = 2026
TOLERANCE = 0.05

# Six short records with host-supplied dense vectors, so no model is needed.
FIXTURE_TEXTS = {
    "a1": "battery storage grid energy resilience",
    "a2": "clinical imaging diagnostic medical sensors",
    "a3": "agricultural irrigation water crop yield",
    "a4": "electrochemical battery storage power system",
    "a5": "medical imaging sensors diagnostic equipment",
    "a6": "battery storage hospital sensors power outage",
}
FIXTURE_VECTORS = {
    "a1": [1, 0, 0],
    "a2": [0, 1, 0],
    "a3": [0, 0, 1],
    "a4": [0.9, 0.1, 0],
    "a5": [0.1, 0.9, 0],
    "a6": [0.5, 0.5, 0.7],
}


def _pairs(matrix: np.ndarray) -> np.ndarray:
    """The upper triangle (k=1) of a square matrix as a flat vector."""
    iu, ju = np.triu_indices(matrix.shape[0], k=1)
    return np.asarray(matrix, dtype=float)[iu, ju]


def _symmetric_unit(rng: np.random.Generator, n: int) -> np.ndarray:
    """A symmetric matrix with values in [0, 1] and a diagonal of 1.0."""
    u = rng.random((n, n))
    u = 0.5 * (u + u.T)
    np.fill_diagonal(u, 1.0)
    return u


def asymmetric_legs(seed: int = SEED, n: int = N_DOCS) -> tuple[np.ndarray, np.ndarray]:
    """Leg A with about 2x the pair spread of leg B. Both in [0, 1], diagonal 1.0."""
    rng = np.random.default_rng(seed)
    lsa = _symmetric_unit(rng, n)
    bm25 = 0.5 * _symmetric_unit(rng, n)
    np.fill_diagonal(bm25, 1.0)
    return lsa, bm25


def equal_spread_legs(seed: int = SEED, n: int = N_DOCS) -> tuple[np.ndarray, np.ndarray]:
    """Two legs with the same pair spread: leg B is rescaled to the spread of leg A."""
    rng = np.random.default_rng(seed)
    lsa = 0.5 + 0.8 * (_symmetric_unit(rng, n) - 0.5)
    bm25 = 0.4 + 0.8 * (_symmetric_unit(rng, n) - 0.5)
    pairs_l, pairs_b = _pairs(lsa), _pairs(bm25)
    mean_b = pairs_b.mean()
    bm25 = np.clip(mean_b + (bm25 - mean_b) * (pairs_l.std() / pairs_b.std()), 0.0, 1.0)
    np.fill_diagonal(lsa, 1.0)
    np.fill_diagonal(bm25, 1.0)
    return lsa, bm25


def raw_average(lsa: np.ndarray, bm25: np.ndarray) -> np.ndarray:
    """The fusion rule that this change replaces."""
    return 0.5 * (lsa + bm25)


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.corrcoef(a, b)[0, 1])


def _leg_correlations(fused: np.ndarray, lsa: np.ndarray, bm25: np.ndarray) -> tuple[float, float]:
    """Pearson correlation of the fused pairs with each leg's pairs."""
    f = _pairs(fused)
    return _pearson(f, _pairs(lsa)), _pearson(f, _pairs(bm25))


def _leg_variance_shares(
    fused: np.ndarray, lsa: np.ndarray, bm25: np.ndarray
) -> tuple[float, float]:
    """Fit fused = a * lsa + b * bm25 + c on the pairs. Return each leg's share of var(fused)."""
    f, pairs_l, pairs_b = _pairs(fused), _pairs(lsa), _pairs(bm25)
    design = np.column_stack([pairs_l, pairs_b, np.ones_like(pairs_l)])
    coef = np.linalg.lstsq(design, f, rcond=None)[0]
    var_f = float(f.var())
    return float((coef[0] * pairs_l).var() / var_f), float((coef[1] * pairs_b).var() / var_f)


def test_asymmetric_spread_fused_gives_each_leg_half_the_vote_and_raw_average_does_not() -> None:
    lsa, bm25 = asymmetric_legs()
    ratio = _pairs(lsa).std() / _pairs(bm25).std()
    assert 1.5 <= ratio <= 2.5  # the design: one leg with about 2x the spread (measured 1.79)

    fused = fuse_lexical_hybrid(lsa, bm25)
    corr_l, corr_b = _leg_correlations(fused, lsa, bm25)
    share_l, share_b = _leg_variance_shares(fused, lsa, bm25)
    assert abs(corr_l - corr_b) <= TOLERANCE
    assert abs(share_l - share_b) <= TOLERANCE

    # The defect: the same two assertions fail on the raw average (measured gaps 0.37 and 0.51).
    raw = raw_average(lsa, bm25)
    raw_corr_l, raw_corr_b = _leg_correlations(raw, lsa, bm25)
    raw_share_l, raw_share_b = _leg_variance_shares(raw, lsa, bm25)
    assert abs(raw_corr_l - raw_corr_b) > TOLERANCE
    assert abs(raw_share_l - raw_share_b) > TOLERANCE
    assert raw_corr_l > raw_corr_b  # the leg with the larger spread takes the vote


def test_equal_spread_fused_matches_the_raw_average() -> None:
    lsa, bm25 = equal_spread_legs()
    assert abs(_pairs(lsa).std() - _pairs(bm25).std()) < 1e-9
    fused = fuse_lexical_hybrid(lsa, bm25)
    assert np.abs(fused - raw_average(lsa, bm25)).max() < 0.02  # measured 1.1e-16


def test_zero_spread_guard_returns_the_raw_average_exactly() -> None:
    _lsa, bm25 = asymmetric_legs()
    constant_a = np.full((N_DOCS, N_DOCS), 0.3)
    constant_b = np.full((N_DOCS, N_DOCS), 0.6)
    np.fill_diagonal(constant_a, 1.0)
    np.fill_diagonal(constant_b, 1.0)
    both = fuse_lexical_hybrid(constant_a, constant_b)
    assert np.array_equal(both, raw_average(constant_a, constant_b))
    one_leg = fuse_lexical_hybrid(constant_a, bm25)
    assert np.array_equal(one_leg, raw_average(constant_a, bm25))
    two_docs = np.array([[1.0, 0.2], [0.2, 1.0]])
    other = 0.5 * two_docs + 0.5
    assert np.array_equal(fuse_lexical_hybrid(two_docs, other), raw_average(two_docs, other))


def test_fused_matrix_is_bounded_symmetric_unit_diagonal_and_deterministic() -> None:
    lsa, bm25 = asymmetric_legs()
    fused = fuse_lexical_hybrid(lsa, bm25)
    assert fused.dtype == np.float64
    assert fused.shape == (N_DOCS, N_DOCS)
    assert fused.min() >= 0.0
    assert fused.max() <= 1.0
    assert np.array_equal(np.diag(fused), np.ones(N_DOCS))
    assert np.array_equal(fused, fused.T)
    assert np.array_equal(fused, fuse_lexical_hybrid(lsa, bm25))
    assert not np.allclose(fused, raw_average(lsa, bm25))  # the fusion changes the matrix here


def _hsi_document(**overrides: object) -> dict[str, object]:
    artifacts = [
        {"id": key, "source_ref": f"mindrian-graph://node/{key}", "title": key, "text": text}
        for key, text in FIXTURE_TEXTS.items()
    ]
    document: dict[str, object] = {
        "artifacts": artifacts,
        "dense_vectors": FIXTURE_VECTORS,
        "top_k": 20,
        "ranking": "percentile",
        "min_percentile": 0.0,
    }
    document.update(overrides)
    return document


@pytest.mark.parametrize(
    ("lexical", "expected"),
    [("hybrid", "equal_spread_average"), ("lsa", "none"), ("bm25", "none")],
)
def test_run_hsi_reports_the_lexical_fusion(lexical: str, expected: str) -> None:
    result = run_hsi(_hsi_document(lexical=lexical))
    assert result["metadata"]["lexical_method"] == lexical
    assert result["metadata"]["lexical_fusion"] == expected


def test_run_hsi_degraded_proxy_reports_no_fusion(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MINDRIAN_EUREKA_HSI_MODEL_PATH", raising=False)
    document = _hsi_document()
    del document["dense_vectors"]
    result = run_hsi(document)
    assert result["status"] == "completed_degraded_lexical_only"
    assert result["metadata"]["lexical_method"] == "hybrid"
    assert result["metadata"]["lexical_fusion"] == "none"
