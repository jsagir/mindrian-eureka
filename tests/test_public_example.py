"""Tests of the shipped public example: hash file, license, reference run, drift guard, README.

These tests need no model and no network. The full real-model check is opt-in and lives in
tests/test_public_example_fresh.py.
"""

from __future__ import annotations

import getpass
import hashlib
import importlib.util
import json
import re
import shutil
from pathlib import Path

import pytest
from mindrian_eureka.cli import main
from mindrian_eureka.example.check import check_run, load_expected
from mindrian_eureka.example.contracts import (
    ENGINE_SOURCE_FILES,
    EXAMPLE_COMMAND,
    EXAMPLE_ID,
    EXAMPLE_LICENSE,
    EXAMPLE_MODEL_NOTE,
    OUTPUT_FILES,
    RESULT_MATCH,
    RESULT_MATCH_ID,
)
from mindrian_eureka.run.engines import wording_params_hash
from test_release_gate_record import parse_front_matter

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/public-example"
EXPECTED = EXAMPLE / "expected-hashes.json"
REFERENCE = EXAMPLE / "reference-run"
README = EXAMPLE / "README.md"
HUB_FIXTURE = ROOT / "tests/fixtures/hub_public"
RELEASE_RECORD = ROOT / "docs/rs-release-gate.md"

README_HEADINGS = [
    "# Public example: 36 arXiv abstracts",
    "## Status",
    "## What the data is",
    "## Run it",
    "## What you should see",
    "## Where it was checked",
    "## Files in this folder",
    "## Notes for the maintainer",
]

DRIFT_MESSAGE = (
    "The engine changed after the expected hashes were made. Steps: (1) run the gated test with "
    "EUREKA_EXAMPLE_REAL_RUN=1 uv run --offline --with pytest python -m pytest "
    "tests/test_public_example_fresh.py -q -p no:cacheprovider; (2) if the outputs changed, "
    "rebuild with scripts/make-example-hashes (absolute paths), replace "
    "examples/public-example/reference-run, and record why in the commit message."
)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected() -> dict:
    return load_expected(EXPECTED)


def test_expected_file_loads_and_describes_the_dataset() -> None:
    document = expected()
    example = document["example"]
    assert example["id"] == EXAMPLE_ID
    assert example["records"] == 36
    assert (ROOT / example["input_folder"]).is_dir()
    assert (ROOT / example["license_record"]).is_file()
    assert document["command"] == EXAMPLE_COMMAND
    assert example["model_note"] == EXAMPLE_MODEL_NOTE
    assert "all-MiniLM-L6-v2" in example["model_note"]
    assert "mdbr-leaf-ir" in example["model_note"]
    assert document["model"]["name"] == "sentence-transformers/all-MiniLM-L6-v2"


def test_license_record_supports_the_example() -> None:
    document = expected()
    record = (ROOT / document["example"]["license_record"]).read_text()
    assert "Creative Commons CC0 1.0 Universal" in record
    assert "https://info.arxiv.org/help/license/index.html" in record
    assert "Retrieval date: 2026-10-24" in record
    assert document["example"]["license"] == EXAMPLE_LICENSE
    assert EXAMPLE_LICENSE in record or "CC0 1.0 Universal" in record


def test_input_hashes_equal_the_files_on_disk() -> None:
    document = expected()
    folder = ROOT / document["example"]["input_folder"]
    on_disk = sorted(p.name for p in folder.glob("*.md"))
    listed = sorted(entry["path"] for entry in document["inputs"]["files"])
    assert len(on_disk) == 36
    assert listed == on_disk
    for entry in document["inputs"]["files"]:
        assert entry["sha256"] == sha256_of(folder / entry["path"]), entry["path"]


def test_reference_run_matches_the_expected_file(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    report = check_run(REFERENCE, expected())
    assert report.result == RESULT_MATCH_ID
    monkeypatch.chdir(ROOT)
    code = main(["check-example", str(REFERENCE)])
    out = capsys.readouterr().out
    assert code == 0
    assert RESULT_MATCH in out


def test_reference_run_has_exactly_five_files() -> None:
    files = sorted(p.relative_to(REFERENCE).as_posix() for p in REFERENCE.rglob("*") if p.is_file())
    assert files == sorted([*OUTPUT_FILES, "manifest.json"])
    assert len(files) == 5


def test_reference_run_has_no_run_info() -> None:
    assert not (REFERENCE / "run-info.json").exists()


def test_one_changed_byte_fails_the_shipped_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    copy = tmp_path / "run"
    shutil.copytree(REFERENCE, copy)
    target = copy / "unusual-pairs.json"
    data = bytearray(target.read_bytes())
    data[len(data) // 2] ^= 0x01
    target.write_bytes(bytes(data))
    monkeypatch.chdir(ROOT)
    assert main(["check-example", str(copy)]) == 1
    assert "unusual-pairs.json" in capsys.readouterr().out


def module_file(module: str) -> Path:
    spec = importlib.util.find_spec(module)
    assert spec is not None and spec.origin is not None
    return Path(spec.origin)


def test_engine_identity_is_current() -> None:
    document = expected()
    wording = document["engine"]["engines"]["wording_and_meaning"]
    assert wording["params_hash"] == wording_params_hash(200), DRIFT_MESSAGE
    reference_file = module_file("mindrian_eureka.hsi_reference")
    assert wording["reference_sha256"] == sha256_of(reference_file), DRIFT_MESSAGE
    assert sorted(document["engine_sources"]) == sorted(ENGINE_SOURCE_FILES)
    for relative, digest in document["engine_sources"].items():
        assert digest == sha256_of(ROOT / relative), f"{relative}: {DRIFT_MESSAGE}"


def test_not_the_frozen_hub_run() -> None:
    document = expected()
    frozen = json.loads((HUB_FIXTURE / "run/manifest.json").read_text())
    frozen_hash = json.dumps(frozen).count("7affae3c94c6bed9")
    assert frozen_hash >= 1
    assert document["engine"]["engines"]["wording_and_meaning"]["params_hash"] != "7affae3c94c6bed9"
    assert (REFERENCE / "manifest.json").read_bytes() != (
        HUB_FIXTURE / "run/manifest.json"
    ).read_bytes()


def test_shipped_files_have_no_private_data() -> None:
    record = parse_front_matter(RELEASE_RECORD.read_text())
    decided_by = record["decided_by"]
    name = re.sub(r"\s*\(.*?\)\s*", " ", decided_by).strip()
    forbidden = [str(Path.home()), getpass.getuser(), "/tmp/", decided_by, name, name.split()[-1]]
    assert all(forbidden)
    files = [p for p in EXAMPLE.rglob("*") if p.is_file()]
    assert files
    for path in files:
        text = path.read_text()
        for value in forbidden:
            assert value not in text, f"{path}: contains a private value"
        assert not re.search(r"(?<![A-Za-z])[A-Za-z]:[\\/]", text), path
        assert not re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text), path


def test_size_under_two_megabytes() -> None:
    total = sum(p.stat().st_size for p in EXAMPLE.rglob("*") if p.is_file())
    assert total < 2_000_000


def headings(text: str) -> list[str]:
    in_code = False
    found: list[str] = []
    for line in text.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        elif not in_code and re.match(r"#{1,2} ", line):
            found.append(line)
    return found


def table_after(text: str, heading: str) -> list[str]:
    section = text.split(heading, 1)[1]
    rows: list[str] = []
    for line in section.splitlines()[1:]:
        if line.startswith("## "):
            break
        if line.startswith("|"):
            rows.append(line)
    return rows


def test_readme_structure_and_wording() -> None:
    text = README.read_text()
    assert headings(text) == README_HEADINGS
    assert text.count("candidate, not verified") >= 3
    assert "–" not in text and "—" not in text
    assert not re.search(r"\bRS\b", text)
    assert not re.search(r"\bHSI\b", text)
    assert "Internal only" in text
    assert "docs/rs-release-gate.md" in text
    # Review item 4 (plan 04.1-03): say what MATCH proves, and what it does not.
    assert "MATCH shows that the output bytes are the shipped ones. It does not prove that the run was made on this machine." in text
    assert "Extra files in the folder are ignored." in text
    status = text.split("## Status", 1)[1].split("## ", 1)[0]
    assert "Internal only." in status
    for target in re.findall(r"\]\(([^)#]+)\)", text):
        if "://" in target:
            continue
        assert (README.parent / target).exists(), target
    rows = table_after(text, "## Where it was checked")
    assert rows[0].startswith("| Setup")
    assert len(rows) - 2 >= 3
