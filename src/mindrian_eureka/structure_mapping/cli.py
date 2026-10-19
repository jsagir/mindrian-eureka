"""File-in/file-out operator interface for the SME research workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import workflow


def _read(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write(value):
    sys.stdout.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="eureka-sme", description="Local structural mapping and host-brokered SME research")
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
        _write(workflow.prepare_research_plan(**_read(args.request_json)))
    elif args.command == "validate-bundle":
        _write(workflow.validate_research_bundle(_read(args.plan_json), _read(args.bundle_json)))
    elif args.command == "map":
        _write(workflow.map_structures(_read(args.mapping_input_json)))
    else:
        _write(workflow.finalize_assessments(
            _read(args.mapping_result_json), _read(args.verification_plan_json),
            _read(args.evidence_bundle_json), _read(args.assessments_json),
        ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
