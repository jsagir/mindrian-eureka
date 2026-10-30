"""Reproduce the LATEST Genesis IP-finance lexicon check on the July 2026 JHTV CSV."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from mindrian_eureka.contracts import validate_request, validate_result
from mindrian_eureka.workflow_handlers import HANDLERS


EXPECTED_CSV_SHA256 = "efa77ea633dc800a10055eafbd279f98dc1149f42f738536b7808f621871ff5a"
CAPABILITY_ID = "research.classify_ip_finance_domain_signals"


def request_from_csv(path: Path) -> dict:
    csv_bytes = path.read_bytes()
    csv_hash = hashlib.sha256(csv_bytes).hexdigest()
    if csv_hash != EXPECTED_CSV_SHA256:
        raise ValueError(f"Unexpected JHTV CSV snapshot hash: {csv_hash}")
    segments = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            text = "\n".join(
                value.strip()
                for value in (
                    row.get("title", ""),
                    row.get("unmet_need", ""),
                    row.get("description_full") or row.get("value_prop") or row.get("tech_description") or "",
                    row.get("keywords", ""),
                )
                if value and value.strip()
            )
            segments.append({
                "id": row["case_id"] or row["tech_id"],
                "source_ref": row["url"] or f"jhtv-csv://technology/{row['tech_id']}",
                "text": text,
            })
    return {
        "scope_id": "room:jhtv-oliver-kuntz",
        "snapshot_id": f"sha256:{csv_hash}",
        "segments": segments,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path, help="July 2026 technologies-full-extract.csv")
    parser.add_argument("--output", required=True, type=Path, help="Path for the complete capability result JSON")
    args = parser.parse_args()

    request = request_from_csv(args.input)
    validate_request(CAPABILITY_ID, request)
    result = HANDLERS[CAPABILITY_ID](request)
    validate_result(CAPABILITY_ID, result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "capability_id": CAPABILITY_ID,
        "status": result["status"],
        "segments": len(result["segment_results"]),
        "warnings": len(result["warnings"]),
        "input_fingerprint": result["input_fingerprint"],
        "output": str(args.output),
    }))


if __name__ == "__main__":
    main()
