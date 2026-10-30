"""Keep the review evidence checkable without treating it as owner approval."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE = ROOT / ".planning/phases/02.1-opportunity-hub-in-the-mos-brand-format"
EVIDENCE = PHASE / "evidence"
RECORD = ROOT / "docs/brand/hub-review-result.md"
RUN = ROOT / ".mindrian/runs/2b4aa394-981c-48b4-9328-33eee4dd2375"


def test_raw_reviews_require_owner_review_without_findings() -> None:
    files = sorted((EVIDENCE / "review").glob("*.json"))
    assert {path.stem for path in files} == {
        "hub", "bank", "graph", "catalogue", "panel-record", "panel-pair", "locked"}
    for path in files:
        review = json.loads(path.read_text())
        assert review["status"] == "REVIEW-REQUIRED" and review["exit_code"] == 2
        assert review["findings"] == []


def test_record_has_checks_limits_and_every_inspected_image() -> None:
    text = RECORD.read_text()
    for heading in ("Status", "Commands run", "Review results", "Measurements",
                    "Screenshot inspection", "Browser results", "Not verified here",
                    "Open items for the owner"):
        assert f"## {heading}\n" in text
    assert "visual verification pending the owner" in text or "approved by" in text
    limits = text.split("## Not verified here")[1].split("## Open items")[0]
    for phrase in ("Screen reader", "Safari", "touch and pinch", "five widths",
                   "read aloud", "right-to-left"):
        assert phrase in limits
    for path in (EVIDENCE / "screens").glob("*.jpg"):
        assert path.name in text
    for path in (RECORD, ROOT / "docs/brand/hub-design-decisions.md",
                 RUN / "04-return-learning/output/silent-items.md"):
        assert not re.search("[\u2013\u2014]", path.read_text())


def test_evidence_inventory_matches_files_and_budget() -> None:
    inventory = json.loads((EVIDENCE / "data/files.json").read_text())
    screens = list((EVIDENCE / "screens").glob("*.jpg"))
    assert len(screens) == 37
    total = sum(path.stat().st_size for path in screens)
    assert total == inventory["screens_total_bytes"] < 6_000_000
    for entry in inventory["files"]:
        path = ROOT / entry["path"]
        assert path.stat().st_size == entry["bytes"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]


def test_decision_and_review_links_resolve() -> None:
    for path in (RECORD, ROOT / "docs/brand/hub-design-decisions.md"):
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text()):
            if not target.startswith(("https:", "http:")):
                assert (path.parent / target.split("#", 1)[0]).exists(), target


def test_learning_and_unapproved_stage_outputs_exist() -> None:
    text = (RUN / "04-return-learning/output/silent-items.md").read_text()
    assert set(re.findall(r"^(\d+)\. ", text, re.M)) == {str(n) for n in range(1, 19)}
    for phrase in ("particles", "Instant camera", "13 px"):
        assert phrase in text
    status = json.loads((RUN / "status.json").read_text())
    assert status["current"] == "01-brief"
    assert status["status"] == "awaiting-output-and-review"
    for stage in ("01-brief", "02-produce", "03-review", "04-return-learning"):
        assert any(path.stat().st_size for path in (RUN / stage / "output").iterdir())
    assert not list(RUN.rglob("approval.json"))


def test_public_projections_preserve_source_identity_and_scores() -> None:
    source = ROOT / "tests/fixtures/hub_public/run/manifest.json"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    for count in (1, 12):
        data = json.loads((EVIDENCE / f"data/public-subset-{count}.json").read_text())
        assert data["source_manifest_sha256"] == digest
        assert len(data["records"]) == count
        assert data["scores_recomputed"] is False and data["cutoffs_changed"] is False
        assert "no model run or finding" in data["purpose"]
