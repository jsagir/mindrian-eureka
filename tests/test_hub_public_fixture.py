"""Validate the licensed public fixture and its real run provenance."""

from __future__ import annotations

import getpass
import hashlib
import json
import re
from pathlib import Path

import pytest
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.hub.verify import verify_payload

FIXTURE = Path(__file__).parent / "fixtures/hub_public"
EXPECTED_RUN_FILES = {
    "corpus/records.jsonl",
    "unusual-pairs.json",
    "wording-and-meaning-pairs.json",
    "ranked-pairs.md",
    "manifest.json",
}


def test_license_statements_are_recorded_with_official_urls() -> None:
    text = (FIXTURE / "SOURCE.md").read_text()
    for phrase in (
        "## Source",
        "## License",
        "## What was changed",
        "## Selection rule",
        "## Documents",
        "## Frozen run",
        "CC0 1.0",
        "Retrieval date: 2026-10-24",
        "https://info.arxiv.org/help/license/index.html",
        "https://info.arxiv.org/help/policies/submission_agreement.html",
        '"Metadata includes title, author, abstract, and other information describing the Work."',
    ):
        assert phrase in text


def test_document_table_matches_all_inputs_and_six_subject_groups() -> None:
    text = (FIXTURE / "SOURCE.md").read_text()
    rows = [line.split("|") for line in text.splitlines() if line.startswith("| arxiv-")]
    files = {path.name for path in (FIXTURE / "input").glob("*.md")}
    assert len(files) == len(rows) == 36
    assert {row[1].strip() for row in rows} == files
    subjects = [row[5].strip() for row in rows]
    assert len(set(subjects)) == 6
    assert all(subjects.count(subject) == 6 for subject in set(subjects))
    for row in rows:
        assert row[3].strip() == "https://arxiv.org/abs/" + row[2].strip()


@pytest.mark.parametrize("path", sorted((FIXTURE / "input").glob("*.md")), ids=lambda p: p.name)
def test_input_has_only_title_metadata_and_clean_abstract_body(path: Path) -> None:
    text = path.read_text()
    lines = text.splitlines()
    assert lines[0] == "---" and lines[1].startswith("title: ") and lines[2] == "---"
    assert len("\n".join(lines[3:]).strip()) >= 50
    assert not re.search(r"\b(?:R[S]|H[S]I)\b", text)
    assert not any(char in text for char in (chr(8211), chr(8212)))
    assert "--" not in "\n".join(lines[3:])


def test_frozen_folder_has_exactly_the_expected_five_files() -> None:
    folder = FIXTURE / "run"
    assert {
        p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()
    } == EXPECTED_RUN_FILES


def test_input_hashes_match_the_manifest() -> None:
    manifest = json.loads((FIXTURE / "run/manifest.json").read_text())
    inputs = {row["path"]: row["sha256"] for row in manifest["inputs"]["files"]}
    assert set(inputs) == {path.name for path in (FIXTURE / "input").glob("*.md")}
    for name, digest in inputs.items():
        assert hashlib.sha256((FIXTURE / "input" / name).read_bytes()).hexdigest() == digest


def test_real_run_loads_and_earns_a_verified_graph_payload() -> None:
    run = load_run(FIXTURE / "run")
    assert len(run.records) == 36
    assert all(len(engine.pairs) > 0 for engine in run.engines.values())
    ids = {
        record_id
        for engine in run.engines.values()
        for pair in engine.pairs
        for record_id in (pair.left_id, pair.right_id)
    }
    assert len(ids) >= 15
    payload = build_payload(run)
    assert payload["graph"]["earned"]
    assert verify_payload(payload) == []
    manifest = json.loads((FIXTURE / "run/manifest.json").read_text())
    assert manifest["model"]["name"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert "model.safetensors" in manifest["model"]["files"]


def test_fixture_contains_no_local_paths_user_name_or_email() -> None:
    forbidden = [str(Path.home()), getpass.getuser(), "/tmp/"]
    for path in FIXTURE.rglob("*"):
        if path.is_file():
            text = path.read_text()
            assert all(value not in text for value in forbidden), path
            assert not re.search(r"(?<![A-Za-z])[A-Za-z]:[\\/]", text), path
            assert not re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text), path


def test_fixture_size_and_repeated_run_record() -> None:
    assert sum(p.stat().st_size for p in FIXTURE.rglob("*") if p.is_file()) < 2_000_000
    source = (FIXTURE / "SOURCE.md").read_text()
    assert (
        "second completed real-model run gave byte-identical files except run-info.json" in source
    )
    assert "Phase 4 owns the expected-hash check for a fresh checkout." in source
    digest = hashlib.sha256((FIXTURE / "run/manifest.json").read_bytes()).hexdigest()
    assert digest in source
