"""Prove the look contract: the target side against the stored target stylesheet, the hub side
against the hub stylesheets, and every deviation against the decisions record (plan 02.3.1-03).

No browser. The target stylesheet is `evidence/target-site.css` of the phase folder; it holds
no name and no page text.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from hub_look_contract import ROLES, WIDTH_KEYS, Role
from mindrian_eureka.hub.page import STYLE_ORDER

ROOT = Path(__file__).resolve().parents[1]
PHASE = ROOT / ".planning/phases" / (
    "02.3.1-hub-look-matches-the-live-jhtv-site-cobalt-red-and-yellow-ac"
)
TARGET = PHASE / "evidence/target-site.css"
STATIC = ROOT / "src/mindrian_eureka/hub/assets/static"
AUTHORED = ROOT / "src/mindrian_eureka/hub/assets/authored"
DECISIONS = ROOT / "docs/brand/hub-design-decisions.md"

MEDIA = re.compile(r"@media\s*([^{]+?)\s*\{((?:[^{}]*\{[^{}]*\})*[^{}]*)\}", re.S)
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)
SCOPES = {"base": "base", "min-width: 768px": "768", "min-width: 1024px": "1024"}
PALETTE = {
    "--paper": "--mos-paper",
    "--ink": "--mos-ink",
    "--white": "--mos-white",
    "--soft": "--mos-soft",
    "--quiet": "--mos-quiet",
    "--blue": "--mos-blue",
    "--red": "--mos-red",
    "--yellow": "--mos-yellow",
}
FONTS = {
    "--display": "--mos-font-display",
    "--body": "--mos-font-body",
    "--mono": "--mos-font-code",
}

Sheet = dict[str, dict[tuple[str, str], str]]


def _declarations(block: str) -> list[tuple[str, str]]:
    found = []
    for item in block.split(";"):
        prop, sep, value = item.partition(":")
        if sep:
            found.append((prop.strip().lower(), value.strip()))
    return found


def parse_sheet(text: str) -> Sheet:
    """Return `{scope: {(selector, property): value}}` for a stylesheet.

    The scope is `base` outside any media query, or the query text (for example
    `min-width: 768px`). Selector lists split at the comma. The last declaration wins.
    """
    clean = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    sheet: Sheet = {"base": {}}

    def add(scope: str, body: str) -> None:
        for selectors, block in RULE.findall(body):
            for selector in selectors.split(","):
                key = re.sub(r"\s+", " ", selector.strip())
                for prop, value in _declarations(block):
                    sheet.setdefault(scope, {})[(key, prop)] = value

    for query, body in MEDIA.findall(clean):
        add(re.sub(r"\s*:\s*", ": ", query.strip().strip("()").strip()), body)
    add("base", MEDIA.sub("", clean))
    return sheet


def normalise(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def expand_hex(value: str) -> str:
    match = re.fullmatch(r"#([0-9a-f])([0-9a-f])([0-9a-f])", value.lower())
    if match:
        return "#" + "".join(char * 2 for char in match.groups())
    return value.lower()


@pytest.fixture(scope="module")
def target() -> Sheet:
    return parse_sheet(TARGET.read_text(encoding="utf-8"))


def _hub_sheets() -> list[Sheet]:
    sheets = []
    for name in STYLE_ORDER:
        path = STATIC / name if name == "tokens.css" else AUTHORED / name
        sheets.append(parse_sheet(path.read_text(encoding="utf-8")))
    return sheets


@pytest.fixture(scope="module")
def hub() -> list[Sheet]:
    return _hub_sheets()


def custom_properties(sheets: list[Sheet]) -> dict[str, str]:
    found: dict[str, str] = {}
    for sheet in sheets:
        for (selector, prop), value in sheet["base"].items():
            if selector == ":root" and prop.startswith("--"):
                found[prop] = value
    return found


def resolve(value: str, properties: dict[str, str]) -> str:
    for _ in range(6):
        changed = re.sub(
            r"var\((--[a-z0-9-]+)\)",
            lambda match: properties.get(match.group(1), match.group(0)),
            value,
        )
        if changed == value:
            break
        value = changed
    return value


def hub_value(sheets: list[Sheet], selector: str, prop: str, width: str) -> str | None:
    """Return the hub value at a width key, with the cascade of narrower scopes."""
    found = None
    for key in WIDTH_KEYS[: WIDTH_KEYS.index(width) + 1]:
        scope = next(query for query, name in SCOPES.items() if name == key)
        for sheet in sheets:
            value = sheet.get(scope, {}).get((selector, prop))
            if value is not None:
                found = value
    return found


def target_problems(role: Role, sheet: Sheet) -> list[str]:
    problems = []
    for selector, prop, expected in role.target:
        actual = sheet["base"].get((selector, prop))
        if actual is None or normalise(actual) != normalise(expected):
            problems.append(f"{role.id} target {selector} {prop}: {actual!r} != {expected!r}")
    return problems


def hub_problems(role: Role, sheets: list[Sheet]) -> list[str]:
    problems = []
    properties = custom_properties(sheets)
    for selector, prop, by_width in role.hub:
        for width, expected in by_width.items():
            actual = hub_value(sheets, selector, prop, width)
            if expected is None:
                if actual is not None:
                    problems.append(
                        f"{role.id} hub {selector} {prop} at {width}: {actual!r} present"
                    )
                continue
            if actual is None or normalise(resolve(actual, properties)) != normalise(
                resolve(expected, properties)
            ):
                problems.append(
                    f"{role.id} hub {selector} {prop} at {width}: {actual!r} != {expected!r}"
                )
    return problems


def deviation_table() -> dict[str, dict[str, str]]:
    text = DECISIONS.read_text(encoding="utf-8")
    start = text.find("Look contract deviations")
    assert start >= 0, "the decisions record has no table 'Look contract deviations'"
    rows: dict[str, dict[str, str]] = {}
    header: list[str] = []
    for line in text[start:].splitlines():
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not header:
            header = cells
            continue
        if set(cells[0]) <= set("-: "):
            continue
        rows[cells[0]] = dict(zip(header, cells, strict=False))
    return rows


def test_palette_equals_the_book_tokens(target: Sheet, hub: list[Sheet]) -> None:
    properties = custom_properties(hub)
    for name, token in PALETTE.items():
        assert expand_hex(target["base"][(":root", name)]) == expand_hex(properties[token]), name


def test_fonts_match(target: Sheet, hub: list[Sheet]) -> None:
    properties = custom_properties(hub)
    for name, token in FONTS.items():
        first = target["base"][(":root", name)].split(",")[0].strip("'\" ")
        assert first == properties[token].split(",")[0].strip("'\" "), name


def test_contract_holds_the_shell_rows() -> None:
    ids = [role.id for role in ROLES if role.after == "03"]
    assert ids == [f"S{n:02d}" for n in range(1, 32)]
    assert all(role.target and role.hub for role in ROLES)
    for role in ROLES:
        for _, _, by_width in role.hub:
            assert set(by_width) <= set(WIDTH_KEYS), role.id


@pytest.mark.parametrize("role", ROLES, ids=lambda role: role.id)
def test_target_side_of_every_role(role: Role, target: Sheet) -> None:
    assert target_problems(role, target) == []


def test_target_side_negative_control(target: Sheet) -> None:
    wrong = Role("S99", "control", (("body", "font", "16px/1.5 var(--body)"),), (), None, "03")
    assert target_problems(wrong, target)
    missing = Role("S98", "control", (("body", "no-such-property", "1"),), (), None, "03")
    assert target_problems(missing, target)


@pytest.mark.parametrize(
    "role", [role for role in ROLES if role.after == "03"], ids=lambda role: role.id
)
def test_hub_side_of_every_shell_role(role: Role, hub: list[Sheet]) -> None:
    assert hub_problems(role, hub) == []


def test_hub_side_negative_control(hub: list[Sheet]) -> None:
    wrong = Role("S97", "control", (), (("body", "line-height", {"base": "1.65"}),), None, "03")
    assert hub_problems(wrong, hub)
    present = Role("S96", "control", (), (("body", "margin", {"base": None}),), None, "03")
    assert hub_problems(present, hub)
    resolved = Role(
        "S95", "control", (), (("#hub-header", "background", {"base": "#f7f5ee"}),), None, "03"
    )
    assert hub_problems(resolved, hub) == []


def test_every_deviation_is_recorded() -> None:
    table = deviation_table()
    used = {item for role in ROLES for item in role.deviations()}
    for item in sorted(used):
        assert item in table, f"deviation {item} is not in the decisions record"
    for n in range(1, 35):
        item = f"LD-{n:02d}"
        assert item in table, f"{item} missing from the table"
        plans = table[item]["Plan"]
        other = [plan for plan in re.findall(r"\d\d", plans) if plan != "03"]
        assert item in used or other, f"{item} is used by no contract row and names no other plan"
    assert set(table) == {f"LD-{n:02d}" for n in range(1, 35)}


def test_decisions_record_the_owner_ruling() -> None:
    text = DECISIONS.read_text(encoding="utf-8")
    for needle in ("Owner ruling 2026-11-08", "overrules", "Phase 2.1 colour rule", "R-01",
                   "not run", "Phase 2.3.1 look change"):
        assert needle in text, needle
    assert "–" not in text and "—" not in text
