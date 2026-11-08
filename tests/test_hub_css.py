"""Keep all authored hub styles within the approved book rules."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from mindrian_eureka.hub.contracts import DIM_COLOR, NEIGHBORHOOD_TINTS

AUTHORED = Path(__file__).resolve().parents[1] / 'src/mindrian_eureka/hub/assets/authored'
COLORS = {"#f7f5ee", "#ffffff", "#fff", "#111111", "#4b4943", "#1f3fbf", "#d6281f",
          "#f2c200", "#eceae2", DIM_COLOR.lower(), *(c.lower() for c in NEIGHBORHOOD_TINTS)}
# The dark token set of plan 02.3.1-05 (a proposal, docs/brand/hub-theme-rules.md). These values
# are allowed only in the theme sheet, only as the value of a custom property, and only inside
# a rule whose selector names the dark theme or inside the dark colour-scheme media block.
THEME_SHEET = "hub-theme.css"
DARK_COLORS = {"#121210", "#1b1a17", "#22211d", "#f4f2ea", "#b8b5aa", "#3a3833", "#8fa2ff",
               "#ff7468", "#4b4943"}
DARK_MEDIA = "@media (prefers-color-scheme: dark)"
DARK_SELECTOR = 'data-theme="dark"'
TOKEN_VALUE = re.compile(r"--[a-z0-9-]+\s*:\s*#[0-9a-fA-F]{3,8}\s*;?")
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")


def _strip_rules(text: str, dark_scope: bool) -> str:
    """Remove dark token declarations from the rules of the dark theme in `text`."""
    def rule(match: re.Match[str]) -> str:
        selector, declarations = match.group(1), match.group(2)
        if dark_scope or DARK_SELECTOR in selector:
            declarations = TOKEN_VALUE.sub(
                lambda m: "" if _hex(m.group(0)) in DARK_COLORS else m.group(0), declarations
            )
        return selector + "{" + declarations + "}"
    return RULE.sub(rule, text)


def _hex(declaration: str) -> str:
    return re.search(r"#[0-9a-fA-F]{3,8}", declaration).group(0).lower()


def without_dark_tokens(clean: str) -> str:
    """Return the theme sheet without the dark token values that the plan allows."""
    parts: list[str] = []
    index = 0
    while True:
        start = clean.find(DARK_MEDIA, index)
        if start == -1:
            parts.append(_strip_rules(clean[index:], False))
            return "".join(parts)
        opening = clean.index("{", start)
        depth = 0
        end = opening
        for end in range(opening, len(clean)):
            depth += clean[end] == "{"
            depth -= clean[end] == "}"
            if depth == 0:
                break
        parts.append(_strip_rules(clean[index:opening + 1], False))
        parts.append(_strip_rules(clean[opening + 1:end], True))
        parts.append("}")
        index = end + 1


def css_problems(text: str, name: str = "") -> list[str]:
    clean = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    if name == THEME_SHEET:
        clean = without_dark_tokens(clean)
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
                                 "prefers-reduced-motion: reduce", "prefers-color-scheme: dark"}:
            problems.append("media query")
    return problems


@pytest.mark.parametrize("path", sorted(AUTHORED.glob("hub*.css")), ids=lambda p: p.name)
def test_all_styles(path: Path) -> None:
    assert css_problems(path.read_text(), path.name) == []


def test_theme_sheet_exists_and_is_checked() -> None:
    assert (AUTHORED / THEME_SHEET).is_file()
    assert THEME_SHEET in {path.name for path in AUTHORED.glob("hub*.css")}


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


DARK_BLOCK = (
    ':root[data-theme="dark"] { color-scheme: dark; --mos-paper: #121210; --mos-ink: #F4F2EA; }'
)
DARK_MEDIA_BLOCK = (
    '@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) '
    "{ --mos-paper: #121210; } .hub-x { color: var(--mos-ink); } }"
)


@pytest.mark.parametrize(
    "good", [DARK_BLOCK, DARK_MEDIA_BLOCK, DARK_BLOCK + "\n" + DARK_MEDIA_BLOCK]
)
def test_dark_tokens_pass_only_in_the_theme_sheet(good: str) -> None:
    assert css_problems(good, THEME_SHEET) == []
    assert css_problems(good, "hub.css"), "a dark value in another sheet must fail"
    assert css_problems(good), "a dark value with no file name must fail"


@pytest.mark.parametrize("bad", [
    ':root[data-theme="dark"] { color: #121210; }',
    ':root[data-theme="dark"] .hub-band { background: #1B1A17; }',
    ':root { --mos-paper: #121210; }',
    '@media (max-width: 600px) { .hub-x { color: var(--mos-ink); } }',
    '@media (prefers-color-scheme: light) { :root { --mos-paper: #F7F5EE; } }',
    '@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { color: #F4F2EA; } }',
])
def test_theme_sheet_negative_controls(bad: str) -> None:
    assert css_problems(bad, THEME_SHEET)
