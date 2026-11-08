"""Static checks of the light and dark theme (plan 02.3.1-05, HUB-10).

The dark values are a proposal (the book is silent on a dark page). This file pins the token
tables, the contrast of every pair the page uses in both themes, the sheet order, the system
default, the asset entry of the reverse lockup, the copy part and the record document.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import pytest
from mindrian_eureka.hub import assets, copy_theme, page
from mindrian_eureka.hub.assets import static_assets
from mindrian_eureka.hub.contracts import has_dash
from mindrian_eureka.hub.deck import DECK
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run

ROOT = Path(__file__).resolve().parents[1]
AUTHORED = ROOT / "src/mindrian_eureka/hub/assets/authored"
STATIC = ROOT / "src/mindrian_eureka/hub/assets/static"
THEME = AUTHORED / "hub-theme.css"
RECORD = ROOT / "docs/brand/hub-theme-rules.md"
PUBLIC = ROOT / "tests/fixtures/hub_public/run"
FILES = (
    {item.output_path for item in static_assets()}
    | set(page.STYLE_ORDER)
    | set(page.SCRIPT_ORDER)
    | {"hub-boot.js"}
)

REVERSE = "assets/brand/mos-lockup-reverse-v2.svg"
REVERSE_SHA = "3033e523efd4f78cafd1ed28fe311251e5f58454491c8aabd783bb456a99236b"
REVERSE_BYTES = 191114
REVERSE_SOURCE = "segments/identity/logo/variants/entries/2026-10-19/asset-aafc7b2563.svg"

COLOR_TOKENS = ("--mos-paper", "--mos-ink", "--mos-white", "--mos-soft", "--mos-blue",
                "--mos-red", "--mos-yellow", "--mos-quiet", "--mos-paper-dim",
                "--mos-ink-hairline")
HUB_TOKENS = ("--hub-line", "--hub-ring", "--hub-dim")
DARK_SELECTOR = ':root[data-theme="dark"]'
SYSTEM_SELECTOR = ':root:not([data-theme="light"])'
DARK_MEDIA = "prefers-color-scheme: dark"

# The plan's table (dark values are the prototype's proposal of 2026-11-08).
DARK_VALUES = {
    "--mos-paper": "#121210", "--mos-white": "#1B1A17", "--mos-quiet": "#22211D",
    "--mos-ink": "#F4F2EA", "--mos-soft": "#B8B5AA", "--mos-blue": "#8FA2FF",
    "--mos-red": "#FF7468", "--mos-yellow": "#F2C200", "--mos-paper-dim": "#4B4943",
    "--mos-ink-hairline": "#B8B5AA", "--hub-line": "#3A3833",
}

# Every text and graphic pair the page uses: (name, foreground by theme, background, floor).
# A floor of None means the pair is measured and reported only.
THEME_PAIRS = (
    ("ink on paper", "--mos-ink", "--mos-paper", 4.5),
    ("soft on paper", "--mos-soft", "--mos-paper", 4.5),
    ("cobalt on paper", "--mos-blue", "--mos-paper", 4.5),
    ("red on paper", "--mos-red", "--mos-paper", 4.5),
    ("ink on white", "--mos-ink", "--mos-white", 4.5),
    ("soft on white", "--mos-soft", "--mos-white", 4.5),
    ("cobalt on white", "--mos-blue", "--mos-white", 4.5),
    ("red on white", "--mos-red", "--mos-white", 4.5),
    ("ink on quiet", "--mos-ink", "--mos-quiet", 4.5),
    ("soft on quiet", "--mos-soft", "--mos-quiet", 4.5),
    ("cobalt on quiet", "--mos-blue", "--mos-quiet", 4.5),
    ("red on quiet", "--mos-red", "--mos-quiet", None),
    ("paper on ink (band)", "--mos-paper", "--mos-ink", 4.5),
    ("paper-dim on ink (band secondary)", "--mos-paper-dim", "--mos-ink", 4.5),
    ("text on yellow", {"light": "--mos-ink", "dark": "--mos-paper"}, "--mos-yellow", 4.5),
    ("focus ring on the band", {"light": "--mos-yellow", "dark": "--mos-paper"}, "--mos-ink", 3.0),
    ("line on paper", "--hub-line", "--mos-paper", None),
    ("ink-hairline on ink", "--mos-ink-hairline", "--mos-ink", None),
)
# The book report (light) and the prototype measurement of 2026-11-08 (dark), on paper.
EXPECTED = {
    "light": {"ink on paper": 17.31, "soft on paper": 8.25, "cobalt on paper": 7.63,
              "red on paper": 4.60},
    "dark": {"ink on paper": 16.73, "soft on paper": 9.13, "cobalt on paper": 7.84,
             "red on paper": 7.10},
}


def declarations(block: str) -> list[tuple[str, str]]:
    return [(prop.strip(), value.strip())
            for prop, value in re.findall(r"([a-zA-Z-]+)\s*:\s*([^;]+);?", block)]


def parse_rules(text: str) -> list[tuple[str, str, list[tuple[str, str]]]]:
    """Return (media query or empty, selector, declarations) for every rule of `text`."""
    clean = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    rules = []
    media = ""
    index = 0
    while True:
        opening = clean.find("{", index)
        if opening == -1:
            return rules
        head = clean[index:opening].strip()
        if head.startswith("@media"):
            media = head[len("@media"):].strip().strip("()").strip()
            index = opening + 1
            continue
        closing = clean.index("}", opening)
        rules.append((media, head, declarations(clean[opening + 1:closing])))
        index = closing + 1
        while clean[index:].lstrip().startswith("}"):
            media = ""
            index = clean.index("}", index) + 1


def token_table(theme: str) -> dict[str, str]:
    """Return the resolved tokens of a theme from tokens.css, hub.css and hub-theme.css."""
    table: dict[str, str] = {}
    for path in (STATIC / "tokens.css", AUTHORED / "hub.css", THEME):
        for media, selector, items in parse_rules(path.read_text(encoding="utf-8")):
            if selector == ":root" and not media:
                table.update((prop, value) for prop, value in items if prop.startswith("--"))
    if theme == "dark":
        for media, selector, items in parse_rules(THEME.read_text(encoding="utf-8")):
            if selector == DARK_SELECTOR and not media:
                table.update((prop, value) for prop, value in items if prop.startswith("--"))
    return table


def resolve(table: dict[str, str], value: str) -> str:
    seen = 0
    while value.startswith("var("):
        value = table[value[4:-1].strip()]
        seen += 1
        assert seen < 10, "token cycle"
    return value


def luminance(color: str) -> float:
    digits = color.lstrip("#")
    if len(digits) == 3:
        digits = "".join(char * 2 for char in digits)
    channels = [int(digits[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def ratio(front: str, back: str) -> float:
    one, two = luminance(front), luminance(back)
    return (max(one, two) + 0.05) / (min(one, two) + 0.05)


def contrast_table() -> dict[str, dict[str, tuple[str, str, float, float | None]]]:
    table = {}
    for theme in ("light", "dark"):
        tokens = token_table(theme)
        rows = {}
        for name, front, back, floor in THEME_PAIRS:
            front_token = front[theme] if isinstance(front, dict) else front
            fg = resolve(tokens, tokens[front_token]).upper()
            bg = resolve(tokens, tokens[back]).upper()
            rows[name] = (fg, bg, round(ratio(fg, bg), 2), floor)
        table[theme] = rows
    return table


def test_token_tables_and_contrast() -> None:
    table = contrast_table()
    print("\n| Theme | Pair | Text | Ground | Ratio | Floor |")
    for theme, rows in table.items():
        for name, (fg, bg, value, floor) in rows.items():
            print(f"| {theme} | {name} | {fg} | {bg} | {value:.2f} | {floor or 'report'} |")
    for theme, rows in table.items():
        for name, (fg, bg, value, floor) in rows.items():
            if floor is not None:
                assert value >= floor, (theme, name, fg, bg, value)
        for name, expected in EXPECTED[theme].items():
            assert rows[name][2] == pytest.approx(expected, abs=0.01), (theme, name, rows[name])
    light, dark = token_table("light"), token_table("dark")
    for token, value in DARK_VALUES.items():
        assert dark[token].upper() == value.upper(), token
    assert light["--mos-paper"].upper() == "#F7F5EE" and light["--mos-ink"] == "#111111"
    assert dark["--mos-yellow"].upper() == light["--mos-yellow"].upper() == "#F2C200"
    assert resolve(dark, dark["--hub-ring"]).upper() == "#F4F2EA"
    assert light["--hub-ring"] == "transparent"
    assert resolve(dark, dark["--hub-dim"]).upper() == "#3A3833"
    assert light["--hub-dim"].lower() == "#d8d4c8"


def _last_sheet_is_theme(html: bytes) -> bool:
    links = re.findall(rb'<link rel="stylesheet" href="([^"]+)">', html)
    return bool(links) and links[-1] == b"hub-theme.css"


def test_theme_sheet_is_last(monkeypatch: pytest.MonkeyPatch) -> None:
    assert page.STYLE_ORDER[-1] == "hub-theme.css"
    assert page.STYLE_ORDER.index("hub-gate.css") == len(page.STYLE_ORDER) - 2
    assert "hub-theme.js" in page.SCRIPT_ORDER
    assert page.SCRIPT_ORDER.index("hub-theme.js") == page.SCRIPT_ORDER.index("hub-core.js") + 1
    payload = build_payload(load_run(PUBLIC))
    open_page = page.render_page(payload, files=FILES)
    locked_page = page.render_page(None, files=FILES, gated=True)
    assert _last_sheet_is_theme(open_page) and _last_sheet_is_theme(locked_page)
    head = re.search(rb"<head>(.*?)</head>", open_page, re.S).group(1)
    assert head.count(b"hub-theme.css") == 1
    moved = list(page.STYLE_ORDER)
    moved.remove("hub-theme.css")
    moved.insert(moved.index("hub-graph.css"), "hub-theme.css")
    monkeypatch.setattr(page, "STYLE_ORDER", tuple(moved))
    assert not _last_sheet_is_theme(page.render_page(payload, files=FILES))


def _dark_blocks() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    explicit = system = None
    for media, selector, items in parse_rules(THEME.read_text(encoding="utf-8")):
        if selector == DARK_SELECTOR and not media:
            explicit = items
        if selector == SYSTEM_SELECTOR and media == DARK_MEDIA:
            system = items
    assert explicit is not None, "the explicit dark block is missing"
    assert system is not None, "the system dark block is missing"
    return explicit, system


def test_dark_set_is_complete() -> None:
    tokens = parse_rules((STATIC / "tokens.css").read_text(encoding="utf-8"))
    colour_tokens = {
        prop for media, selector, items in tokens if selector == ":root"
        for prop, value in items if prop.startswith("--mos-") and value.startswith("#")
    }
    assert colour_tokens == set(COLOR_TOKENS)
    explicit, _ = _dark_blocks()
    custom = {prop for prop, value in explicit if prop.startswith("--")}
    assert custom == set(COLOR_TOKENS) | set(HUB_TOKENS)
    assert ("color-scheme", "dark") in explicit
    assert {prop for prop, value in explicit if not prop.startswith("--")} == {"color-scheme"}


def test_default_follows_the_system_unless_a_choice_is_saved() -> None:
    explicit, system = _dark_blocks()
    assert sorted(explicit) == sorted(system)
    light = [items for media, selector, items in parse_rules(THEME.read_text(encoding="utf-8"))
             if selector == ':root[data-theme="light"]' and not media]
    assert light and ("color-scheme", "light") in light[0]
    root = [items for media, selector, items in parse_rules(THEME.read_text(encoding="utf-8"))
            if selector == ":root" and not media]
    assert root and ("color-scheme", "light") in root[0]
    text = THEME.read_text(encoding="utf-8")
    assert text.count("@media (prefers-color-scheme: dark)") == 1
    assert "prefers-color-scheme: light" not in text


def test_dark_specific_rules_use_tokens_only() -> None:
    """Rules that are not token sets take colours only through var(); no filter or blend."""
    text = THEME.read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    assert "filter" not in code and "mix-blend-mode" not in code
    scopes = {"explicit": [], "system": []}
    for media, selector, items in parse_rules(text):
        for prop, value in items:
            if prop.startswith("--"):
                continue
            if prop in {"color", "background", "background-color", "border-color", "fill",
                        "stroke", "outline-color", "box-shadow"}:
                assert "#" not in value, (selector, prop, value)
                assert re.search(r"var\(--(?:mos|hub)-[a-z-]+\)|transparent|currentColor", value), (
                    selector, prop, value)
        if DARK_SELECTOR in selector and not media:
            scopes["explicit"].append((selector, items))
        if SYSTEM_SELECTOR in selector and media == DARK_MEDIA:
            scopes["system"].append((selector, items))
    # Text on a yellow block: ink would be light on yellow in dark (1.50). Both scopes set paper.
    for name, rules in scopes.items():
        yellow = [items for selector, items in rules
                  if ".hub-role--bridge" in selector and ".hub-graph-chip" in selector]
        assert yellow and ("color", "var(--mos-paper)") in yellow[0], name
        lockup = {selector: items for selector, items in rules if "hub-lockup" in selector}
        assert any(".hub-lockup--paper" in s and ("display", "none") in i
                   for s, i in lockup.items()), name
        assert any(".hub-lockup--reverse" in s and ("display", "block") in i
                   for s, i in lockup.items()), name


def test_asset_entry() -> None:
    assert assets.EXPECTED_STATIC[REVERSE] == REVERSE_SHA
    assert assets.BOOK_SOURCES[REVERSE] == REVERSE_SOURCE
    packaged = STATIC / REVERSE
    data = packaged.read_bytes()
    assert len(data) == REVERSE_BYTES
    assert hashlib.sha256(data).hexdigest() == REVERSE_SHA
    assert b"<svg" in data[:200] and b"<script" not in data and b"https://" not in data
    assert data.count(b"http://") == data.count(b"http://www.w3.org/")
    book = Path(os.environ.get("MOS_BRAND_BOOK", str(Path.home() / "mos-brand")))
    if (book / REVERSE_SOURCE).is_file():
        assert data == (book / REVERSE_SOURCE).read_bytes()
    # The paper lockup entry is untouched.
    assert assets.EXPECTED_STATIC["assets/brand/mos-lockup-paper-v2.svg"] == (
        "028ffd9040e769684c78767b890175bf1b2734e7bd0a4bbf953de38051ba4477"
    )


def test_copy_theme_part() -> None:
    assert copy_theme.COPY == {
        "G03.theme.name": "Dark mode",
        "G03.theme.dark": "Dark",
        "G03.theme.light": "Light",
    }
    for key, value in copy_theme.COPY.items():
        assert DECK[key] == value
        assert value.isascii() and not has_dash(value)


def test_record_document() -> None:
    assert RECORD.is_file()
    text = RECORD.read_text(encoding="utf-8")
    assert not has_dash(text)
    for token, value in DARK_VALUES.items():
        assert f"`{token}`" in text, token
        assert value in text, (token, value)
    for theme, rows in EXPECTED.items():
        for value in rows.values():
            assert f"{value:.2f}" in text, (theme, value)
    lower = text.lower()
    assert "book silent, proposed segment" in lower
    assert "`hub-theme`" in text and "no flash" in lower and "aria-pressed" in text
    assert "prefers-color-scheme" in text and "localStorage" in text
    assert "mos-lockup-reverse-v2.svg" in text and "filter" in lower
    assert "proposal" in lower
