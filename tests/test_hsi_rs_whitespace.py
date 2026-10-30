import json
import sys

import pytest

from mindrian_eureka.contracts import ContractError, validate_request, validate_result
from mindrian_eureka.opportunity_pairs import mcp_server
from mindrian_eureka.workflow_cli import main as workflow_cli_main
from mindrian_eureka.workflow_handlers import HANDLERS


def request():
    frameworks = [
        ("f-x", "Complex Systems", [1, 0, 0]),
        ("f-y", "Jobs To Be Done", [0, 1, 0]),
        ("f-z", "Future Design", [0, 0, 1]),
        ("f-all", "Wicked Problems", [.577, .577, .577]),
    ]
    sections = [
        ("alpha", [1, 0, 0]), ("beta", [0, 1, 0]),
        ("gamma", [0, 0, 1]), ("delta", [-1, 0, 0]),
    ]
    return {
        "scope_id": "room:downstream-whitespace", "snapshot_id": "snapshot:rs-coverage-11",
        "embedding_model": "local-research-v3", "signal_method": "percentile",
        "artifacts": [
            {"id": f"a-{section}", "section": section, "title": f"{name} notes",
             "text": f"{name} research and evidence", "source_ref": f"mindrian-graph://node/a-{section}", "vector": vector}
            for section, vector in sections for name in [section]
        ],
        "baseline_frameworks": [
            {"id": fid, "name": name, "source_ref": f"mindrian-graph://node/{fid}", "vector": vector}
            for fid, name, vector in frameworks
        ],
        "reverse_salients": [
            {"opportunity_id": f"rs-{i}", "source_section": "platform", "target_section": section,
             "differential_score": .8-i*.1, "source_ref": f"mindrian-graph://node/rs-{i}"}
            for i, (section, _) in enumerate(sections)
        ] + [{"opportunity_id": "rs-duplicate", "source_section": "platform", "target_section": "delta"}],
    }


def test_rs_whitespace_identifies_low_coverage_downstream_zone_with_lineage():
    payload = request()
    validate_request("portfolio.discover_rs_whitespace", payload)
    result = HANDLERS["portfolio.discover_rs_whitespace"](payload)
    validate_result("portfolio.discover_rs_whitespace", result)
    assert result["scope"] == {"scope_id": payload["scope_id"], "snapshot_id": payload["snapshot_id"]}
    assert result["metadata"]["bottlenecks_checked"] == 5
    assert result["metadata"]["sections_in_reference"] == 4
    assert len(result["zones"]) == 4  # one zone per target section
    delta = next(zone for zone in result["zones"] if zone["downstream_section"] == "delta")
    assert delta["gap_signal"] == "strong"
    assert delta["coverage_percentile"] == .25
    assert delta["bottleneck"]["opportunity_id"] == "rs-3"
    assert delta["source_trail"][1]["source_ref"].startswith("mindrian-graph://")
    assert result["input_fingerprint"]


def test_rs_whitespace_cli_and_mcp_share_contract(tmp_path, capsys, monkeypatch):
    payload = request()
    expected = HANDLERS["portfolio.discover_rs_whitespace"](payload)
    assert mcp_server.scout_run_workflow("portfolio.discover_rs_whitespace", payload) == expected
    path = tmp_path / "rs-whitespace.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["eureka-workflow", "portfolio.discover_rs_whitespace", str(path)])
    workflow_cli_main()
    assert json.loads(capsys.readouterr().out) == expected


def test_rs_whitespace_rejects_mismatched_embedding_dimensions():
    payload = request()
    payload["baseline_frameworks"][0]["vector"] = [1, 0]
    with pytest.raises(ContractError, match="share one embedding dimension/model"):
        HANDLERS["portfolio.discover_rs_whitespace"](payload)
