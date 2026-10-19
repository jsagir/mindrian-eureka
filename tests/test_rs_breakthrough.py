import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from mindrian_eureka.contracts import validate_request, validate_result
from mindrian_eureka.opportunity_pairs.mcp_server import scout_run_workflow
from mindrian_eureka.workflow_handlers import HANDLERS


def _request():
    return {
        "scope_id": "room:rs",
        "snapshot_id": "snap-rs-12",
        "classified_pair": {
            "query_concept": "distributed sensing",
            "doc_concept": "swarm coordination",
            "diff": 0.65,
            "lsa": 0.5,
            "bert": 0.7,
            "passes": True,
            "classification": "hybrid",
            "bridge_concept": "local consensus",
            "evidence": [
                {"source_id": "paper:1", "side": "problem", "sentence": "Sensors lose coordination when links fail."},
                {"source_id": "paper:2", "side": "method", "sentence": "Local consensus recovers coordination."},
            ],
            "second_signal": {"confirmed": True, "method": "independent review"},
            "novelty_check_status": "passed",
        },
        "options": {
            "substrate_metadata": {"tier": "applied"},
            "industry_signal_count": 4,
            "diff_percentile": 0.95,
            "pair_density": 0.25,
        },
    }


def test_rs_breakthrough_cli_mcp_contract_and_determinism():
    request = _request()
    validate_request("research.score_rs_breakthrough", request)
    expected = HANDLERS["research.score_rs_breakthrough"](request)
    validate_result("research.score_rs_breakthrough", expected)
    assert scout_run_workflow("research.score_rs_breakthrough", request) == expected

    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    with tempfile.TemporaryDirectory() as temp_dir:
        request_file = Path(temp_dir) / "request.json"
        request_file.write_text(json.dumps(request), encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-m", "mindrian_eureka.workflow_cli", "research.score_rs_breakthrough", str(request_file)],
            text=True, capture_output=True, env=env, check=True,
        )
    assert json.loads(completed.stdout) == expected
    assert expected["status"] == "score_ready"
    assert expected["scope_id"] == request["scope_id"]
    assert expected["snapshot_id"] == request["snapshot_id"]
    assert expected["breakthrough"]["score"] == 7.0
    assert expected["breakthrough"]["dominant_dimension"] == "feasibility"
    assert expected["classified_pair"]["evidence"] == request["classified_pair"]["evidence"]
    assert expected["input_fingerprint"] == HANDLERS["research.score_rs_breakthrough"](request)["input_fingerprint"]


def test_rs_breakthrough_output_feeds_evidence_linked_thesis_stage():
    scored = HANDLERS["research.score_rs_breakthrough"](_request())
    thesis_request = {
        "scope_id": scored["scope_id"],
        "snapshot_id": scored["snapshot_id"],
        "classified_pair": scored["classified_pair"],
        "breakthrough": scored["breakthrough"],
    }
    validate_request("research.generate_rs_thesis", thesis_request)
    thesis = HANDLERS["research.generate_rs_thesis"](thesis_request)
    assert thesis["status"] == "hypothesis_recorded"
    assert thesis["source_ids"] == ["paper:1", "paper:2"]
    assert thesis["scope_id"] == scored["scope_id"]
    assert thesis["snapshot_id"] == scored["snapshot_id"]
