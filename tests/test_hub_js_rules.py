"""Apply DOM safety, local-loading and classic-script rules to every authored script."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from hub_scan import scan_for_network

AUTHORED = Path(__file__).resolve().parents[1] / 'src/mindrian_eureka/hub/assets/authored'
FORBIDDEN = re.compile(
    r"\b(?:innerHTML|outerHTML|insertAdjacentHTML|sessionStorage|"
    r"indexedDB|postMessage)\b|\beval\s*\(|document\s*\.\s*(?:write|cookie)|new\s+Function\b|"
    r"window\s*\.\s*open\s*\(|(?:setTimeout|setInterval)\s*\(\s*['\"]"
)
STORAGE = re.compile(r"\blocalStorage\b")
# Plan 02.3.1-05: the theme choice is the only storage use of the hub. Two files may call
# localStorage, with one key and two values, and every call sits inside a try block.
STORAGE_FILES = {"hub-boot.js", "hub-theme.js"}
STORAGE_KEY = "hub-theme"
STORAGE_CALL = re.compile(
    r'\.(getItem|setItem)\(\s*"' + STORAGE_KEY + r'"\s*'
    r'(?:,\s*([A-Za-z_$][\w$]*|"dark"|"light")\s*)?\)'
)
THEME_LITERAL = r'"(?:dark|light)"'
THEME_VALUE = re.compile(
    r"(?:[^?;]*\?\s*)?" + THEME_LITERAL + r"(?:\s*:\s*" + THEME_LITERAL + r")?"
)


def _inside_try(text: str, position: int) -> bool:
    """Return True when `position` sits inside a `try {` block of `text`."""
    stack: list[bool] = []
    for index, char in enumerate(text[:position]):
        if char == "{":
            stack.append(bool(re.search(r"\btry\s*$", text[:index])))
        elif char == "}" and stack:
            stack.pop()
    return any(stack)


def _assignments(text: str, name: str) -> list[str]:
    pattern = r"\b" + re.escape(name) + r"\s*(?<![=!<>])=(?!=)\s*([^;]+);"
    return [value.strip() for value in re.findall(pattern, text)]


def storage_problems(text: str) -> list[str]:
    """Return every storage use that is not the theme key inside a try block."""
    problems = []
    for match in STORAGE.finditer(text):
        call = STORAGE_CALL.match(text, match.end())
        if call is None or (call.group(1) == "setItem") != (call.group(2) is not None):
            problems.append("storage call")
            continue
        value = call.group(2)
        if value is not None and not re.fullmatch(THEME_LITERAL, value):
            assigned = _assignments(text, value)
            if not assigned or not all(THEME_VALUE.fullmatch(item) for item in assigned):
                problems.append("storage value")
        if not _inside_try(text, match.start()):
            problems.append("storage outside try")
    return problems


def js_problems(text: str, boot: bool = False, name: str = "") -> list[str]:
    problems = []
    if FORBIDDEN.search(text):
        problems.append("forbidden API")
    if name in STORAGE_FILES:
        problems.extend(storage_problems(text))
    elif STORAGE.search(text):
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
    assert js_problems(path.read_text(), boot=path.name == "hub-boot.js", name=path.name) == []
    subprocess.run(["node", "--check", str(path)], check=True, capture_output=True)


def test_theme_scripts_exist_and_use_storage_inside_try() -> None:
    for name in STORAGE_FILES:
        text = (AUTHORED / name).read_text()
        assert STORAGE.search(text), f"{name} must read or write the theme key"
        assert storage_problems(text) == []


def test_authored_scripts_make_no_network_call() -> None:
    assert scan_for_network(AUTHORED) == []


@pytest.mark.parametrize("body", ['node.innerHTML = text', 'eval("x")',
                                   'window.open("x")', 'localStorage.setItem("x", "y")',
                                   'setTimeout("x", 0)', 'export const x = 1'])
def test_negative_api_controls(body: str) -> None:
    assert js_problems('(function () { "use strict";\n' + body + '\n})();')


def _theme_script(body: str) -> str:
    return '(function () { "use strict";\n' + body + '\n})();'


GOOD_STORAGE = [
    'try { var saved = localStorage.getItem("hub-theme"); } catch (error) { saved = null; }',
    'var next = dark ? "light" : "dark";\ntry { localStorage.setItem("hub-theme", next); } '
    'catch (error) { saved = null; }',
    'try { localStorage.setItem("hub-theme", "dark"); } catch (error) { return; }',
]
BAD_STORAGE = [
    'try { localStorage.getItem("other"); } catch (error) { return; }',
    'try { localStorage.setItem("hub-theme", payload); } catch (error) { return; }',
    'var next = payload.theme;\ntry { localStorage.setItem("hub-theme", next); } '
    'catch (error) { return; }',
    'localStorage.getItem("hub-theme");',
    'try { localStorage.setItem("hub-theme"); } catch (error) { return; }',
    'try { localStorage.getItem("hub-theme", "dark"); } catch (error) { return; }',
    'try { localStorage.clear(); } catch (error) { return; }',
    'try { window["localStorage"].setItem("hub-theme", "dark"); } catch (error) { return; }',
]


@pytest.mark.parametrize("body", GOOD_STORAGE)
def test_theme_storage_positive_controls(body: str) -> None:
    assert js_problems(_theme_script(body), name="hub-theme.js") == []
    assert js_problems(body, boot=True, name="hub-boot.js") == []


@pytest.mark.parametrize("body", BAD_STORAGE)
def test_theme_storage_negative_controls(body: str) -> None:
    assert js_problems(_theme_script(body), name="hub-theme.js")


def test_theme_key_is_banned_in_every_other_script() -> None:
    body = 'try { localStorage.getItem("hub-theme"); } catch (error) { return; }'
    assert js_problems(_theme_script(body), name="hub-bank.js") == ["forbidden API"]
    assert js_problems(_theme_script(body)) == ["forbidden API"]
