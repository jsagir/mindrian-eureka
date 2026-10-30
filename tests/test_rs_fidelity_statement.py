"""One fidelity phrase must appear on every surface where a reader looks first.

The phrase is "not verified bit-for-bit". The test reads repo files only. It runs
no engine, so no embedding cache is involved.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHRASE = "not verified bit-for-bit"
CAPABILITY_ID = "opportunity.find_cross_domain_pairs"
EM_DASH = chr(8212)

README = ROOT / "README.md"
PYPROJECT = ROOT / "pyproject.toml"
MANIFEST = ROOT / "capabilities" / CAPABILITY_ID / "manifest.json"
CATALOG = ROOT / "src" / "mindrian_eureka" / "data" / "capability-catalog.v1.json"
RUNNER = ROOT / "src" / "mindrian_eureka" / "opportunity_pairs" / "runner.py"
GUIDE = ROOT / "docs" / "engines" / "opportunity-pairs.md"
PARITY = ROOT / "docs" / "rs-engine-parity.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_readme_has_phrase_twice_and_links_the_three_records():
    text = _read(README)
    assert text.count(PHRASE) >= 2
    for link in ("rs-engine-parity.md", "rs-release-gate.md", "hsi-rs-jhtv-reproduction.md"):
        assert link in text, f"README lacks a link to {link}"


def test_readme_does_not_state_a_release_decision():
    section = _read(README).split("## Fidelity of the unusual-pairs engine", 1)[1].split("\n## ", 1)[0]
    lowered = section.lower()
    assert "no-go" not in lowered
    assert "decision: go" not in lowered


def test_pyproject_metadata():
    project = tomllib.loads(_read(PYPROJECT))["project"]
    assert project["readme"] == "README.md"
    assert PHRASE in project["description"]
    assert "license" not in project
    assert "license-files" not in project
    assert not any(item.startswith("License ::") for item in project.get("classifiers", []))


def test_manifest_limitations_have_phrase():
    manifest = json.loads(_read(MANIFEST))
    assert any(PHRASE in item for item in manifest["limitations"])


def test_catalog_entry_limitations_have_phrase():
    catalog = json.loads(_read(CATALOG))
    entry = next(item for item in catalog["capabilities"] if item["id"] == CAPABILITY_ID)
    assert any(PHRASE in item for item in entry["limitations"])


def test_runner_source_has_phrase():
    assert PHRASE in _read(RUNNER)


def test_guide_and_parity_record_have_phrase():
    assert PHRASE in _read(GUIDE)
    assert PHRASE in _read(PARITY)


def test_guide_lists_deviations_and_repo_wording():
    text = _read(GUIDE)
    for number in range(1, 10):
        assert f"| D{number} |" in text, f"deviation row D{number} missing"
    assert "not in this repo" in text
    assert "not present in this checkout" not in text


def test_changed_docs_have_no_em_dash():
    for path in (README, GUIDE, PARITY, MANIFEST, CATALOG):
        assert EM_DASH not in _read(path), f"em-dash in {path.name}"
