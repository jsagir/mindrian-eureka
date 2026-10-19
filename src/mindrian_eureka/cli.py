"""Top-level operator CLI for Mindrian Eureka."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent / "data"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="eureka",
        description="Inspect Mindrian Eureka capabilities and the MindrianOS host workflow.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("capabilities", help="list runnable, brokered, blocked, and planned capability jobs")
    show = commands.add_parser("capability", help="show one capability by its stable ID")
    show.add_argument("capability_id")
    schema = commands.add_parser("schema", help="show a packaged input/output schema for a capability")
    schema.add_argument("capability_id")
    schema.add_argument("--direction", choices=("input", "output", "both"), default="both")
    commands.add_parser("workflow", help="print the MindrianOS opportunity-discovery host contract")
    args = parser.parse_args()

    if args.command in ("capabilities", "capability", "schema"):
        document = json.loads((DATA_DIR / "capability-catalog.v1.json").read_text(encoding="utf-8"))
        if args.command in ("capability", "schema"):
            matches = [item for item in document["capabilities"] if item["id"] == args.capability_id]
            capability = matches[0] if matches else None
            if args.command == "capability":
                document = capability or {"status": "not_found", "capability_id": args.capability_id}
            elif capability is None:
                document = {"status": "not_found", "capability_id": args.capability_id}
            else:
                keys = ("input_schema", "output_schema") if args.direction == "both" else (f"{args.direction}_schema",)
                definitions = {}
                for key in keys:
                    relative = capability.get(key)
                    if not relative:
                        definitions[key] = {"status": "not_published"}
                        continue
                    path = (DATA_DIR / relative).resolve()
                    if not path.is_relative_to(DATA_DIR.resolve()):
                        definitions[key] = {"status": "invalid_catalog_path"}
                        continue
                    try:
                        definitions[key] = json.loads(path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError) as exc:
                        definitions[key] = {"status": "unavailable", "detail": str(exc)}
                document = {"capability_id": args.capability_id, "version": capability.get("version"),
                            "status": capability.get("status"), **definitions}
    else:
        document = json.loads((DATA_DIR / "mos-opportunity-discovery.v1.json").read_text(encoding="utf-8"))
    print(json.dumps(document, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
