import pytest
import json
import sys

from mindrian_eureka.contracts import ResultContractError, validate_request, validate_result
from mindrian_eureka.workflow_handlers import HANDLERS
from mindrian_eureka.opportunity_pairs import mcp_server
from mindrian_eureka.workflow_cli import main as workflow_cli_main


SCOPE = "room:workflow"
SNAPSHOT = "mos-snapshot-workflow-4"


def test_shared_workflows_echo_graph_snapshot_lineage():
    evidence = [{"id": "e1", "source_ref": "mindrian-graph://node/e1", "claim": "Source evidence."}]
    cases = [
        ("research.prepare_multidomain_plan", {"objective": "Find mechanisms", "approved_domains": ["thermal systems"]}),
        ("research.group_multidomain_findings", {"findings": [{"id": "f1", "claim": "A sourced finding", "source_ref": "room://finding/1"}]}),
        ("analysis.audit_claim_traceability", {"proposal": "Test a mechanism", "claims": [{"id": "c1", "text": "A claim", "evidence_ids": ["e1"], "counterevidence_ids": []}], "evidence": evidence}),
        ("analysis.critique_pitch", {"pitch": "A sourced pitch with mechanism and intended use.", "proposal": "Test a mechanism", "claims": [{"id": "c1", "text": "A claim", "evidence_ids": ["e1"]}], "evidence": evidence}),
        ("deliberation.prepare_six_hat_review", {"topic": "A decision", "hypothesis": "A testable hypothesis", "arguments": [{"id": f"arg-{hat}", "hat": hat, "argument": f"{hat} perspective", "evidence_ids": ["e1"]} for hat in ("white", "red", "black", "yellow", "green", "blue")], "evidence": evidence}),
        ("graph.package_relationship_proposals", {"nodes": [{"id": "n1", "source_ref": "mindrian-graph://node/n1"}, {"id": "n2", "source_ref": "mindrian-graph://node/n2"}], "evidence": evidence, "relationships": [{"source_id": "n1", "target_id": "n2", "relation": "related_to", "rationale": "Candidate to review", "evidence_ids": ["e1"]}]}),
        ("discovery.plan_opportunity_scout", {"objective": "Explore future opportunity", "capability_ids": ["graph.prepare_artifact_bundle"]}),
    ]
    for capability_id, specific in cases:
        request = {**specific, "scope_id": SCOPE, "snapshot_id": SNAPSHOT}
        validate_request(capability_id, request)
        result = HANDLERS[capability_id](request)
        validate_result(capability_id, result)
        assert result.get("scope_id") == SCOPE, capability_id
        assert result.get("snapshot_id") == SNAPSHOT, capability_id


def test_taxonomy_coverage_capability_runs_through_cli_and_mcp(tmp_path, capsys, monkeypatch):
    capability_id = "portfolio.inventory_taxonomy_coverage"
    request = {
        "scope_id": "room:coverage",
        "snapshot_id": "coverage-snapshot-1",
        "taxonomy_source": "fixture:taxonomy-v1",
        "artifacts": [
            {"id": "a", "category_ids": ["represented"], "source_ref": "mindrian-graph://node/a"},
            {"id": "b", "category_ids": [], "source_ref": "mindrian-graph://node/b"},
        ],
        "taxonomy": [{"id": "represented", "label": "Represented"}, {"id": "open", "label": "Open"}],
    }
    expected = HANDLERS[capability_id](request)
    expected["provenance"].pop("computed_at")
    mcp_result = mcp_server.scout_run_workflow(capability_id, request)
    mcp_result["provenance"].pop("computed_at")
    assert mcp_result == expected

    input_file = tmp_path / "coverage.json"
    input_file.write_text(json.dumps(request), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["eureka-workflow", capability_id, str(input_file)])
    workflow_cli_main()
    cli_result = json.loads(capsys.readouterr().out)
    cli_result["provenance"].pop("computed_at")
    assert cli_result == expected


def test_direct_mcp_sme_and_decision_routes_enforce_published_result_schemas(monkeypatch):
    from mindrian_eureka.opportunity_pairs import mcp_server

    monkeypatch.setattr(mcp_server.sme_workflow, "map_structures", lambda _document: {})
    valid_empty_mapping = {
        "run_id": "sme-result-contract", "scope_id": "room:sme-result-contract",
        "target": {"expressions": []}, "target_evidence": {}, "evidence_catalog": [],
        "bases": [{"base_id": "base", "domain": "fixture", "description": {"expressions": []}, "evidence": {}}],
    }
    with pytest.raises(ResultContractError):
        mcp_server.scout_sme_map(mcp_server.StructureMappingInput(document=valid_empty_mapping))

    monkeypatch.setattr(mcp_server.decision_patterns, "analyze_sequence", lambda _request: {})
    model = lambda model_id: {
        "id": model_id,
        "initial_distribution": [0.25, 0.25, 0.25, 0.25],
        "transition_matrix": [[0.25, 0.25, 0.25, 0.25] for _ in range(4)],
        "emission_probabilities": [[0.5, 0.5, 0.5, 0.5] for _ in range(4)],
    }
    sequence = mcp_server.DecisionSequenceInput(
        scope_id="room:test", sequence_id="seq-1",
        observations=[{"step_id": "step-1", "features": {
            "complex_features": True, "multidirectional_causation": False,
            "holistic_view": True, "creative_synthesis": False,
        }}],
        models=[model("one"), model("two")],
    )
    with pytest.raises(ResultContractError):
        mcp_server.decision_compare_sequence_patterns(sequence)


def test_direct_mcp_research_plan_route_emits_catalog_valid_result():
    from mindrian_eureka.opportunity_pairs import mcp_server

    request = mcp_server.ResearchPlanInput(
        run_id="run-contract-check", stage="mechanism_discovery", scope_id="room:contract-check",
        queries=[{"query_id": "q1", "provider": "openalex", "query": "thermal transfer mechanism",
                  "why": "Find a source mechanism", "intent": "find_mechanism"}],
    )
    result = mcp_server.scout_sme_prepare_research(request)
    assert result["schema_version"] == "eureka.external-research-plan.v1"
    assert result["queries"][0]["query_hash"]


def test_direct_jason_hsi_and_fitness_tools_reject_requests_outside_the_catalog_contract():
    from mindrian_eureka.opportunity_pairs import mcp_server

    assert mcp_server.scout_compare_text_differences({"unpublished_field": True})["status"] == "invalid_input"
    assert mcp_server.scout_find_hybrid_similarity_pairs({"artifacts": []})["status"] == "invalid_input"
    assert mcp_server.scout_assess_analogy_fitness({})["status"] == "invalid_input"


def test_direct_jason_hsi_and_fitness_tools_validate_successful_results(monkeypatch):
    from mindrian_eureka.opportunity_pairs import mcp_server

    monkeypatch.setattr(mcp_server, "_run_jason_workflow", lambda _request: {
        "schema_version": "eureka.text-difference-result.v1", "capability_id": "analysis.compare_text_differences",
        "status": "completed_descriptive_analysis", "pairs": [], "buzzword_heuristic": [], "label": "diagnostic",
    })
    assert mcp_server.scout_compare_text_differences({})["status"] == "completed_descriptive_analysis"

    monkeypatch.setattr(mcp_server, "run_hsi", lambda _request: {
        "schema_version": "eureka.hsi-result.v1", "capability_id": "portfolio.find_hybrid_similarity_pairs",
        "status": "completed_experimental", "hsi_pairs": [], "warnings": [],
    })
    assert mcp_server.scout_find_hybrid_similarity_pairs({"artifacts": [{"id": "a", "text": "a"}, {"id": "b", "text": "b"}]})["status"] == "completed_experimental"

    monkeypatch.setattr(mcp_server, "assess_analogy_fitness", lambda _request: {
        "schema_version": "eureka.analogy-fitness-result.v1", "capability_id": "analogy.assess_structural_fitness",
        "status": "completed_experimental", "limitations": [],
    })
    group = {"id": "g", "source_ref": "fixture:g", "structure": {
        "state_change": "s", "action": "a", "parts": "p", "phenomenon": "ph",
        "input": "i", "real_effect": "r", "effect": "e"},
        "evidence_refs": {key: [] for key in ("state_change", "action", "parts", "phenomenon", "input", "real_effect", "effect")}}
    result = mcp_server.scout_assess_analogy_fitness({"target": group, "candidates": [group]})
    assert result["status"] == "completed_experimental"
