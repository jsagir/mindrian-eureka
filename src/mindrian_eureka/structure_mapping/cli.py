"""File-in/file-out operator interface for the SME research workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import workflow
from ..contracts import validate_request, validate_result


def _read(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(value):
    sys.stdout.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="eureka-structure-mapping", description="Map structures and prepare host-brokered verification research")
    commands = parser.add_subparsers(dest="command", required=True)
    plan = commands.add_parser("plan", help="freeze exact query strings for host-side review and approval")
    plan.add_argument("request_json")
    validate = commands.add_parser("validate-bundle", help="validate query/source lineage in a host-returned bundle")
    validate.add_argument("plan_json")
    validate.add_argument("bundle_json")
    mapping = commands.add_parser("map", help="run SME locally over a prepared mapping document")
    mapping.add_argument("mapping_input_json")
    finalize = commands.add_parser("finalize", help="attach human/model-reviewed evidence assessments")
    finalize.add_argument("mapping_result_json")
    finalize.add_argument("verification_plan_json")
    finalize.add_argument("evidence_bundle_json")
    finalize.add_argument("assessments_json")
    args = parser.parse_args(argv)
    if args.command == "plan":
        request = _read(args.request_json)
        validate_request("analogy.cross_domain_research", {"stage": "prepare_research_plan", "request": request})
        result = workflow.prepare_research_plan(**request)
        validate_result("analogy.cross_domain_research", result)
        _write(result)
    elif args.command == "validate-bundle":
        request = {"plan": _read(args.plan_json), "bundle": _read(args.bundle_json)}
        validate_request("analogy.cross_domain_research", {"stage": "validate_research_bundle", "request": request})
        result = workflow.validate_research_bundle(request["plan"], request["bundle"])
        validate_result("analogy.cross_domain_research", result)
        _write(result)
    elif args.command == "map":
        document = _read(args.mapping_input_json)
        payload = document if "document" in document else {"document": document}
        validate_request("analogy.map_structure", payload)
        result = workflow.map_structures(payload["document"])
        validate_result("analogy.map_structure", result)
        _write(result)
    else:
        request = {"mapping_result": _read(args.mapping_result_json),
                   "verification_plan": _read(args.verification_plan_json),
                   "evidence_bundle": _read(args.evidence_bundle_json),
                   "assessments": _read(args.assessments_json)}
        validate_request("analogy.cross_domain_research", {"stage": "finalize_assessments", "request": request})
        result = workflow.finalize_assessments(request["mapping_result"], request["verification_plan"],
                                               request["evidence_bundle"], request["assessments"])
        validate_result("analogy.cross_domain_research", result)
        _write(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
