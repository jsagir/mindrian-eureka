import numpy as np

from mindrian_eureka.analogy_fitness import _rank_candidates, assess_analogy_fitness
from mindrian_eureka.analogy_whitespace import analyze
from mindrian_eureka.contracts import validate_request, validate_result
from mindrian_eureka.discovery_workflows import retrieve_mechanisms


def _structure(prefix):
    return {
        "state_change": f"{prefix} state change",
        "action": f"{prefix} action",
        "parts": f"{prefix} parts",
        "phenomenon": f"{prefix} phenomenon",
        "input": f"{prefix} input",
        "real_effect": f"{prefix} real effect",
        "effect": f"{prefix} effect",
    }


def _group(group_id, prefix):
    return {
        "id": group_id, "source_ref": f"mindrian-graph://node/{group_id}",
        "description": f"{prefix} system mechanism", "structure": _structure(prefix),
        "evidence_refs": {key: [f"claim:{group_id}:{key}"] for key in _structure(prefix)},
    }


def test_analogy_transfer_whitespace_echoes_host_scope_and_snapshot():
    request = {
        "scope_id": "room:analogy", "snapshot_id": "mos-snapshot-ana-1", "mode": "fixed",
        "artifacts": [
            {"id": "a", "title": "Source", "section": "one", "vector": [1, 0, 0]},
            {"id": "b", "title": "Target", "section": "two", "vector": [0, 1, 0]},
            {"id": "c", "title": "Other", "section": "three", "vector": [0, 0, 1]},
        ],
        "baselines": [{"id": "framework-1", "name": "Framework", "vector": [1, 1, 0]}],
        "analogy_edges": [{"source_id": "a", "target_id": "b", "analogy_distance": "cross-domain"}],
    }
    validate_request("analogy.discover_transfer_whitespace", request)
    result = analyze(request)
    validate_result("analogy.discover_transfer_whitespace", result)
    assert result["scope_id"] == request["scope_id"]
    assert result["snapshot_id"] == request["snapshot_id"]


def test_sap_phire_fitness_echoes_host_snapshot(monkeypatch):
    monkeypatch.setenv("MINDRIAN_EUREKA_ANALOGY_MODEL_PATH", "/local/test-model")

    class FakeEncoder:
        def __init__(self, *_args, **_kwargs):
            pass
        def encode(self, texts):
            return np.ones((len(texts), 4), dtype=float)

    monkeypatch.setattr("mindrian_eureka.analogy_fitness.SentenceTransformerEncoder", FakeEncoder)
    request = {
        "scope_id": "room:analogy", "snapshot_id": "mos-snapshot-fit-2",
        "target": _group("target", "target"), "candidates": [_group("source", "source")],
    }
    validate_request("analogy.assess_structural_fitness", request)
    result = assess_analogy_fitness(request)
    validate_result("analogy.assess_structural_fitness", result)
    assert result["scope_id"] == request["scope_id"]
    assert result["snapshot_id"] == request["snapshot_id"]
    candidate = result["candidates"][0]
    assert candidate["fused_fitness"] == 1.0
    assert candidate["rank"] == 1
    assert result["provenance"]["threshold_mode"] == "fixed_small_pool"
    assert result["provenance"]["scoring_parameters"]["text_weight"] == 0.5


def test_sap_phire_ranking_lifts_flagged_restatement_below_best_clear_candidate():
    rows = [
        {"candidate_id": "restatement", "band": "behavioral", "fused_fitness": 0.99, "restatement_warning": True},
        {"candidate_id": "transfer", "band": "surface", "fused_fitness": 0.45, "restatement_warning": False},
    ]
    ranked = _rank_candidates(rows)
    assert [row["candidate_id"] for row in ranked] == ["transfer", "restatement"]
    assert [row["rank"] for row in ranked] == [1, 2]


def test_mechanism_retrieval_echoes_host_scope_and_snapshot():
    request = {
        "problem": "Improve heat transfer in compact batteries",
        "scope_id": "room:mechanisms", "snapshot_id": "mos-snapshot-mech-3",
        "mechanisms": [{"id": "m1", "domain": "thermal engineering", "mechanism": "Heat pipes transfer heat through evaporation and condensation.", "source_ref": "mindrian-graph://node/m1"}],
    }
    validate_request("analogy.retrieve_mechanism_candidates", request)
    result = retrieve_mechanisms(request)
    validate_result("analogy.retrieve_mechanism_candidates", result)
    assert result["scope_id"] == request["scope_id"]
    assert result["snapshot_id"] == request["snapshot_id"]
