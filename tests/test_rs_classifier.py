import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from mindrian_eureka.contracts import validate_request, validate_result
from mindrian_eureka.opportunity_pairs.mcp_server import scout_run_workflow
from mindrian_eureka.workflow_handlers import HANDLERS


def _request(lsa=0.8, bert=0.8):
    return {
        "scope_id": "room:rs-classifier",
        "snapshot_id": "snapshot:rs-13",
        "scored_pair": {
            "query_concept": "distributed sensing",
            "doc_concept": "swarm coordination",
            "diff": 0.65,
            "lsa": lsa,
            "bert": bert,
            "passes": True,
            "evidence": [
                {"source_id": "paper:1", "side": "problem", "sentence": "Sensors lose coordination when links fail."},
                {"source_id": "paper:2", "side": "method", "sentence": "Local consensus recovers coordination."},
            ],
            "second_signal": {"confirmed": True, "method": "independent review"},
            "novelty_check_status": "passed",
        },
    }


def test_rs_classifier_cli_mcp_contract_and_source_thresholds():
    request = _request()
    validate_request("research.classify_rs_pair", request)
    expected = HANDLERS["research.classify_rs_pair"](request)
    validate_result("research.classify_rs_pair", expected)
    assert scout_run_workflow("research.classify_rs_pair", request) == expected

    env = dict(os.environ)
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    with tempfile.TemporaryDirectory() as temp_dir:
        request_file = Path(temp_dir) / "request.json"
        request_file.write_text(json.dumps(request), encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-m", "mindrian_eureka.workflow_cli", "research.classify_rs_pair", str(request_file)],
            text=True, capture_output=True, env=env, check=True,
        )
    assert json.loads(completed.stdout) == expected
    assert expected["classification"] == "hybrid"
    assert expected["bridge_concept"] == "cross-domain isomorphism + semantic bridge"
    assert expected["scope_id"] == request["scope_id"]
    assert expected["classified_pair"]["evidence"] == request["scored_pair"]["evidence"]
    assert expected["input_fingerprint"] == HANDLERS["research.classify_rs_pair"](request)["input_fingerprint"]

    assert HANDLERS["research.classify_rs_pair"](_request(lsa=0.3, bert=0.3))["classification"] == "none"
    assert HANDLERS["research.classify_rs_pair"](_request(lsa=0.2, bert=0.8))["classification"] == "structural_transfer"
    assert HANDLERS["research.classify_rs_pair"](_request(lsa=0.8, bert=0.2))["classification"] == "semantic_implementation"


def test_rs_classifier_composes_through_breakthrough_and_thesis_contracts():
    classified = HANDLERS["research.classify_rs_pair"](_request())
    score_request = {
        "scope_id": classified["scope_id"],
        "snapshot_id": classified["snapshot_id"],
        "classified_pair": classified["classified_pair"],
        "options": {
            "substrate_metadata": {"tier": "applied"},
            "industry_signal_count": 4,
            "diff_percentile": 0.95,
            "pair_density": 0.25,
        },
    }
    validate_request("research.score_rs_breakthrough", score_request)
    scored = HANDLERS["research.score_rs_breakthrough"](score_request)
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
