"""Helpers shared by the host-run tests. This module holds no test."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FIXTURE_CORPUS = FIXTURES / "rs_parity" / "corpus.json"
FROZEN_RUN = FIXTURES / "hub_public" / "run"
SCHEMA_DIR = Path(__file__).resolve().parents[1] / "src" / "mindrian_eureka" / "data" / "schemas"


def make_request(count: int = 32, **overrides: Any) -> dict[str, Any]:
    """Build a host request from the first `count` synthetic fixture artifacts.

    Args:
        count: How many artifacts to take from the fixture (1 to 32).
        **overrides: Top-level keys that replace the defaults.

    Returns:
        A request dictionary with the keys `objective`, `scope_id`, `snapshot_id`,
        `top_k` and `artifacts`.
    """
    data = json.loads(FIXTURE_CORPUS.read_text(encoding="utf-8"))
    artifacts = [
        {
            "id": item["id"],
            "source_ref": item["source_ref"],
            "title": item["title"],
            "text": item["text"],
        }
        for item in data["artifacts"][:count]
    ]
    request: dict[str, Any] = {
        "objective": "Find unusual pairs in the synthetic set",
        "scope_id": "room:test-scope",
        "snapshot_id": "snapshot:test-1",
        "top_k": 15,
        "artifacts": artifacts,
    }
    request.update(overrides)
    return request
