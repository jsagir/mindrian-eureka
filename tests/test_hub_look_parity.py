"""Prove the built page against the target stylesheet through the look contract (plan 06).

Two static checks and three browser checks:

- the hub side of every row role (R01 to R11) holds in hub-bank.css (the static parser of
  `test_hub_look_tokens.py`);
- every role whose hub value differs from the target value carries a deviation id that the
  decisions record lists;
- the computed styles of the built public fixture at 390 and 1280 px equal the contract's hub
  values (px within 0.05, colours and words exact) in Chromium and Firefox;
- the longest index and the numerals fit their columns.

The target stylesheet holds no name and no page text. The public fixture is frozen; it is
built into a scratch folder.
"""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pytest
from hub_browser_support import file_url, require_browser, run_scenario
from hub_look_contract import ROLES, Role
from mindrian_eureka.hub.writer import HubRequest, build_hub
from mindrian_eureka.run.console import Console
from test_hub_browser_core import CHECKS
from test_hub_look_tokens import (
    PALETTE,
    TARGET,
    _hub_sheets,
    custom_properties,
    deviation_table,
    expand_hex,
    hub_problems,
    parse_sheet,
    resolve,
)

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_RUN = ROOT / "tests/fixtures/hub_public/run"
BANK = str(CHECKS / "bank-state.js")
PARITY = str(CHECKS / "look-parity.js")
WIDTHS = (390, 1280)
TOLERANCE = 0.05

# Role id to probe selector. A role not listed here is proven statically only.
PROBES: dict[str, str] = {
    "S01": "body", "S02": "body", "S04": "#hub-header", "S05": "#hub-header",
    "S06": "#hub-header", "S07": "#hub-header img", "S08": ".hub-header-label",
    "S10": "#hub-nav a", "S12": ".hub-header-action", "S13": ".hub-eyebrow",
    "S14": ".hub-eyebrow-dot", "S15": "#hub-title", "S16": ".hub-title-row",
    "S17": "#hub-counts", "S18": ".hub-count strong", "S19": ".hub-count span",
    "S21": "#hub-data-check", "S25": "#hub-footer", "S27": ".hub-band",
    "S28": ".hub-band-label", "S29": ".hub-band-mark", "S30": ".hub-band-reading",
    "S31": ".hub-band-link", "R01": ".hub-bank-row", "R02": ".hub-bank-row",
    "R03": ".hub-bank-row", "R04": ".hub-bank-rank-n", "R05": ".hub-bank-pair",
    "R06": ".hub-bank-ids a", "R07": ".hub-bank-numeral", "R08": ".hub-bank-caption",
    "R09": ".hub-bank-reading p", "R10": ".hub-bank-read", "R11": ".hub-bank-list",
}
# Contract selectors whose probe differs from the selector itself: the band section carries
# both classes; the current nav link is 700 by design, so a link that is not current is read.
SELECTOR_ALIAS = {".mos-ground-ink": ".hub-band", "#hub-nav a": "#hub-nav a:not([aria-current])"}
ONLY_AT = {"S04": (1280,)}
# Logical property to the physical computed property (horizontal writing, left to right).
LOGICAL = {
    "inset-block-start": "top", "min-block-size": "min-height", "inline-size": "width",
    "block-size": "height", "max-inline-size": "max-width",
    "margin-block-start": "margin-top", "margin-block-end": "margin-bottom",
    "padding-block-start": "padding-top", "padding-block-end": "padding-bottom",
    "border-block-end": "border-bottom", "border-block-start": "border-top",
}
COLOUR_PROPS = {"color", "background-color"}
# The computed value the browser gives when the hub must not declare the property.
INITIAL = {"backdrop-filter": "none", "border-radius": "0px", "transform": "none",
           "scroll-behavior": "auto"}
Expectation = tuple[str, str, str | float | list[str | float] | None]


@pytest.fixture(scope="module")
def public_hub(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("parity") / "hub"
    build_hub(HubRequest(PUBLIC_RUN, out), Console(stderr=io.StringIO()))
    return out


def hub_expectation(by_width: dict[str, str | None], width: int) -> tuple[bool, str | None]:
    """Return (declared, value) for a width: the last present key of the cascade."""
    keys = ["base"] + (["768"] if width >= 768 else []) + (["1024"] if width >= 1024 else [])
    found = False
    value: str | None = None
    for key in keys:
        if key in by_width:
            found = True
            value = by_width[key]
    return found, value


def to_rgb(value: str) -> str:
    value = expand_hex(value.strip())
    match = re.fullmatch(r"#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})", value)
    if not match:
        return value
    return "rgb({}, {}, {})".format(*(int(part, 16) for part in match.groups()))


def clamp_px(value: str, width: int) -> float:
    match = re.fullmatch(r"clamp\(\s*([\d.]+)px\s*,\s*([\d.]+)vw\s*,\s*([\d.]+)px\s*\)", value)
    assert match, value
    low, middle, high = (float(part) for part in match.groups())
    return min(max(low, middle * width / 100), high)


def expand(prop: str, value: str, width: int) -> list[tuple[str, str]]:
    """Turn a contract declaration into computed longhands with their expected text."""
    prop = LOGICAL.get(prop, prop)
    parts = value.split()
    if prop in {"border", "border-top", "border-bottom"}:
        sides = ["top", "right", "bottom", "left"] if prop == "border" else [prop.split("-")[1]]
        width_text, style, colour = parts
        return [item for side in sides for item in (
            (f"border-{side}-width", width_text), (f"border-{side}-style", style),
            (f"border-{side}-color", colour))]
    if prop == "border-block":
        return expand("border-top", value, width) + expand("border-bottom", value, width)
    if prop in {"padding", "margin"}:
        if len(parts) == 1:
            parts = parts * 4
        elif len(parts) == 2:
            parts = [parts[0], parts[1], parts[0], parts[1]]
        return list(zip([f"{prop}-top", f"{prop}-right", f"{prop}-bottom", f"{prop}-left"],
                        parts, strict=True))
    if prop == "padding-block":
        if len(parts) == 1:
            parts = parts * 2
        return [("padding-top", parts[0]), ("padding-bottom", parts[1])]
    if prop == "background":
        return [("background-color", value)]
    if prop == "text-decoration":
        return [("text-decoration-line", value)]
    return [(prop, value)]


def expected_computed(prop: str, value: str, width: int, font_size: float,
                      properties: dict[str, str]) -> str | float | list[str | float]:
    """Return the computed form of a contract value: px number, rgb text, word or tracks."""
    value = resolve(value, properties).strip()
    if prop == "grid-template-columns":
        tracks = re.findall(r"minmax\([^)]*\)|\S+", value)
        return [float(track[:-2]) if re.fullmatch(r"[\d.]+px", track) else track
                for track in tracks]
    if prop.endswith("color") or prop in COLOUR_PROPS:
        return "rgba(0, 0, 0, 0)" if value == "transparent" else to_rgb(value)
    if prop == "font-family":
        return value.split(",")[0].strip("'\" ")
    if value.startswith("clamp("):
        return clamp_px(value, width)
    if re.fullmatch(r"-?[\d.]+px", value):
        return float(value[:-2])
    if re.fullmatch(r"-?[\d.]+em", value):
        return round(float(value[:-2]) * font_size, 4)
    if prop == "line-height" and re.fullmatch(r"[\d.]+", value):
        return round(float(value) * font_size, 4)
    if value == "0":
        return 0.0
    return value


def compare(prop: str, expected: str | float | list[str | float], actual: str) -> str | None:
    if isinstance(expected, list):
        tracks = actual.split()
        if len(tracks) != len(expected):
            return f"{len(tracks)} tracks != {len(expected)}"
        for want, got in zip(expected, tracks, strict=True):
            if isinstance(want, float) and abs(float(got[:-2]) - want) > TOLERANCE:
                return f"track {got} != {want}px"
        return None
    if isinstance(expected, float):
        match = re.fullmatch(r"(-?[\d.]+)px", actual.strip())
        if not match or abs(float(match.group(1)) - expected) > TOLERANCE:
            return f"{actual!r} != {expected}px"
        return None
    if prop == "font-family":
        actual = actual.split(",")[0].strip("'\" ")
    return None if actual.strip() == expected else f"{actual!r} != {expected!r}"


def probes_for(width: int) -> list[dict[str, object]]:
    probes: list[dict[str, object]] = []
    for role in ROLES:
        if role.id not in PROBES or width not in ONLY_AT.get(role.id, WIDTHS):
            continue
        for selector, prop, by_width in role.hub:
            declared, value = hub_expectation(dict(by_width), width)
            if not declared or selector == ":root":
                continue
            probe_selector = SELECTOR_ALIAS.get(selector, selector)
            if value is None:
                if prop not in INITIAL:
                    continue
                props = [prop]
            else:
                props = [name for name, _ in expand(prop, value, width)]
            probes.append({"id": f"{role.id}|{selector}|{prop}", "selector": probe_selector,
                           "visible": True, "props": props})
    return probes


def problems_at(width: int, measured: dict[str, object],
                properties: dict[str, str]) -> list[str]:
    problems = []
    for role in ROLES:
        if role.id not in PROBES or width not in ONLY_AT.get(role.id, WIDTHS):
            continue
        for selector, prop, by_width in role.hub:
            declared, value = hub_expectation(dict(by_width), width)
            if not declared or selector == ":root":
                continue
            probe_id = f"{role.id}|{selector}|{prop}"
            if value is None and prop not in INITIAL:
                continue
            result = measured.get(probe_id)
            if result is None:
                problems.append(f"{probe_id} at {width}: no element")
                continue
            values = result["values"]  # type: ignore[index]
            font_size = float(result["fontSize"])  # type: ignore[index]
            if value is None:
                if values[prop].strip() != INITIAL[prop]:
                    problems.append(f"{probe_id} at {width}: {values[prop]!r} present")
                continue
            for name, text in expand(prop, value, width):
                expected = expected_computed(name, text, width, font_size, properties)
                difference = compare(name, expected, values[name])
                if difference:
                    problems.append(f"{probe_id} {name} at {width}: {difference}")
    return problems


def parity(hub: Path, browser: str) -> dict[str, dict[str, object]]:
    steps: list[dict[str, object]] = []
    for width in WIDTHS:
        steps.append({"kind": "setViewport", "width": width, "height": 900})
        steps.append({"kind": "eval", "file": PARITY, "as": str(width),
                      "args": {"probes": probes_for(width)}})
    result = run_scenario({"browser": browser, "url": file_url(hub / "hub.html"),
                           "steps": steps})
    assert result["ok"], result["stepErrors"]
    assert result["blockedRequests"] == [] and result["pageErrors"] == []
    assert result["cspViolations"] == []
    return result["results"]


# --- static ----------------------------------------------------------------


def test_contract_holds_the_row_rows() -> None:
    ids = [role.id for role in ROLES if role.after == "06"]
    assert ids == [f"R{n:02d}" for n in range(1, 12)]
    assert set(PROBES) <= {role.id for role in ROLES}


@pytest.mark.parametrize(
    "role", [role for role in ROLES if role.after == "06"], ids=lambda role: role.id
)
def test_hub_side_of_every_row_role(role: Role) -> None:
    assert hub_problems(role, _hub_sheets()) == []


def _plain(value: str, properties: dict[str, str]) -> str:
    text = resolve(value, properties)
    text = re.sub(r"#[0-9a-fA-F]{3,6}\b", lambda m: expand_hex(m.group(0)), text)
    text = re.sub(r"(?<![\d.])\.(\d)", r"0.\1", text)
    return re.sub(r"\s+", "", text).lower()


def target_properties() -> dict[str, str]:
    sheet = parse_sheet(TARGET.read_text(encoding="utf-8"))
    return {name: value for (selector, name), value in sheet["base"].items()
            if selector == ":root" and name.startswith("--")}


def unrecorded(role: Role, hub_props: dict[str, str], target_props: dict[str, str],
               table: dict[str, dict[str, str]]) -> list[str]:
    """Return the hub values that differ from the target without a recorded deviation."""
    targets = [_plain(value, target_props) for _, _, value in role.target]
    for name, token in PALETTE.items():
        hub_props = {**hub_props, token: hub_props.get(token, "")}
        target_props = {**target_props, name: target_props.get(name, "")}
    differences = []
    for selector, prop, by_width in role.hub:
        for value in by_width.values():
            if value is None:
                continue
            plain = _plain(value, hub_props)
            if not any(plain in target for target in targets):
                differences.append(f"{role.id} {selector} {prop} {value!r}")
    if not differences:
        return []
    missing = [item for item in role.deviations() if item not in table]
    if role.deviations() and not missing:
        return []
    return differences + [f"{role.id} deviation {item} not in the table" for item in missing]


def test_every_difference_is_a_recorded_deviation() -> None:
    hub_props = custom_properties(_hub_sheets())
    target_props = target_properties()
    table = deviation_table()
    for role in ROLES:
        if role.id in PROBES:
            assert unrecorded(role, hub_props, target_props, table) == [], role.id
    control = Role("S94", "control", (("body", "line-height", "1.58"),),
                   (("body", "line-height", {"base": "1.59"}),), None, "06")
    assert unrecorded(control, hub_props, target_props, table)
    recorded = Role("S93", "control", (("body", "line-height", "1.58"),),
                    (("body", "line-height", {"base": "1.59"}),), "LD-02", "06")
    assert unrecorded(recorded, hub_props, target_props, table) == []
    same = Role("S92", "control", (("body", "line-height", "1.58"),),
                (("body", "line-height", {"base": "1.58"}),), None, "06")
    assert unrecorded(same, hub_props, target_props, table) == []


# --- browser ---------------------------------------------------------------


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_target_parity_for_shell_and_rows(public_hub: Path, browser: str) -> None:
    require_browser(browser)
    results = parity(public_hub, browser)
    properties = custom_properties(_hub_sheets())
    problems = []
    for width in WIDTHS:
        measured = results[str(width)]
        assert measured["theme"] in (None, "light"), measured["theme"]
        assert measured["scrollWidth"] <= width
        problems.extend(problems_at(width, measured["probes"], properties))
    print(json.dumps({browser: {str(width): results[str(width)]["probes"] for width in WIDTHS}},
                     sort_keys=True))
    assert problems == []


def test_parity_negative_control() -> None:
    assert compare("font-size", 13.0, "14px")
    assert compare("font-size", 13.0, "13.02px") is None
    assert compare("color", "rgb(31, 63, 191)", "rgb(31, 63, 190)")
    assert compare("grid-template-columns", [44.0, "minmax(0, 1fr)", 150.0],
                   "44px 300px 151px")
    assert compare("grid-template-columns", [44.0, "minmax(0, 1fr)", 150.0],
                   "44px 300px 150px") is None
    assert expected_computed("color", "var(--mos-blue)", 1280, 16.0,
                             {"--mos-blue": "#1F3FBF"}) == "rgb(31, 63, 191)"
    assert expected_computed("letter-spacing", "-0.04em", 1280, 40.0, {}) == -1.6
    assert expected_computed("font-size", "clamp(34px, 4.2vw, 52px)", 390, 16.0, {}) == 34.0
    assert expected_computed("font-size", "clamp(34px, 4.2vw, 52px)", 1280, 16.0, {}) == 52.0


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_row_content_fits(public_hub: Path, browser: str) -> None:
    require_browser(browser)
    steps: list[dict[str, object]] = []
    for width in WIDTHS:
        steps.append({"kind": "setViewport", "width": width, "height": 900})
        # The filter first (it resets the paging), then 8 more pages reach rank 200.
        steps.append({"kind": "eval", "file": BANK, "as": f"filter-{width}",
                      "args": {"engine": "wording_and_meaning"}})
        steps.append({"kind": "eval", "file": BANK, "as": str(width),
                      "args": {"more": 8, "fit": True}})
    result = run_scenario({"browser": browser, "url": file_url(public_hub / "hub.html"),
                           "steps": steps})
    assert result["ok"], result["stepErrors"]
    for width in WIDTHS:
        state = result["results"][str(width)]
        ranks = [row["rank"] for row in state["fit"]]
        assert max(ranks) == 200, (width, max(ranks))
        for row in state["fit"]:
            index = row["index"]
            assert index is not None, (width, row["key"])
            assert index["scrollWidth"] <= index["clientWidth"], (width, row["key"], index)
            assert index["height"] < index["lineHeight"] * 1.5, (width, row["key"], index)
            assert len(row["numerals"]) == 2, (width, row["key"])
            for numeral in row["numerals"]:
                where = (width, row["key"], numeral)
                assert re.fullmatch(r"-?\d+\.\d{4}", numeral["text"]), where
                assert numeral["scrollWidth"] <= numeral["clientWidth"], where
                assert numeral["height"] < numeral["fontSize"] * 1.5, where
