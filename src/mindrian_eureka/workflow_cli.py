"""CLI for source-bounded local discovery workflow stages."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .contracts import validate_request, validate_result
from .workflow_handlers import HANDLERS


def main() -> None:
    parser = argparse.ArgumentParser(prog="eureka-workflow", description="Run a local MindrianOS Eureka workflow stage from a JSON bundle.")
    parser.add_argument("capability_id", choices=sorted(HANDLERS))
    parser.add_argument("input", help="JSON request bundle")
    parser.add_argument("--output", default="-", help="Output JSON path, or - for stdout")
    args = parser.parse_args()
    try:
        source = Path(args.input)
        if source.stat().st_size > 20 * 1024 * 1024:
            raise ValueError("Input bundle exceeds 20 MiB")
        document = json.loads(source.read_text(encoding="utf-8-sig"))
        if not isinstance(document, dict):
            raise ValueError("Input bundle must contain a JSON object")
        validate_request(args.capability_id, document)
        result = HANDLERS[args.capability_id](document)
        validate_result(args.capability_id, result)
        if args.capability_id == "analysis.compare_text_differences" and result.get("errors"):
            result["status"] = "invalid_input"
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output == "-":
            sys.stdout.write(rendered)
        else:
            Path(args.output).write_text(rendered, encoding="utf-8")
    except Exception as exc:
        parser.exit(2, f"eureka-workflow: {exc}\n")


if __name__ == "__main__":
    main()
