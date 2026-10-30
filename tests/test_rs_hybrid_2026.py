import numpy as np
import mindrian_eureka.opportunity_pairs.runner as runner

from mindrian_eureka.opportunity_pairs.algorithm import (
    Artifact,
    _bm25_cosine,
    rank_pairs,
    rank_pairs_hybrid_2026,
)


def _fixture():
    artifacts = [
        Artifact(f"a{i}", f"Title {i}", text, corpus="room" if i < 3 else "external")
        for i, text in enumerate((
            "battery storage grid power resilience", "clinical imaging diagnostic signal",
            "agricultural water irrigation crop yield", "battery chemistry electrochemical storage",
            "medical sensor image diagnostic",
        ))
    ]
    structural = np.array([
        [1, .8, .2, .3, .1], [.8, 1, .1, .2, .7], [.2, .1, 1, .4, .3],
        [.3, .2, .4, 1, .6], [.1, .7, .3, .6, 1],
    ])
    semantic = np.array([
        [1, .2, .7, .9, .2], [.2, 1, .3, .1, .9], [.7, .3, 1, .5, .2],
        [.9, .1, .5, 1, .3], [.2, .9, .2, .3, 1],
    ])
    return artifacts, structural, semantic


def test_latest_hybrid_returns_stable_scored_candidates():
    artifacts, structural, semantic = _fixture()
    pairs = rank_pairs_hybrid_2026(artifacts, structural, semantic, top_k=10)
    assert pairs
    assert all(pair.method_signals["scoring"] == "hybrid_2026" for pair in pairs)
    assert all(0 <= pair.method_signals["gap_percentile"] <= 1 for pair in pairs)
    assert pairs == rank_pairs_hybrid_2026(artifacts, structural, semantic, top_k=10)


def test_latest_hybrid_enforces_minimum_eligible_pair_count():
    artifacts, structural, semantic = _fixture()
    pairs = rank_pairs_hybrid_2026(artifacts[:4], structural[:4, :4], semantic[:4, :4])
    assert pairs == []


def test_legacy_ranker_remains_available_and_bm25_is_symmetric():
    artifacts, structural, semantic = _fixture()
    assert rank_pairs(artifacts, structural, semantic, top_k=3)
    lexical = _bm25_cosine([artifact.model_text for artifact in artifacts])
    assert np.allclose(lexical, lexical.T)


def test_runner_honors_scoring_request_and_returns_traceable_method_metadata(monkeypatch, tmp_path):
    artifacts, structural, semantic = _fixture()
    monkeypatch.setattr(runner, "structural_similarity", lambda _texts, cancel_check=None: (structural, {
        "small_corpus_topic_adaptation": False, "empty_topic_profile_rows": [],
    }))
    monkeypatch.setattr(runner, "cached_encode", lambda texts, **kwargs: (
        [np.array([1.0, float(index + 1)]) for index, _ in enumerate(texts)], {"cache": "test"}
    ))
    monkeypatch.setattr(runner, "modern_semantic_similarity", lambda _vectors: (semantic, {"method": "fixture"}))
    request = {
        "objective": "Find cross-domain leads", "scope_id": "room-test", "snapshot_id": "mos-snapshot-42", "mode": "local",
        "scoring": "hybrid_2026", "artifacts": [
            {"id": item.id, "title": item.title, "text": item.text, "source_ref": f"mindrian-graph://node/{item.id}"}
            for item in artifacts
        ],
    }
    result = runner.run_document(
        request, encoder_name="sentence-transformers", model_path="local-fixture",
        cache_path=tmp_path / "cache.sqlite3",
    )
    assert result["method_details"]["scoring"]["method"] == "hybrid_2026"
    assert result["outputs"]
    assert result["outputs"][0]["payload"]["method_signals"]["scoring"] == "hybrid_2026"
    assert result["scope"]["scope_id"] == "room-test"
    assert result["scope"]["snapshot_id"] == "mos-snapshot-42"
    assert result["method_details"]["input_digest"].startswith("sha256:")


def test_input_validator_rejects_invalid_hybrid_configuration():
    from mindrian_eureka.opportunity_pairs.runner import validate_document

    payload = {"artifacts": [{"id": "a", "text": "text", "source_ref": "room://a"},
                             {"id": "b", "text": "text", "source_ref": "room://b"}]}
    validate_document(payload)
    payload["lex_weight"] = 1.5
    try:
        validate_document(payload)
    except ValueError as exc:
        assert "lex_weight" in str(exc)
    else:
        raise AssertionError("out-of-range lex_weight was accepted")
