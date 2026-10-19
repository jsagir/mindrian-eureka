"""JSON CLI for the configurable decision-sequence HMM capability."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .algorithm import analyze_sequence, fit_model
from ..contracts import validate_request, validate_result


def main() -> None:
    parser = argparse.ArgumentParser(prog="eureka-decision-sequences", description="Compare or exploratory-fit decision-sequence models.")
    parser.add_argument("command", choices=("analyze", "fit"), help="analyze a trace or fit exploratory parameters")
    parser.add_argument("input", help="JSON input bundle")
    parser.add_argument("--output", default="-", help="Output JSON path (default: stdout)")
    args = parser.parse_args()
    try:
        source = Path(args.input)
        if source.stat().st_size > 5 * 1024 * 1024:
            raise ValueError("Input bundle exceeds 5 MiB")
        document = json.loads(source.read_text(encoding="utf-8"))
        if args.command == "fit":
            validate_request("decision.fit_sequence_patterns", document)
            result = fit_model(document)
            validate_result("decision.fit_sequence_patterns", result)
        else:
            validate_request("decision.compare_sequence_patterns", document)
            result = analyze_sequence(document)
            validate_result("decision.compare_sequence_patterns", result)
        rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.output == "-":
            sys.stdout.write(rendered)
        else:
            Path(args.output).write_text(rendered, encoding="utf-8")
    except Exception as exc:
        parser.exit(2, f"eureka-decision-sequences: {exc}\n")


if __name__ == "__main__":
    main()

