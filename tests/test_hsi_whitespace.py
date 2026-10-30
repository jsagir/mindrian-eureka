from mindrian_eureka.contracts import validate_request, validate_result
from mindrian_eureka.discovery_workflows import discover_hsi_whitespace


def request():
    artifacts = [
        ("a", "Battery storage", [1, 0, 0]),
        ("b", "Clinical imaging", [0, 1, 0]),
        ("c", "Water systems", [0, 0, 1]),
        ("d", "Grid batteries", [.9, .1, 0]),
        ("e", "Medical sensors", [.1, .9, 0]),
    ]
    return {
        "scope_id": "room:hsi-whitespace", "snapshot_id": "snapshot:hsi-42",
        "embedding_model": "shared-model-v2",
        "artifacts": [{"id": i, "title": title, "source_ref": f"mindrian-graph://node/{i}", "vector": vec}
                      for i, title, vec in artifacts],
        "baseline_frameworks": [
            {"id": "f1", "label": "Energy Systems", "vector": [1, 0, 0]},
            {"id": "f2", "label": "Clinical Systems", "vector": [0, 1, 0]},
            {"id": "f3", "label": "Water Systems", "vector": [0, 0, 1]},
            {"id": "f4", "label": "Complex Systems", "vector": [.577, .577, .577]},
        ],
        "hsi_pairs": [
            {"left_id": "a", "right_id": "b", "hsi_score": .9, "lexical_sim": .2},
            {"left_id": "c", "right_id": "d", "hsi_score": .3, "lexical_sim": .8},
        ],
    }


def test_hsi_whitespace_applies_legacy_source_pair_threshold_and_returns_two_signals():
    payload = request()
    validate_request("portfolio.discover_hsi_whitespace", payload)
    result = discover_hsi_whitespace(payload)
    validate_result("portfolio.discover_hsi_whitespace", result)
    assert result["pair_selection"] == "hsi_score > 0.4 (legacy default)"
    assert result["input_counts"]["qualifying_pairs"] == 1
    assert len(result["zones"]) == 1
    assert result["zones"][0]["seed_pair"]["left_id"] == "a"
    assert result["zones"][0]["second_signal"] == {
        "method": "pair_lexical_similarity", "lexical_sim": .2, "confirmed": True
    }


def test_percentile_ranked_pairs_are_preserved_and_small_corpora_use_fixed_cutoffs():
    payload = request()
    payload["hsi_pairs"][1]["hsi_percentile"] = .2
    payload["artifacts"] = payload["artifacts"][:3]
    result = discover_hsi_whitespace(payload)
    assert result["pair_selection"] == "as ranked by compute-hsi (percentile)"
    assert result["input_counts"]["qualifying_pairs"] == 2
    assert result["provenance"]["signal_method"] == "fixed"
    assert all(zone["baseline_density_percentile"] is None for zone in result["zones"])
