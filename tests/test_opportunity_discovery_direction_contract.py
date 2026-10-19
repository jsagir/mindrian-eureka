from mindrian_eureka import opportunity_discovery


def test_signal_synthesis_uses_categorical_rs_direction(monkeypatch, tmp_path):
    artifacts = [
        {"id": "a", "source_ref": "mindrian-graph://node/a", "title": "A", "text": "alpha mechanism"},
        {"id": "b", "source_ref": "mindrian-graph://node/b", "title": "B", "text": "beta mechanism"},
    ]
    monkeypatch.setattr(opportunity_discovery, "run_document", lambda *args, **kwargs: {
        "status": "completed",
        "scope": {"scope_id": "room:test", "snapshot_id": "snap-1"},
        "outputs": [{
            "rank": 1,
            "payload": {
                "left": {"artifact_id": "a"},
                "right": {"artifact_id": "b"},
                "structural_similarity": 0.4,
                "semantic_similarity": 0.8,
                "disagreement": 0.4,
                "direction": "a_to_b",
            },
            "review_context": "Source-linked review context.",
        }],
        "method_details": {"encoder": {"name": "fixture"}},
        "warnings": [],
    })
    monkeypatch.setattr(opportunity_discovery, "run_hsi", lambda _request: {
        "status": "completed_empty", "hsi_pairs": [], "metadata": {}, "warnings": [],
    })

    result = opportunity_discovery.run_signal_synthesis(
        {"objective": "Explore links", "scope_id": "room:test", "snapshot_id": "snap-1",
         "artifacts": artifacts, "encoder": "fixture", "model_path": "unused"},
        data_dir=tmp_path, job_id="direction-contract",
    )

    rs_signal = result["outputs"][0]["payload"]["signals"]["rs"]
    assert rs_signal["direction"] == "a_to_b"
    assert isinstance(rs_signal["direction"], str)
    assert "disagreement" not in rs_signal
