"""Keep all authored hub styles within the approved book rules."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from mindrian_eureka.hub.contracts import DIM_COLOR, NEIGHBORHOOD_TINTS

AUTHORED = Path(__file__).resolve().parents[1] / 'src/mindrian_eureka/hub/assets/authored'
COLORS = {"#f7f5ee", "#ffffff", "#fff", "#111111", "#4b4943", "#1f3fbf", "#d6281f",
          "#f2c200", "#eceae2", DIM_COLOR.lower(), *(c.lower() for c in NEIGHBORHOOD_TINTS)}


def css_problems(text: str) -> list[str]:
    clean = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    problems = []
    for color in re.findall(r"#[0-9a-fA-F]{3,8}\b", clean):
        if color.lower() not in COLORS:
            problems.append("color " + color)
    if re.search(r"\b(?:rgb|rgba|hsl|hsla)\s*\(", clean, re.I):
        problems.append("functional color")
    for prop, value in re.findall(r"([a-z-]+)\s*:\s*([^;{}]+)", clean):
        if prop == "font-size":
            values = re.findall(r"([\d.]+)(px|rem|em)", value)
            if not values or min(float(n) * (1 if unit == "px" else 16) for n, unit in values) < 13:
                problems.append("font floor")
        if re.fullmatch(r"(?:margin|padding|border)-(?:left|right)(?:-.*)?|left|right|float", prop):
            problems.append("physical direction")
        if prop == "text-align" and value.strip() in {"left", "right"}:
            problems.append("physical alignment")
        if prop == "transition":
            for transition in value.split(","):
                if transition.strip().split()[0] not in {
                    "none", "color", "background-color", "border-color", "text-decoration-thickness"
                }:
                    problems.append("transition property")
        if prop in {"color", "background", "background-color", "border-color", "outline-color"}:
            words = re.sub(r"var\([^)]*\)|#[0-9a-fA-F]+", "", value).strip()
            if words and words.lower() not in {"transparent", "currentcolor", "inherit", "none"}:
                problems.append("named color")
    if re.search(r"@import|@keyframes|\banimation\s*:", clean):
        problems.append("import or ambient motion")
    if re.search(r"url\s*\(\s*['\"]?(?:[a-z]+:|//)", clean, re.I):
        problems.append("remote URL")
    for selector, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", clean):
        radii = re.findall(r"border-radius\s*:\s*([^;]+)", declarations)
        if "swatch" not in selector and any(value.strip() != "0" for value in radii):
            problems.append("rounded corner")
    if "!important" in clean:
        before_motion = clean.split("@media (prefers-reduced-motion: reduce)")[0]
        if "!important" in before_motion:
            problems.append("important")
    for query in re.findall(r"@media\s*\(([^)]+)\)", clean):
        if query.strip() not in {"min-width: 768px", "min-width: 1024px",
                                 "prefers-reduced-motion: reduce"}:
            problems.append("media query")
    return problems


@pytest.mark.parametrize("path", sorted(AUTHORED.glob("hub*.css")), ids=lambda p: p.name)
def test_all_styles(path: Path) -> None:
    assert css_problems(path.read_text()) == []


def test_shell_requirements() -> None:
    text = (AUTHORED / "hub.css").read_text()
    assert "font-synthesis: none" in text and "font-optical-sizing: auto" in text
    assert ":focus-visible { outline: 3px solid var(--mos-ink); outline-offset: 3px; }" in text
    assert "@media (prefers-reduced-motion: reduce)" in text
    floor_copy = ("Hub applies 13 px at all widths. The book fails only below 13 px at 1024 px "
                  "and up. Stricter by choice, proposed segment.")
    assert floor_copy in text
    for selector in (".hub-button", ".hub-field", "#hub-nav a"):
        declarations = re.search(re.escape(selector) + r"\s*\{([^}]+)", text).group(1)
        assert "min-block-size: 44px" in declarations
    assert not re.search(r"[^{}]*hub-quiet[^{}]*hub-flag[^{}]*\{", text)
    assert "Red flag text is never placed on a quiet fill" in text


@pytest.mark.parametrize("bad", ["font-size: 12px", "margin-left: 1px", "color: pink",
                                  "background: #123456", "animation: spin 1s",
                                  "transition: transform 200ms", "border-radius: 3px"])
def test_rule_negative_controls(bad: str) -> None:
    assert css_problems(".bad {" + bad + ";}")
