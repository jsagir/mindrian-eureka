import json
import sys

import pytest

from mindrian_eureka.contracts import ContractError, validate_request, validate_result
from mindrian_eureka.opportunity_pairs import mcp_server
from mindrian_eureka.workflow_cli import main as workflow_cli_main
from mindrian_eureka.workflow_handlers import HANDLERS


def request():
    return {
        "scope_id": "room:external-whitespace",
        "snapshot_id": "snapshot:approved-research-5",
        "embedding_model": "shared-research-v1",
        "research_grant_id": "grant:approved-literature-search",
        "retrieved_at": "2026-10-19T12:00:00Z",
        "artifacts": [
            {"id": "r1", "title": "Clinical device signals", "section": "health systems", "source_ref": "mindrian-graph://node/r1", "vector": [1, 0, 0]},
            {"id": "r2", "title": "Clinical monitoring devices", "section": "health systems", "source_ref": "mindrian-graph://node/r2", "vector": [.9, .1, 0]},
            {"id": "r3", "title": "Grid storage operations", "section": "energy systems", "source_ref": "mindrian-graph://node/r3", "vector": [0, 1, 0]},
            {"id": "r4", "title": "Battery storage networks", "section": "energy systems", "source_ref": "mindrian-graph://node/r4", "vector": [.1, .9, 0]},
        ],
        "external_papers": [
            {"id": "p1", "title": "Remote sensing for agriculture", "abstract": "Remote sensing methods combine distributed sensor networks with agricultural monitoring to identify field conditions and support more timely management decisions.", "source_ref": "https://papers.example/p1", "year": 2025, "fields_of_study": ["agriculture"], "vector": [0, 0, 1]},
            {"id": "p2", "title": "Clinical device monitoring", "abstract": "Clinical device monitoring uses sensor signals and care workflows to support diagnostic and operational decisions across hospitals and community health settings.", "source_ref": "https://papers.example/p2", "year": 2024, "fields_of_study": ["health systems"], "vector": [1, 0, 0]},
            {"id": "p3", "title": "Distributed sensor governance", "abstract": "Distributed governance approaches coordinate sensor data, public infrastructure, and local decision makers across connected environmental monitoring systems.", "source_ref": "https://papers.example/p3", "year": 2023, "fields_of_study": ["public policy"], "vector": [.7, .7, 0]},
            {"id": "p4", "title": "Battery diagnostics", "abstract": "Battery diagnostic methods compare operating signals with degradation patterns to improve energy storage maintenance and grid reliability.", "source_ref": "https://papers.example/p4", "year": 2022, "fields_of_study": ["energy systems"], "vector": [0, 1, 0]},
        ],
        "known_gaps": [{"id": "gap-1", "zone_id": "ws-governance", "framework_name": "Distributed governance", "nearest_artifact_ids": ["r1", "r2"]}],
        "zone_percentile": .5,
        "gap_fill_percentile": .5,
        "cross_domain_percentile": .5,
    }


def test_external_whitespace_returns_traceable_gap_and_cross_domain_leads():
    payload = request()
    validate_request("portfolio.analyze_external_whitespace", payload)
    result = HANDLERS["portfolio.analyze_external_whitespace"](payload)
    validate_result("portfolio.analyze_external_whitespace", result)
    assert result["scope"] == {"scope_id": payload["scope_id"], "snapshot_id": payload["snapshot_id"]}
    assert result["research_grant_id"] == payload["research_grant_id"]
    assert result["cross_domain_zones"]
    assert result["gap_filling_suggestions"]
    assert result["cross_domain_papers"]
    for zone in result["cross_domain_zones"]:
        assert zone["source_trail"][0]["source_ref"].startswith("https://papers.example/")
    assert all(paper["source_trail"] for group in result["gap_filling_suggestions"] for paper in group["suggested_papers"])
    assert "exhaustive literature novelty" in " ".join(result["limitations"])


def test_external_whitespace_cli_and_mcp_share_result_contract(tmp_path, capsys, monkeypatch):
    payload = request()
    expected = HANDLERS["portfolio.analyze_external_whitespace"](payload)
    assert mcp_server.scout_run_workflow("portfolio.analyze_external_whitespace", payload) == expected
    path = tmp_path / "external-whitespace.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["eureka-workflow", "portfolio.analyze_external_whitespace", str(path)])
    workflow_cli_main()
    assert json.loads(capsys.readouterr().out) == expected


def test_external_whitespace_requires_host_grant_and_matching_vectors():
    payload = request()
    payload.pop("research_grant_id")
    with pytest.raises(ContractError, match="research_grant_id"):
        HANDLERS["portfolio.analyze_external_whitespace"](payload)
    payload = request()
    payload["external_papers"][0]["vector"] = [1, 2]
    with pytest.raises(ContractError, match="share one embedding dimension/model"):
        HANDLERS["portfolio.analyze_external_whitespace"](payload)
