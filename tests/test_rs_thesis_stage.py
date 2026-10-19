import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from mindrian_eureka.contracts import validate_request, validate_result
from mindrian_eureka.workflow_handlers import HANDLERS
from mindrian_eureka.opportunity_pairs.mcp_server import scout_run_workflow


def test_rs_thesis_generation_is_evidence_linked_and_contract_valid():
    request = {
        "scope_id": "room:rs",
        "snapshot_id": "snap-rs-12",
        "classified_pair": {
            "query_concept": "distributed sensing",
            "doc_concept": "swarm coordination",
            "classification": "structural_transfer",
            "bridge_concept": "local consensus",
            "evidence": [
                {"source_id": "paper:1", "side": "problem", "sentence": "Sensors lose coordination when links fail."},
                {"source_id": "paper:2", "side": "method", "sentence": "Local consensus recovers coordination."},
            ],
            "second_signal": {"confirmed": True, "method": "independent review"},
            "novelty_check_status": "passed",
        },
        "breakthrough": {"dominant_dimension": "feasibility"},
    }
    validate_request("research.generate_rs_thesis", request)
    result = HANDLERS["research.generate_rs_thesis"](request)
    validate_result("research.generate_rs_thesis", result)
    mcp_result = scout_run_workflow("research.generate_rs_thesis", request)
    assert mcp_result == result

    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    with tempfile.TemporaryDirectory() as temp_dir:
        request_file = Path(temp_dir) / "request.json"
        request_file.write_text(json.dumps(request), encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-m", "mindrian_eureka.workflow_cli", "research.generate_rs_thesis", str(request_file)],
            text=True, capture_output=True, env=env, check=True,
        )
    assert json.loads(completed.stdout) == mcp_result

    assert result["status"] == "hypothesis_recorded"
    assert result["scope_id"] == "room:rs"
    assert result["snapshot_id"] == "snap-rs-12"
    assert result["thesis"] == (
        "By applying distributed sensing to swarm coordination, achieve feasible novel transfer "
        "because isomorphic structure transfers under local consensus."
    )
    assert result["confidence"] == 0.9
    assert result["source_ids"] == ["paper:1", "paper:2"]
    assert result["input_fingerprint"] == HANDLERS["research.generate_rs_thesis"](request)["input_fingerprint"]
    assert "Confidence is a fixed heuristic" in " ".join(result["limitations"])


def test_rs_thesis_without_evidence_stays_unsupported():
    request = {"classified_pair": {
        "query_concept": "A", "doc_concept": "B", "classification": "hybrid"
    }}
    result = HANDLERS["research.generate_rs_thesis"](request)
    assert result["status"] == "unsupported_hypothesis"
    assert result["confidence"] == 0.05
    assert result["confidence_label"] == "unsupported"
    assert result["evidence"] == []
