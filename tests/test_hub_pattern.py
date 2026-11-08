"""Pin the run reading band: states, sourced numbers, honest words, page markup and privacy.

Phase 2.3.1 plan 01 (D-04, HUB-07, HUB-04). The band reads the whole run in plain words
from the run data only. Names from `pattern.py` are imported inside each test, so a missing
module fails one test cleanly instead of the whole file.
"""

from __future__ import annotations

import ast
import copy
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from hub_support import build_run_folder_with_potential_eureka, make_run_folder
from mindrian_eureka.hub.contracts import has_dash, has_internal_name
from mindrian_eureka.hub.deck import DECK, fill
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.hub.verify import verify_payload
from mindrian_eureka.run.output import canonical_json
from test_hub_page import FILES, Document

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "tests/fixtures/hub_public"
PATTERN_SOURCE = ROOT / "src/mindrian_eureka/hub/pattern.py"

# The 14 strings of the family G17, byte for byte (Task 2 of the plan).
G17 = {
    "G17.label": "What this run shows",
    "G17.link": "Read the data check",
    "G17.read": (
        "This run read {records} records. Pairs ranked: {a} by the unusual-pairs engine, "
        "{b} by the wording engine."
    ),
    "G17.both": "Pairs that both engines list: {n}.",
    "G17.spread": (
        "Records in at least one pair that is shown: {a}. "
        "Records in no pair that is shown: {b}."
    ),
    "G17.hoods": (
        "The pair links group the records into {n} neighborhoods. The largest has {a} records."
    ),
    "G17.single": (
        "The pair links keep every paired record in one neighborhood and no record bridges two. "
        "This run shows no grouping to read."
    ),
    "G17.bridges": (
        "Records marked Potential eureka: {n}. A mark is a place to look, not a result."
    ),
    "G17.weak": "Pairs below the cut-off of their engine: {n}. They are hidden by default.",
    "G17.copies": (
        "Records that share their text with another record: {n}. A top pair may be a copy. "
        "Read the data check."
    ),
    "G17.classes": (
        "Pairs in the lists by class. Open next to licensed: {a}. Both open: {b}. "
        "Both licensed: {n}."
    ),
    "G17.top_k": "{engine}: the list stops at {n} pairs. Lower pairs are not shown.",
    "G17.none": (
        "No pairs were ranked, so this run has nothing to read. "
        "The engine notes are in the Opportunity bank."
    ),
    "G17.hidden": (
        "Every ranked pair sits below its cut-off and is hidden by default. "
        "Show weaker pairs in the Opportunity bank to read them."
    ),
}
CLAIM_WORDS = re.compile(
    r"\b(novel|novelty|new|wanted|valuable|value|breakthrough|discovery|promising|"
    r"interesting|significant|strongly|winner)\b",
    re.IGNORECASE,
)
OLD_KEYS = {
    "schema",
    "label",
    "tool_version",
    "run_fingerprint",
    "config",
    "counts",
    "engines",
    "records",
    "pairs",
    "hoods",
    "bridges",
    "data_check",
    "graph",
}
OLD_OPTIONAL_KEYS = {"has_pair_classes", "has_seed_commands"}
LATER_OPTIONAL_KEYS = {"pattern", "figures"}


def _payload(folder: Path) -> dict[str, Any]:
    return dict(build_payload(load_run(folder)))


def _keys(pattern: Mapping[str, Any]) -> list[str]:
    return [line["key"] for line in pattern["lines"]]


def _line(pattern: Mapping[str, Any], key: str) -> dict[str, Any]:
    found = [line for line in pattern["lines"] if line["key"] == key]
    assert len(found) == 1, (key, _keys(pattern))
    return found[0]


def _both_count(payload: Mapping[str, Any]) -> int:
    engines_by_pair: dict[str, set[str]] = {}
    for pair in payload["pairs"]:
        engines_by_pair.setdefault(pair["pair_id"], set()).add(pair["engine"])
    return sum(1 for engines in engines_by_pair.values() if len(engines) == 2)


def _hidden_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deep copy where every pair is weak, with counts and hoods edited to match."""
    data = copy.deepcopy(dict(payload))
    data.pop("pattern", None)
    for pair in data["pairs"]:
        pair["weak"] = True
    total = sum(data["counts"]["pairs"].values())
    data["counts"]["records_in_visible_pairs"] = 0
    data["counts"]["records_in_no_pair"] = data["counts"]["records"]
    data["counts"]["hoods"] = 0
    data["counts"]["weak_pairs"] = total
    data["hoods"] = []
    data["bridges"] = []
    return data


@pytest.fixture(scope="module")
def public_payload() -> dict[str, Any]:
    return _payload(PUBLIC / "run")


@pytest.fixture
def fixtures(tmp_path: Path) -> dict[str, dict[str, Any]]:
    """Every state once, plus the optional-line runs. Keys name the case."""
    grouped = _payload(build_run_folder_with_potential_eureka(tmp_path))
    no_bridges = copy.deepcopy(grouped)
    no_bridges.pop("pattern", None)
    no_bridges["bridges"] = []
    return {
        "public": _payload(PUBLIC / "run"),
        "grouped": grouped,
        "grouped_no_bridges": no_bridges,
        "none": _payload(make_run_folder(tmp_path / "none", zero_pairs=True)),
        "hidden": _hidden_payload(_payload(make_run_folder(tmp_path / "plain"))),
        "weak": _payload(
            make_run_folder(tmp_path / "weak", wording_floor=0.5, percentile_below_floor=3)
        ),
        "copies": _payload(make_run_folder(tmp_path / "copies", copies=2)),
        "classes": _payload(make_run_folder(tmp_path / "classes", pair_classes=True)),
    }


# --- Unit part ---------------------------------------------------------------


def test_public_fixture_is_single(public_payload: dict[str, Any]) -> None:
    pattern = public_payload["pattern"]
    assert pattern["state"] == "single"
    assert _keys(pattern) == [
        "G17.read",
        "G17.both",
        "G17.spread",
        "G17.single",
        "G17.top_k",
        "G16",
    ]
    assert _line(pattern, "G17.read")["values"] == {"records": 36, "a": 63, "b": 200}
    assert _line(pattern, "G17.both")["values"] == {"n": _both_count(public_payload)}
    assert _line(pattern, "G17.spread")["values"] == {"a": 36, "b": 0}
    assert _line(pattern, "G17.top_k")["values"] == {"engine": "Wording engine", "n": 200}
    assert _line(pattern, "G17.single")["values"] == {}
    assert _line(pattern, "G16")["values"] == {}


def test_grouped_state(fixtures: dict[str, dict[str, Any]]) -> None:
    pattern = fixtures["grouped"]["pattern"]
    assert pattern["state"] == "grouped"
    keys = _keys(pattern)
    assert _line(pattern, "G17.hoods")["values"]["n"] == 2
    assert _line(pattern, "G17.bridges")["values"] == {"n": 2}
    assert "G17.single" not in keys and "Gr09" not in keys
    assert keys.index("G17.hoods") + 1 == keys.index("G17.bridges")
    assert keys[-1] == "G16"


def test_none_state(fixtures: dict[str, dict[str, Any]]) -> None:
    pattern = fixtures["none"]["pattern"]
    assert pattern["state"] == "none"
    assert _keys(pattern) == ["G17.none", "G16"]


def test_hidden_state(fixtures: dict[str, dict[str, Any]]) -> None:
    from mindrian_eureka.hub.pattern import describe_run

    pattern = describe_run(fixtures["hidden"])
    assert pattern["state"] == "hidden"
    assert _keys(pattern) == ["G17.hidden", "G16"]


def test_optional_lines(fixtures: dict[str, dict[str, Any]]) -> None:
    from mindrian_eureka.hub.pattern import describe_run

    weak = fixtures["weak"]["pattern"]
    assert _line(weak, "G17.weak")["values"] == {"n": 3}
    copies = fixtures["copies"]
    assert _line(copies["pattern"], "G17.copies")["values"] == {
        "n": copies["data_check"]["identical_records"]
    }
    assert copies["data_check"]["identical_records"] > 0
    classes = fixtures["classes"]
    by_class = {"cross": 0, "open_open": 0, "licensed_licensed": 0}
    for pair in classes["pairs"]:
        if not pair["weak"]:
            by_class[pair["pair_class"]] += 1
    assert _line(classes["pattern"], "G17.classes")["values"] == {
        "a": by_class["cross"],
        "b": by_class["open_open"],
        "n": by_class["licensed_licensed"],
    }
    assert "G17.classes" not in _keys(fixtures["weak"]["pattern"])
    assert "G17.classes" not in _keys(fixtures["public"]["pattern"])
    no_bridges = describe_run(fixtures["grouped_no_bridges"])
    assert no_bridges["state"] == "grouped"
    keys = _keys(no_bridges)
    assert "G17.bridges" not in keys
    assert keys.index("G17.hoods") + 1 == keys.index("Gr09")
    assert _line(no_bridges, "Gr09")["values"] == {}


def _expected_values(payload: Mapping[str, Any], key: str) -> dict[str, Any] | None:
    """Recompute the values of one line from the payload, per the plan's Source table."""
    counts = payload["counts"]
    if key == "G17.read":
        return {
            "records": counts["records"],
            "a": counts["pairs"]["unusual_pairs"],
            "b": counts["pairs"]["wording_and_meaning"],
        }
    if key == "G17.both":
        return {"n": _both_count(payload)}
    if key == "G17.spread":
        return {"a": counts["records_in_visible_pairs"], "b": counts["records_in_no_pair"]}
    if key == "G17.hoods":
        return {"n": len(payload["hoods"]), "a": max(h["size"] for h in payload["hoods"])}
    if key == "G17.bridges":
        return {"n": len(payload["bridges"])}
    if key == "G17.weak":
        return {"n": counts["weak_pairs"]}
    if key == "G17.copies":
        return {"n": payload["data_check"]["identical_records"]}
    if key == "G17.classes":
        by_class = {"cross": 0, "open_open": 0, "licensed_licensed": 0}
        for pair in payload["pairs"]:
            if not pair["weak"] and pair.get("pair_class") in by_class:
                by_class[pair["pair_class"]] += 1
        return {
            "a": by_class["cross"],
            "b": by_class["open_open"],
            "n": by_class["licensed_licensed"],
        }
    if key in {"G17.single", "G17.none", "G17.hidden", "Gr09", "G16"}:
        return {}
    if key == "G17.top_k":
        return None
    raise AssertionError(f"unexpected band key {key}")


def test_numbers_are_sourced(fixtures: dict[str, dict[str, Any]]) -> None:
    from mindrian_eureka.hub.pattern import describe_run

    for name, payload in fixtures.items():
        pattern = payload["pattern"] if "pattern" in payload else describe_run(payload)
        top_k_lines = [line for line in pattern["lines"] if line["key"] == "G17.top_k"]
        expected_top_k = [
            {"engine": engines["short_name"], "n": engines["top_k"]}
            for engines in (payload["engines"][k] for k in ("unusual_pairs", "wording_and_meaning"))
            if engines["top_k_reached"]
        ]
        assert [line["values"] for line in top_k_lines] == expected_top_k, name
        for line in pattern["lines"]:
            expected = _expected_values(payload, line["key"])
            if expected is not None:
                assert line["values"] == expected, (name, line["key"])
        # The state rules compare counts with 0, 1 and 2 only.
        total = sum(payload["counts"]["pairs"].values())
        if total == 0:
            expected_state = "none"
        elif payload["counts"]["records_in_visible_pairs"] == 0:
            expected_state = "hidden"
        elif len(payload["hoods"]) >= 2 or len(payload["bridges"]) >= 1:
            expected_state = "grouped"
        else:
            expected_state = "single"
        assert pattern["state"] == expected_state, name


def test_no_threshold_constants() -> None:
    tree = ast.parse(PATTERN_SOURCE.read_text(encoding="utf-8"))
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.FunctionDef | ast.ClassDef | ast.AsyncFunctionDef):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docstrings.add(id(body[0].value))
    numbers = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, int | float)
        and not isinstance(node.value, bool)
        and id(node) not in docstrings
    ]
    assert all(value in (0, 1, 2) for value in numbers), numbers


def _filled_lines(pattern: Mapping[str, Any]) -> list[tuple[str, str]]:
    return [(line["key"], fill(DECK[line["key"]], **line["values"])) for line in pattern["lines"]]


def _assert_honest(text: str) -> None:
    assert text.isascii(), text
    assert not has_dash(text), text
    assert not has_internal_name(text), text
    assert CLAIM_WORDS.search(text) is None, text


def test_lines_are_plain_honest_words(fixtures: dict[str, dict[str, Any]]) -> None:
    from mindrian_eureka.hub.pattern import describe_run

    for payload in fixtures.values():
        pattern = payload["pattern"] if "pattern" in payload else describe_run(payload)
        for key, text in _filled_lines(pattern):
            assert text.isascii() and not has_dash(text) and not has_internal_name(text), key
            if key != "G16":
                _assert_honest(text)
    with pytest.raises(AssertionError):
        _assert_honest("A promising discovery.")


def test_deck_strings_are_exact() -> None:
    for key, text in G17.items():
        assert DECK[key] == text, key
    assert len([key for key in DECK if key.startswith("G17.")]) == len(G17) == 14


def test_pattern_is_deterministic() -> None:
    first = build_payload(load_run(PUBLIC / "run"))
    second = build_payload(load_run(PUBLIC / "run"))
    assert first["pattern"] == second["pattern"]
    assert canonical_json(first["pattern"]) == canonical_json(second["pattern"])


def test_pattern_holds_no_source_text(tmp_path: Path) -> None:
    payload = _payload(make_run_folder(tmp_path, hostile=True))
    short_names = {engine["short_name"] for engine in payload["engines"].values()}
    forbidden = {record["id"] for record in payload["records"]}
    forbidden |= {record["title"] for record in payload["records"] if record["title"]}
    forbidden.add("<script>")
    for line in payload["pattern"]["lines"]:
        for value in line["values"].values():
            assert isinstance(value, int | str) and not isinstance(value, bool)
            if isinstance(value, str):
                assert value in short_names, value
                assert value not in forbidden
                assert "<" not in value and "script" not in value.lower()


def test_pattern_does_not_change_other_keys(public_payload: dict[str, Any]) -> None:
    assert verify_payload(public_payload) == []  # type: ignore[arg-type]
    keys = set(public_payload) - LATER_OPTIONAL_KEYS
    assert OLD_KEYS <= keys
    assert keys - OLD_KEYS <= OLD_OPTIONAL_KEYS
    assert "pattern" in public_payload


# --- Page part ---------------------------------------------------------------


def _reading_text(pattern: Mapping[str, Any]) -> str:
    return " ".join(text for key, text in _filled_lines(pattern) if key != "G16")


def test_open_page_has_the_band(public_payload: dict[str, Any]) -> None:
    from mindrian_eureka.hub import page

    doc = Document(page.render_page(public_payload, files=FILES))  # type: ignore[arg-type]
    bands = [node for node in doc.tagged("section") if node.attrs.get("id") == "hub-band"]
    assert len(bands) == 1
    band = bands[0]
    assert "hub-band" in (band.attrs.get("class") or "").split()
    label = next(node for node in band.descendants() if node.attrs.get("id") == "hub-band-label")
    assert label.text == DECK["G17.label"]
    reading = [n for n in band.descendants() if "hub-band-reading" in (n.attrs.get("class") or "")]
    assert len(reading) == 1 and reading[0].tag == "p"
    assert reading[0].text == _reading_text(public_payload["pattern"])
    limit = [n for n in band.descendants() if "hub-band-limit" in (n.attrs.get("class") or "")]
    assert len(limit) == 1 and limit[0].tag == "p" and limit[0].text == DECK["G16"]
    links = [node for node in band.descendants() if node.tag == "a"]
    assert len(links) == 1
    assert links[0].attrs["href"] == "#hub-data-check" and links[0].text == DECK["G17.link"]
    body = doc.tagged("body")[0]
    order = [node.attrs.get("id") for node in body.children if node.attrs.get("id")]
    assert order.index("hub-counts") < order.index("hub-band") < order.index("hub-nav")


def _band_fragments() -> list[str]:
    fragments = []
    for text in G17.values():
        for part in re.split(r"\{[a-z_]+\}", text):
            part = part.strip()
            if len(part) >= 8:
                fragments.append(part)
    return fragments


def test_locked_page_band_is_empty_and_hidden() -> None:
    from mindrian_eureka.hub import page

    raw = page.render_page(None, files=FILES, gated=True)
    doc = Document(raw)
    band = doc.by_id("hub-band")
    assert "hidden" in band.attrs
    assert band.text == "" and band.children == []
    text = raw.decode("utf-8")
    for fragment in _band_fragments():
        assert fragment not in text, fragment


def test_band_has_no_script_dependency(public_payload: dict[str, Any]) -> None:
    from mindrian_eureka.hub import page

    raw = page.render_page(public_payload, files=FILES).decode("utf-8")  # type: ignore[arg-type]
    expected = _reading_text(public_payload["pattern"])
    assert expected in raw
    assert DECK["G17.label"] in raw and DECK["G17.link"] in raw
