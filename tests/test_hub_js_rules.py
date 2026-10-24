"""Apply DOM safety, local-loading and classic-script rules to every authored script."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from hub_scan import scan_for_network

AUTHORED = Path(__file__).resolve().parents[1] / 'src/mindrian_eureka/hub/assets/authored'
FORBIDDEN = re.compile(
    r"\b(?:innerHTML|outerHTML|insertAdjacentHTML|localStorage|sessionStorage|"
    r"indexedDB|postMessage)\b|\beval\s*\(|document\s*\.\s*(?:write|cookie)|new\s+Function\b|"
    r"window\s*\.\s*open\s*\(|(?:setTimeout|setInterval)\s*\(\s*['\"]"
)


def js_problems(text: str, boot: bool = False) -> list[str]:
    problems = []
    if FORBIDDEN.search(text):
        problems.append("forbidden API")
    if re.search(r"^\s*(?:import|export)\s", text, re.M):
        problems.append("module syntax")
    if not boot:
        if not re.match(r'^\s*\(function\s*\(\)\s*\{\s*"use strict";', text):
            problems.append("strict IIFE")
        if not text.rstrip().endswith("})();"):
            problems.append("IIFE closure")
    return problems


@pytest.mark.parametrize("path", sorted(AUTHORED.glob("*.js")), ids=lambda p: p.name)
def test_all_scripts(path: Path) -> None:
    assert js_problems(path.read_text(), boot=path.name == "hub-boot.js") == []
    subprocess.run(["node", "--check", str(path)], check=True, capture_output=True)


def test_authored_scripts_make_no_network_call() -> None:
    assert scan_for_network(AUTHORED) == []


@pytest.mark.parametrize("body", ['node.innerHTML = text', 'eval("x")',
                                   'window.open("x")', 'localStorage.setItem("x", "y")',
                                   'setTimeout("x", 0)', 'export const x = 1'])
def test_negative_api_controls(body: str) -> None:
    assert js_problems('(function () { "use strict";\n' + body + '\n})();')
