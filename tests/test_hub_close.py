"""Keep page order, policy, records and distribution assets in agreement."""

from __future__ import annotations

import fnmatch
import re
import tomllib
from pathlib import Path

from mindrian_eureka.hub import page

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src/mindrian_eureka"
AUTHORED = PACKAGE / "hub/assets/authored"
RECORD_FILES = (
    "hub-model-rules.md", "hub-probe-results.md", "hub-vendor-record.md",
    "hub-gate-record.md", "hub-jhtv-view-mapping.md",
)


def test_script_and_style_order_are_complete() -> None:
    generated = {"hub-copy.js", "hub-data.js", "tokens.css"}
    ordered = set(page.SCRIPT_ORDER) | set(page.STYLE_ORDER)
    for name in ordered - generated:
        assert (AUTHORED / name).is_file(), name
    actual = {path.name for path in AUTHORED.glob("*") if path.suffix in {".js", ".css"}}
    assert actual == (ordered - generated) | {"hub-boot.js"}
    assert len(page.SCRIPT_ORDER) == len(set(page.SCRIPT_ORDER))
    assert len(page.STYLE_ORDER) == len(set(page.STYLE_ORDER))


def test_csp_record_and_constant_agree() -> None:
    text = (ROOT / "docs/brand/hub-probe-results.md").read_text()
    assert re.findall(r"^CSP decision: (.+)$", text, re.M) == [page.CONTENT_SECURITY_POLICY]


def test_record_files_exist_and_decisions_link_them() -> None:
    decisions = (ROOT / "docs/brand/hub-design-decisions.md").read_text()
    for name in RECORD_FILES:
        assert (ROOT / "docs/brand" / name).is_file()
        assert name in decisions


def test_package_data_covers_every_authored_file() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    patterns = config["tool"]["setuptools"]["package-data"]["mindrian_eureka"]
    for path in AUTHORED.iterdir():
        if path.is_file():
            relative = path.relative_to(PACKAGE).as_posix()
            assert any(fnmatch.fnmatchcase(relative, pattern) for pattern in patterns), relative
    assert "--password-env" in (ROOT / "README.md").read_text()
