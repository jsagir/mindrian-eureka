import json
import sys

from mindrian_eureka.contracts import validate_request, validate_result
from mindrian_eureka.opportunity_pairs import mcp_server
from mindrian_eureka.workflow_cli import main as workflow_cli_main
from mindrian_eureka.workflow_handlers import HANDLERS


CAPABILITY_ID = "research.classify_ip_finance_domain_signals"
REQUEST = {
    "scope_id": "room:ip-finance",
    "snapshot_id": "snapshot:ip-finance-1",
    "segments": [{
        "id": "paper:ip-lending",
        "source_ref": "room://paper/ip-lending",
        "text": "Patent-backed lending depends on IP collateral valuation, credit risk analysis, and royalty securitization.",
    }],
}


def test_latest_ip_finance_domain_detector_preserves_lineage_and_cli_mcp_parity(tmp_path, capsys, monkeypatch):
    original = json.loads(json.dumps(REQUEST))
    validate_request(CAPABILITY_ID, REQUEST)
    expected = HANDLERS[CAPABILITY_ID](REQUEST)
    assert REQUEST == original
    validate_result(CAPABILITY_ID, expected)
    assert expected["status"] == "completed_lexical_domain_scan"
    assert expected["scope_id"] == REQUEST["scope_id"]
    assert expected["snapshot_id"] == REQUEST["snapshot_id"]
    assert expected["segment_results"][0]["id"] == "paper:ip-lending"
    assert expected["segment_results"][0]["source_ref"] == "room://paper/ip-lending"
    assert expected["segment_results"][0]["classification"]["domain"] == "IP-Backed-Finance"
    assert expected["warnings"] == []
    assert expected["provenance"]["source_sha256"] == "55ef917bb46da7065e668aba8e3df019e24259fc1b593a20a5a726597931319d"
    assert any("not calibrated probabilities" in item for item in expected["limitations"])

    mcp_result = mcp_server.scout_run_workflow(CAPABILITY_ID, REQUEST)
    validate_result(CAPABILITY_ID, mcp_result)
    assert mcp_result == expected

    input_file = tmp_path / "ip-finance.json"
    input_file.write_text(json.dumps(REQUEST), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["eureka-workflow", CAPABILITY_ID, str(input_file)])
    workflow_cli_main()
    cli_result = json.loads(capsys.readouterr().out)
    assert cli_result == expected


def test_ip_finance_domain_detector_rejects_wrong_source_hash():
    request = json.loads(json.dumps(REQUEST))
    request["segments"][0]["sha256"] = "0" * 64
    try:
        HANDLERS[CAPABILITY_ID](request)
    except ValueError as error:
        assert "text hash does not match" in str(error)
    else:
        raise AssertionError("bad segment hashes must be refused")


def test_ambiguous_domain_acronyms_are_reported_with_source_lineage():
    request = json.loads(json.dumps(REQUEST))
    request["segments"][0]["id"] = "paper:parkinsons"
    request["segments"][0]["text"] = "A biomarker detects Parkinson's disease (PD) from a blood sample."
    result = HANDLERS[CAPABILITY_ID](request)
    assert result["segment_results"][0]["classification"]["domain"] == "Credit-Risk-Analysis"
    assert result["warnings"][0]["code"] == "ambiguous_acronym_match"
    assert result["warnings"][0]["tokens"] == ["pd"]
    assert result["warnings"][0]["segment_id"] == "paper:parkinsons"
    assert result["warnings"][0]["source_ref"] == request["segments"][0]["source_ref"]
