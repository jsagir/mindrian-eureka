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
    commands.add_parser("workflow", help="print the MindrianOS opportunity-discovery host contract")
    args = parser.parse_args()

    if args.command in ("capabilities", "capability"):
        document = json.loads((DATA_DIR / "capability-catalog.v1.json").read_text(encoding="utf-8"))
        if args.command == "capability":
            matches = [item for item in document["capabilities"] if item["id"] == args.capability_id]
            document = matches[0] if matches else {"status": "not_found", "capability_id": args.capability_id}
    else:
        document = json.loads((DATA_DIR / "mos-opportunity-discovery.v1.json").read_text(encoding="utf-8"))
    print(json.dumps(document, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
