import json
import sys

import pytest

from mindrian_eureka.contracts import ContractError, validate_request
from mindrian_eureka.opportunity_pairs import mcp_server
from mindrian_eureka.structure_mapping.cli import main as sme_cli_main


def _mapping_request():
    return {
        "run_id": "sme-parity-1",
        "scope_id": "room:sme-parity",
        "target": {
            "name": "target",
            "entities": ["oxygen", "plant"],
            "expressions": [{"name": "flow-expression", "functor": "flow", "args": ["oxygen", "plant"]}],
        },
        "target_evidence": {"flow-expression": ["claim-target"]},
        "evidence_catalog": [
            {"claim_id": "claim-target", "source_ref": "room://claim/target", "text": "oxygen flows to plant"},
            {"claim_id": "claim-base", "source_ref": "room://claim/base", "text": "water flows to tree"},
        ],
        "bases": [{
            "base_id": "base-water",
            "domain": "hydrology",
            "description": {
                "name": "source",
                "entities": ["water", "tree"],
                "expressions": [{"name": "flow-expression", "functor": "flow", "args": ["water", "tree"]}],
            },
            "evidence": {"flow-expression": ["claim-base"]},
        }],
        "rules": ["AN"],
        "max_maps_per_base": 2,
    }


def test_sme_mapping_cli_and_mcp_return_the_same_source_linked_result(tmp_path, monkeypatch, capsys):
    request = _mapping_request()
    validate_request("analogy.map_structure", {"document": request})
    input_path = tmp_path / "mapping.json"
    input_path.write_text(json.dumps({"document": request}), encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["eureka-sme", "map", str(input_path)])
    assert sme_cli_main() == 0
    cli_result = json.loads(capsys.readouterr().out)

    mcp_result = mcp_server.scout_sme_map(mcp_server.StructureMappingInput(document=request))
    assert cli_result == mcp_result
    assert cli_result["capability_id"] == "analogy.map_structure"
    assert cli_result["status"] == "completed"
    assert cli_result["scope_id"] == request["scope_id"]
    assert cli_result["maps"][0]["correspondences"]
    assert [row["claim_id"] for row in cli_result["evidence_catalog"]] == ["claim-base", "claim-target"]


def test_sme_mapping_contract_rejects_untyped_or_unlinked_inputs():
    request = _mapping_request()
    request["bases"][0]["evidence"]["flow-expression"] = []
    with pytest.raises(ContractError):
        validate_request("analogy.map_structure", {"document": request})

    request = _mapping_request()
    request["bases"][0]["description"]["expressions"] = [{"args": ["water"]}]
    with pytest.raises(ContractError):
        validate_request("analogy.map_structure", {"document": request})
