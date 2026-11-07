"""Regression tests for three wrong-number defects. Real engines, no mocks."""

from __future__ import annotations

import math
import unittest

import numpy as np
import pytest

from mindrian_eureka import opportunity_discovery
from mindrian_eureka.contracts import validate_result
from mindrian_eureka.decision_patterns.algorithm import analyze_sequence, fit_model
from mindrian_eureka.discovery_workflows import portfolio_coverage
from mindrian_eureka.encoder_spec import custom_spec
from mindrian_eureka.hsi_engine import run_hsi
from mindrian_eureka.opportunity_pairs.cache import EmbeddingCache
from mindrian_eureka.opportunity_pairs.runner import run_document


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


# --- W3: the same label name must not hide opposite polarity ------------------
#
# RS:  structural_transfer = semantic > structural (same meaning, different words)
# HSI: structural_transfer = LSA > semantic        (shared words, different meaning)
# The enum values stay. Each engine now carries a plain-language meaning next to
# the label. These tests run the REAL engines offline. The dense semantic
# vectors are supplied the way a host supplies them: HSI takes `dense_vectors`,
# RS reads them from its own embedding cache, so no model download is needed.

FIXTURE_TEXTS = {
    "a1": "battery storage grid energy resilience",
    "a2": "clinical imaging diagnostic medical sensors",
    "a3": "agricultural irrigation water crop yield",
    "a4": "electrochemical battery storage power system",
    "a5": "medical imaging sensors diagnostic equipment",
    "a6": "battery storage hospital sensors power outage",
}
FIXTURE_VECTORS = {
    "a1": [1, 0, 0], "a2": [0, 1, 0], "a3": [0, 0, 1],
    "a4": [0.9, 0.1, 0], "a5": [0.1, 0.9, 0], "a6": [0.5, 0.5, 0.7],
}
ENCODER, MODEL_PATH, RS_METHOD = "sentence-transformers", "fixture", "sentence-transformer-chunk-mean-v1"
RS_MEANING = {"structural_transfer": "same meaning in different words", "semantic_implementation": "same words with different meaning"}
HSI_MEANING_WORDS = {"structural_transfer": "shared words with different meaning", "semantic_implementation": "same meaning in different words"}


def _artifacts():
    return [{"id": key, "source_ref": f"mindrian-graph://node/{key}", "title": key, "text": text} for key, text in FIXTURE_TEXTS.items()]


def _seed_rs_cache(path):
    cache = EmbeddingCache(path)
    for key, text in FIXTURE_TEXTS.items():
        # RS embeds "<title>\n\n<text>"; the fixture title equals the id.
        # The runner keys the cache by the full encoder identity of the bare-folder spec.
        cache_key = EmbeddingCache.key(
            f"{key}\n\n{text}", encoder=ENCODER, model=MODEL_PATH, revision=None,
            method_version=RS_METHOD, identity=custom_spec(MODEL_PATH).identity(),
        )
        cache.put(cache_key, np.asarray([FIXTURE_VECTORS[key]], dtype=float))


def _run_rs(tmp_path, scoring):
    _seed_rs_cache(tmp_path / "embeddings.sqlite3")
    return run_document(
        {"artifacts": _artifacts(), "scoring": scoring, "mode": "local"},
        encoder_name=ENCODER, model_path=MODEL_PATH, top_k=20, cache_path=tmp_path / "embeddings.sqlite3",
    )


def _run_hsi():
    return run_hsi({"artifacts": _artifacts(), "dense_vectors": FIXTURE_VECTORS, "top_k": 20, "ranking": "percentile", "min_percentile": 0.0})


def test_hsi_surprise_type_meaning_matches_actual_polarity():
    result = _run_hsi()
    seen = set()
    for pair in result["hsi_pairs"]:
        if abs(pair["lsa_sim"] - pair["semantic_sim"]) < 1e-3:
            continue  # rounded tie: the label is not meaningful
        label = pair["surprise_type"]
        seen.add(label)
        lsa_higher = pair["lsa_sim"] > pair["semantic_sim"]
        assert (label == "structural_transfer") == lsa_higher
        assert pair["surprise_type_meaning"].startswith(HSI_MEANING_WORDS[label])
        if lsa_higher:
            assert "LSA similarity exceeds semantic similarity" in pair["surprise_type_meaning"]
        else:
            assert "semantic similarity exceeds LSA similarity" in pair["surprise_type_meaning"]
    assert seen == {"structural_transfer", "semantic_implementation"}  # fixture covers both polarities


def test_rs_direction_meaning_matches_actual_polarity_legacy_scoring(tmp_path):
    result = _run_rs(tmp_path, "legacy")
    seen = set()
    for output in result["outputs"]:
        payload = output["payload"]
        semantic_higher = payload["semantic_similarity"] > payload["structural_similarity"]
        assert (payload["direction"] == "structural_transfer") == semantic_higher
        assert payload["direction_meaning"] == RS_MEANING[payload["direction"]]
        seen.add(payload["direction"])
    assert seen == {"structural_transfer", "semantic_implementation"}


def test_rs_direction_meaning_matches_label_with_hybrid_scoring(tmp_path):
    result = _run_rs(tmp_path, "hybrid_2026")
    assert result["outputs"], "fixture must pass the hybrid percentile gate"
    for output in result["outputs"]:
        payload = output["payload"]
        assert (payload["direction"] == "structural_transfer") == (payload["signed_difference"] > 0)
        assert payload["direction_meaning"] == RS_MEANING[payload["direction"]]


def test_combined_signal_carries_both_meanings_and_disambiguates_equal_labels(tmp_path):
    _seed_rs_cache(tmp_path / "embeddings.sqlite3")
    request = {
        "objective": "polarity check", "scope_id": "room:polarity", "snapshot_id": "snap-polarity",
        "artifacts": _artifacts(), "dense_vectors": FIXTURE_VECTORS, "mode": "local",
        "scoring": "legacy", "top_k": 20, "encoder": ENCODER, "model_path": MODEL_PATH,
    }
    result = opportunity_discovery.run_signal_synthesis(request, data_dir=tmp_path, job_id="polarity")
    validate_result("opportunity.synthesize_discovery_signals", result)
    same_name_opposite_meaning = 0
    for output in result["outputs"]:
        signals = output["payload"]["signals"]
        rs, hsi = signals["rs"], signals["hsi"]
        if rs:
            assert rs["direction_meaning"] == RS_MEANING[rs["direction"]]
        if hsi:
            assert hsi["surprise_type_meaning"].startswith(HSI_MEANING_WORDS[hsi["surprise_type"]])
        if rs and hsi and rs["direction"] == hsi["surprise_type"]:
            # Same label name on both engines: the text must tell the reader the polarity differs.
            if rs["direction_meaning"] != hsi["surprise_type_meaning"].split(" (")[0]:
                same_name_opposite_meaning += 1
    assert same_name_opposite_meaning >= 1, "fixture must contain a pair that shows the label collision"


if __name__ == "__main__":
    unittest.main()
