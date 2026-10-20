"""Regression tests for three wrong-number defects. Real engines, no mocks."""

from __future__ import annotations

import math
import unittest

import numpy as np
import pytest

from mindrian_eureka.decision_patterns.algorithm import analyze_sequence, fit_model
from mindrian_eureka.discovery_workflows import portfolio_coverage


def _coverage(artifact_categories: list[list[str]], taxonomy_ids: list[str]) -> dict:
    return portfolio_coverage({
        "artifacts": [{"id": f"a{i}", "category_ids": ids} for i, ids in enumerate(artifact_categories)],
        "taxonomy": [{"id": cid, "label": cid.upper()} for cid in taxonomy_ids],
    })["coverage"]


class PortfolioCoverageCounts(unittest.TestCase):
    """W1: unrepresented_categories must count categories with no artifact."""

    def test_one_of_three_represented(self):
        cov = _coverage([["x"], ["x"]], ["x", "y", "z"])
        self.assertEqual(cov["represented_categories"], 1)
        self.assertEqual(cov["unrepresented_categories"], 2)
        self.assertAlmostEqual(cov["represented_fraction"], 1 / 3)

    def test_all_covered(self):
        cov = _coverage([["x"], ["y"], ["z", "x"]], ["x", "y", "z"])
        self.assertEqual(cov["represented_categories"], 3)
        self.assertEqual(cov["unrepresented_categories"], 0)
        self.assertEqual(cov["represented_fraction"], 1.0)

    def test_none_covered(self):
        cov = _coverage([[], []], ["x", "y", "z"])
        self.assertEqual(cov["represented_categories"], 0)
        self.assertEqual(cov["unrepresented_categories"], 3)
        self.assertEqual(cov["represented_fraction"], 0.0)

    def test_counts_always_sum_to_taxonomy_size(self):
        cov = _coverage([["a"], ["b"], ["b"]], ["a", "b", "c", "d", "e"])
        self.assertEqual(cov["represented_categories"], 2)
        self.assertEqual(cov["unrepresented_categories"], 3)
        self.assertEqual(cov["represented_categories"] + cov["unrepresented_categories"], 5)


# --- W2: fit_model must return valid, normalised, finite parameters -----------

def _hmm_seed(emissions):
    return {
        "id": "seed",
        "label": "seed",
        "initial_distribution": [0.25] * 4,
        "transition_matrix": [[0.25] * 4 for _ in range(4)],
        "emission_probabilities": emissions,
    }


SPREAD_SEED = _hmm_seed([[0.9, 0.1, 0.1, 0.1], [0.1, 0.9, 0.1, 0.1], [0.1, 0.1, 0.9, 0.1], [0.1, 0.1, 0.1, 0.9]])
UNIFORM_SEED = _hmm_seed([[0.5] * 4 for _ in range(4)])
FEATURES = ("complex_features", "multidirectional_causation", "holistic_view", "creative_synthesis")


def _sequences():
    rng = np.random.default_rng(0)
    out = []
    for name in ("a", "b"):
        matrix = rng.random((16, 4)) < [0.8, 0.8, 0.1, 0.1]
        out.append({"observations": [
            {"step_id": f"{name}-{i}", "features": {f: bool(matrix[i, j]) for j, f in enumerate(FEATURES)}}
            for i in range(16)
        ]})
    return out


def _fit_request(seed, iterations, tolerance=None):
    request = {
        "training_mode": "exploratory_unlabeled_baum_welch",
        "seed_model": seed,
        "sequences": _sequences(),
        "max_iterations": iterations,
    }
    if tolerance is not None:
        request["tolerance"] = tolerance
    return request


def _assert_valid_model(model):
    for row in model["transition_matrix"]:
        assert all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in row)
        assert sum(row) == pytest.approx(1.0, abs=1e-9)
    assert sum(model["initial_distribution"]) == pytest.approx(1.0, abs=1e-9)
    for row in model["emission_probabilities"]:
        assert all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in row)


@pytest.fixture(scope="module")
def _hmm_engine():
    pytest.importorskip("pomegranate")


@pytest.mark.parametrize("seed", [UNIFORM_SEED, SPREAD_SEED], ids=["uniform", "spread"])
@pytest.mark.parametrize("iterations", [1, 5, 10, 20])
@pytest.mark.parametrize("tolerance", [0, None], ids=["tol0", "default-tol"])
def test_fit_rows_sum_to_one_and_never_nan(_hmm_engine, seed, iterations, tolerance):
    try:
        result = fit_model(_fit_request(seed, iterations, tolerance))
    except ValueError as error:
        # An explicit refusal is allowed, but only for a non-finite fit.
        assert "non-finite" in str(error)
        return
    _assert_valid_model(result["model"])


def test_fit_that_collapses_a_state_is_refused_not_returned_as_nan(_hmm_engine):
    # With this seed pomegranate drives one state to zero mass by iteration 8
    # and its 0/0 update turns every parameter into NaN.
    with pytest.raises(ValueError, match="non-finite"):
        fit_model(_fit_request(SPREAD_SEED, 10, 0))


def test_short_fit_keeps_learned_ends_out_of_the_rows(_hmm_engine):
    # Raw pomegranate rows sum to about 0.68..1.0 after one iteration on this
    # fixture because the learned end probability takes the rest.
    result = fit_model(_fit_request(SPREAD_SEED, 1))
    _assert_valid_model(result["model"])
    assert result["status"] == "exploratory_unvalidated_fit"


def test_fitted_model_round_trips_into_analyze_sequence(_hmm_engine):
    fitted = fit_model(_fit_request(SPREAD_SEED, 5))["model"]
    observations = _sequences()[0]["observations"]
    result = analyze_sequence({"observations": observations, "models": [fitted, SPREAD_SEED]})
    assert {item["model_id"] for item in result["model_results"]} == {fitted["id"], "seed"}
    for item in result["model_results"]:
        assert math.isfinite(item["log_likelihood"])


if __name__ == "__main__":
    unittest.main()
