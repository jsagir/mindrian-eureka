"""CLI for the durable RS + HSI local opportunity-signal scout."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from .opportunity_pairs.jobs import JobManager
from .contracts import validate_request, validate_result


def main() -> None:
    parser = argparse.ArgumentParser(prog="eureka-signal-scout", description="Find cross-domain pair leads with RS and HSI over one prepared local snapshot.")
    parser.add_argument("input", help="JSON bundle with objective, scope_id, and source-linked artifacts")
    parser.add_argument("--output", default="-", help="Result JSON path, or - for stdout")
    parser.add_argument("--data-dir", default=os.environ.get("MINDRIAN_EUREKA_DATA_DIR"), help="Local job/cache directory")
    args = parser.parse_args()
    try:
        path = Path(args.input)
        if path.stat().st_size > 24 * 1024 * 1024:
            raise ValueError("Input bundle exceeds 24 MiB")
        request = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(request, dict):
            raise ValueError("Input must contain a JSON object")
        validate_request("opportunity.synthesize_discovery_signals", request)
        request.update({
            "capability_id": "opportunity.synthesize_discovery_signals",
            "mode": "local",
            "encoder": os.environ.get("MINDRIAN_EUREKA_RS_ENCODER", "sentence-transformers"),
            "model_path": os.environ.get("MINDRIAN_EUREKA_RS_MODEL_PATH", "sentence-transformers/all-MiniLM-L6-v2"),
            "model_revision": os.environ.get("MINDRIAN_EUREKA_RS_MODEL_REVISION") or None,
        })
        manager = JobManager(args.data_dir)
        started = manager.start(request)
        job_id = started["job_id"]
        while True:
            status = manager.status(job_id)
            if status["status"] in {"completed", "completed_empty", "failed", "blocked", "cancelled", "expired"}:
                break
            time.sleep(0.25)
        result = manager.result(job_id)
        if result.get("capability_id"):
            validate_result(result["capability_id"], result)
        if args.output == "-":
            sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        else:
            Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if status["status"] in {"failed", "blocked", "cancelled"}:
            raise RuntimeError(f"Scout job ended with status {status['status']}")
    except Exception as exc:
        parser.exit(2, f"eureka-signal-scout: {exc}\n")


if __name__ == "__main__":
    main()
