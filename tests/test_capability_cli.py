import json
import sys
from pathlib import Path

from mindrian_eureka.cli import main


CATALOG = Path(__file__).parents[1] / "src/mindrian_eureka/data/capability-catalog.v1.json"


def invoke(monkeypatch, capsys, *arguments):
    monkeypatch.setattr(sys, "argv", ["eureka", "capabilities", *arguments])
    main()
    return json.loads(capsys.readouterr().out)


def test_compact_capability_catalog_preserves_all_jobs_and_readiness(monkeypatch, capsys):
    source = json.loads(CATALOG.read_text(encoding="utf-8"))
    result = invoke(monkeypatch, capsys, "--summary")

    assert result["schema_version"] == source["schema_version"]
    assert result["catalog_version"] == source["catalog_version"]
    assert result["count"] == len(source["capabilities"]) == 68
    assert {item["id"] for item in result["capabilities"]} == {item["id"] for item in source["capabilities"]}
    assert result["counts_by_status"] == {
        "experimental": 55,
        "host_brokered": 5,
        "blocked": 4,
        "planned": 4,
    }
    for item in result["capabilities"]:
        assert item["name"]
        assert item["jtbd"]
        assert item["status"]
        assert "cli" in item
        assert "mcp" in item
        assert "input_schema" not in item
        assert "output_schema" not in item
    handoffs = {item["id"]: item["host_handoff"] for item in result["capabilities"] if "host_handoff" in item}
    assert set(handoffs) == {
        "opportunity.discover_breakthroughs",
        "research.orchestrate_multidomain",
        "deliberation.structure",
        "bottleneck.diagnose",
        "claims.compare",
        "evidence.fetch_for_question",
        "experts.find_for_topic",
        "thesis.read_prior",
    }
    assert handoffs["bottleneck.diagnose"]["type"] == "host_native"
    assert handoffs["thesis.read_prior"]["type"] == "host_native"
    assert "rs_thesis_read" in handoffs["thesis.read_prior"]["mcp"]
    assert "not an Eureka route" in handoffs["thesis.read_prior"]["mcp"]
    assert handoffs["claims.compare"]["type"] == "related_partial"
    assert handoffs["claims.compare"]["capabilities"] == [
        "analysis.compare_text_differences", "analysis.audit_claim_traceability"
    ]
    assert handoffs["experts.find_for_topic"]["type"] == "related_partial"
    assert handoffs["experts.find_for_topic"]["capabilities"] == ["research.extract_experts_from_papers"]
    assert "rs_experts_find" in handoffs["experts.find_for_topic"]["mcp"]
    assert "external expert directory" in handoffs["experts.find_for_topic"]["limitation"]
    assert handoffs["research.orchestrate_multidomain"]["capabilities"] == [
        "research.run_genesis_local_plan", "research.prepare_multidomain_plan",
        "research.group_multidomain_findings"
    ]
    by_id = {item["id"]: item for item in source["capabilities"]}
    for handoff in handoffs.values():
        for capability_id in handoff.get("capabilities", []):
            related = by_id[capability_id]
            assert related["status"] in {"experimental", "host_brokered"}
            assert related["routes"]["cli"]
            assert related["routes"]["mcp"]


def test_capability_catalog_can_filter_by_readiness_and_jtbd(monkeypatch, capsys):
    blocked = invoke(monkeypatch, capsys, "--summary", "--status", "blocked")
    assert blocked["count"] == 4
    assert all(item["status"] == "blocked" for item in blocked["capabilities"])
    assert all(item["cli"] is None and item["mcp"] is None for item in blocked["capabilities"])
    assert all(item["host_handoff"] for item in blocked["capabilities"])

    selected = invoke(monkeypatch, capsys, "--summary", "--search", "wicked")
    assert selected["count"] > 0
    assert all("wicked" in json.dumps(item).casefold() for item in selected["capabilities"])


def test_default_capabilities_output_remains_full_catalog(monkeypatch, capsys):
    source = json.loads(CATALOG.read_text(encoding="utf-8"))
    result = invoke(monkeypatch, capsys)
    assert result == source
