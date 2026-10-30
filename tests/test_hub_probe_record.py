"""Structure and fact checks of docs/brand/hub-probe-results.md.

The record answers the UNVERIFIED items of the hub UI-SPEC. These tests do not need a browser.
The browser measurements are repeated in tests/test_hub_browser_probe.py.
"""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest
from conftest import InputSet
from mindrian_eureka.cli import main
from mindrian_eureka.run.output import OUTPUT_MANIFEST

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "docs" / "brand" / "hub-probe-results.md"
SECTIONS = (
    "Headless browser tool",
    "WebCrypto on file URLs",
    "CSP on file URLs",
    "WebGL in headless browsers",
    "3d-force-graph (npm)",
    "Crypto library dependency",
    "Safari (WebKit)",
    "Engine cut-offs in the manifest",
)
MIN_PIN_AGE_DAYS = 14


@pytest.fixture(scope="module")
def text() -> str:
    return RECORD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def sections(text: str) -> dict[str, str]:
    parts = re.split(r"^## (.+)$", text, flags=re.M)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def test_every_section_has_a_result_line_and_a_fallback_line(sections: dict[str, str]) -> None:
    for name in SECTIONS:
        assert name in sections, f"missing section: {name}"
        body = sections[name]
        assert re.search(r"^Result: \S", body, re.M), f"{name}: no Result line"
        assert re.search(r"^Fallback: \S", body, re.M), f"{name}: no Fallback line"


def test_the_record_has_exactly_one_csp_decision_line(text: str, sections: dict[str, str]) -> None:
    assert len(re.findall(r"^CSP decision:", text, re.M)) == 1
    assert re.search(r"^CSP decision: \S", sections["CSP on file URLs"], re.M)


def test_the_record_has_no_dash_characters(text: str) -> None:
    assert "–" not in text
    assert "—" not in text


def test_the_pin_section_holds_the_integrity_string_the_date_and_a_passing_age(
    sections: dict[str, str],
) -> None:
    body = sections["3d-force-graph (npm)"]
    assert re.search(r"sha512-[A-Za-z0-9+/]{80,}={0,2}", body)
    assert "3d-force-graph@1.79.1" in body
    assert "MIT" in body
    published = re.search(r"\| Published \| (\d{4}-\d{2}-\d{2})", body)
    recorded = re.search(r"\| Age on (\d{4}-\d{2}-\d{2}) \| (\d+) days", body)
    assert published and recorded
    days = (date.fromisoformat(recorded.group(1)) - date.fromisoformat(published.group(1))).days
    assert days == int(recorded.group(2))
    assert days >= MIN_PIN_AGE_DAYS


def test_the_crypto_section_matches_the_repository(sections: dict[str, str]) -> None:
    body = sections["Crypto library dependency"]
    assert "NOT a base dependency" in body
    assert "hub-gate" in body
    assert "uv sync --extra hub-gate" in body
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    base = project["project"]["dependencies"]
    assert not any(item.lower().startswith("cryptography") for item in base)
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    dependents: set[str] = set()
    for package in lock["package"]:
        groups = [package.get("dependencies", [])]
        groups.extend(package.get("optional-dependencies", {}).values())
        if any(item["name"] == "cryptography" for group in groups for item in group):
            dependents.add(package["name"])
    assert "pyjwt" in dependents
    # Plan 06 may add the hub-gate extra, which adds the package itself to the set.
    assert dependents <= {"pyjwt", "mindrian-eureka"}


def test_the_safari_section_claims_nothing_it_did_not_run(sections: dict[str, str]) -> None:
    body = sections["Safari (WebKit)"]
    assert "not testable here" in body
    assert "plan 19" in body


def test_the_cut_off_keys_named_in_the_record_exist_in_a_stub_run_manifest(
    sections: dict[str, str],
    isolated_env: Path,
    stub_encoders: None,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
) -> None:
    inputs = tmp_inputs("markdown")
    out = tmp_path / "out"
    code = main(["run", str(inputs.folder), "--out", str(out), "--model-path", str(fake_model_dir)])
    assert code == 0
    manifest = json.loads((out / OUTPUT_MANIFEST).read_text(encoding="utf-8"))
    named = re.findall(
        r"`(settings\.[a-z_.]+)`: default (\d+\.\d+)", sections["Engine cut-offs in the manifest"]
    )
    keys = {key for key, _ in named}
    assert keys == {
        "settings.unusual_pairs.min_percentile",
        "settings.wording_and_meaning.min_percentile",
        "settings.wording_and_meaning.confirm_percentile",
    }
    for key, default in named:
        value: object = manifest
        for part in key.split("."):
            assert isinstance(value, dict) and part in value, f"{key} is not in the manifest"
            value = value[part]
        assert value == pytest.approx(float(default)), key
