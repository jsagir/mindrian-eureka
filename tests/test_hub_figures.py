"""Tests of the lead figures (`mindrian_eureka.hub.figures` and `figure_copy`).

Phase 2.3.1 plan 04 (D-07, HUB-06). Every picture of the hub is an SVG that the hub's own
code draws from the run data and the run's own record text, with the standard library
only. The modules are imported inside each test, so a missing module is a clean failure.
A figure is a screening picture, never evidence. No test here claims otherwise.
"""

from __future__ import annotations

import copy
import hashlib
import os
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pytest
from hub_support import make_run_folder
from mindrian_eureka.hub.contracts import ENGINE_UNUSUAL, ENGINE_WORDING, has_internal_name
from mindrian_eureka.hub.deck import SLOT_NAMES
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.hub.terms import build_terms
from mindrian_eureka.run.contracts import LABEL

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_RUN = ROOT / "tests/fixtures/hub_public/run"
GOLDEN_DIR = ROOT / "tests/fixtures/hub_figures"
RULES_DOC = ROOT / "docs/brand/hub-figure-rules.md"
WRITE_FLAG = "EUREKA_WRITE_FIGURE_GOLDENS"
SVG_NS = "http://www.w3.org/2000/svg"

# The light palette of the plan (the 8 values a figure may hold).
PALETTE = {
    "paper": "#F7F5EE",
    "white": "#FFFFFF",
    "ink": "#111111",
    "soft": "#4B4943",
    "quiet": "#ECEAE2",
    "blue": "#1F3FBF",
    "red": "#D6281F",
    "yellow": "#F2C200",
}
PALETTE_VALUES = frozenset(value.lower() for value in PALETTE.values())

# The class table of the plan: class, fill token, stroke token and stroke width, dash,
# opacity, and text size. `None` means the class has no rule of that kind.
SHAPE_CLASSES: dict[str, dict[str, Any]] = {
    "f-paper": {"fill": "paper"},
    "f-frame": {"fill": "none", "stroke": "ink", "width": 6},
    "f-rule": {"stroke": "ink", "width": 6},
    "f-panel": {"fill": "white", "stroke": "ink", "width": 5},
    "f-ink": {"fill": "ink"},
    "f-blue": {"fill": "blue"},
    "f-red": {"fill": "red"},
    "f-yellow": {"fill": "yellow", "stroke": "ink", "width": 6},
    "f-tick": {"stroke": "ink", "width": 2, "opacity": ".35"},
    "f-fan": {"stroke": "ink", "width": 2, "opacity": ".55"},
    "f-link": {"stroke": "ink", "width": 8, "dash": "28 32"},
    "f-track": {"fill": "quiet", "stroke": "ink", "width": 3},
    "f-band": {"fill": "ink"},
    "f-chip": {"fill": "paper", "stroke": "ink", "width": 3},
    "f-chip-on": {"fill": "paper", "stroke": "paper", "width": 3},
}
TEXT_SIZES = {"f-mono": 28, "f-title": 36, "f-body": 34, "f-num": 72}
TEXT_MODIFIERS = {"f-soft", "f-blue-t", "f-red-t", "f-band-t", "f-chip-t"}
CLASS_TABLE = frozenset(SHAPE_CLASSES) | frozenset(TEXT_SIZES) | frozenset(TEXT_MODIFIERS)

# The slot names that the figure copy may use (a subset of the deck's SLOT_NAMES).
FIGURE_SLOTS = frozenset({"engine", "n", "x", "y", "z", "a", "b", "list", "title"})

# Detail layout containers of the plan, in canvas units.
PANEL_A = (50.0, 570.0)
PANEL_B = (830.0, 1350.0)
COLUMN = (570.0, 830.0)
BAND_X = (50.0, 1350.0)
BAND_Y = (702.0, 912.0)
CANVAS = (1400.0, 934.0)
CARD_TRACK = 760
BAR_MIN = 8

CLAIM_WORDS = (
    "novel",
    "novelty",
    "new",
    "wanted",
    "valuable",
    "value",
    "breakthrough",
    "discovery",
    "promising",
    "interesting",
    "significant",
    "strongly",
    "winner",
)
NO_SHARED_SENTENCE = "No distinctive word is shared. The link is in meaning only."


# --- helpers ----------------------------------------------------------------


def _elements(svg: str) -> list[ET.Element]:
    """Return every element of the figure in document order (the root first)."""
    return list(ET.fromstring(svg).iter())


def _tag(element: ET.Element) -> str:
    tag = element.tag
    return tag.split("}", 1)[1] if tag.startswith("{") else tag


def _classes(element: ET.Element) -> set[str]:
    return set(element.get("class", "").split())


def _num(element: ET.Element, name: str, default: float = 0.0) -> float:
    value = element.get(name)
    return float(value) if value is not None else default


def _bbox(element: ET.Element) -> tuple[float, float, float, float]:
    """Return the box of a rect or a line, with half the stroke on every side."""
    half = _num(element, "stroke-width") / 2.0
    if _tag(element) == "rect":
        x, y = _num(element, "x"), _num(element, "y")
        return (
            x - half,
            y - half,
            x + _num(element, "width") + half,
            y + _num(element, "height") + half,
        )
    if _tag(element) == "line":
        xs = (_num(element, "x1"), _num(element, "x2"))
        ys = (_num(element, "y1"), _num(element, "y2"))
        return (min(xs) - half, min(ys) - half, max(xs) + half, max(ys) + half)
    if _tag(element) == "circle":
        cx, cy, r = _num(element, "cx"), _num(element, "cy"), _num(element, "r")
        return (cx - r - half, cy - r - half, cx + r + half, cy + r + half)
    raise AssertionError(f"not a shape: {_tag(element)}")


def _overlaps(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _shapes(svg: str) -> list[ET.Element]:
    return [element for element in _elements(svg) if _tag(element) in {"rect", "line", "circle"}]


def _texts(svg: str) -> list[ET.Element]:
    return [element for element in _elements(svg) if _tag(element) == "text"]


def _title_and_desc(svg: str) -> tuple[str, str]:
    root = ET.fromstring(svg)
    children = list(root)
    return children[0].text or "", children[1].text or ""


def _all_text(svg: str) -> str:
    return " ".join(element.text or "" for element in _texts(svg))


def _public_payload() -> dict[str, Any]:
    run = load_run(PUBLIC_RUN)
    payload: dict[str, Any] = dict(build_payload(run))
    payload.pop("figures", None)
    payload["terms"] = build_terms(
        list(run.records),
        [(pair["pair_id"], pair["left"]["id"], pair["right"]["id"]) for pair in payload["pairs"]],
    )
    return payload


@pytest.fixture(scope="module")
def public() -> dict[str, Any]:
    return _public_payload()


@pytest.fixture(scope="module")
def public_figures(public: dict[str, Any]) -> dict[str, Any]:
    from mindrian_eureka.hub.figures import build_figures

    return build_figures(public)


@pytest.fixture(scope="module")
def hostile(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    run = load_run(make_run_folder(tmp_path_factory.mktemp("hostile"), hostile=True))
    payload: dict[str, Any] = dict(build_payload(run))
    payload.pop("figures", None)
    payload["terms"] = build_terms(
        list(run.records),
        [(pair["pair_id"], pair["left"]["id"], pair["right"]["id"]) for pair in payload["pairs"]],
    )
    return payload


def _every_figure(figures: Mapping[str, Any]) -> Iterable[tuple[str, str, str]]:
    for key in sorted(figures["pairs"]):
        yield key, "card", figures["pairs"][key]["card"]
        yield key, "detail", figures["pairs"][key]["detail"]


def _by_key(payload: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {pair["key"]: pair for pair in payload["pairs"]}


def _agree(payload: Mapping[str, Any], pair_id: str) -> bool:
    """The test's own agreement rule: both engines list the pair, a wording entry confirmed."""
    engines = {pair["engine"] for pair in payload["pairs"] if pair["pair_id"] == pair_id}
    confirmed = any(
        pair.get("confirmed") is True
        for pair in payload["pairs"]
        if pair["pair_id"] == pair_id and pair["engine"] == ENGINE_WORDING
    )
    return engines == {ENGINE_UNUSUAL, ENGINE_WORDING} and confirmed


def _eureka(payload: Mapping[str, Any], pair: Mapping[str, Any]) -> bool:
    bridges = {record["id"] for record in payload["records"] if record["bridge"]}
    return pair["left"]["id"] in bridges or pair["right"]["id"] in bridges


def mini(
    pairs: list[dict[str, Any]],
    records: list[tuple[str, str, bool]],
    terms_records: Mapping[str, list[str]] | None = None,
    terms_pairs: Mapping[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Build the smallest payload that `build_figures` reads.

    A pair spec holds engine, pair_id, rank, left, right, wording, meaning, and optional
    weak and confirmed. A record is (id, title, bridge).
    """
    entries = []
    for spec in pairs:
        entry: dict[str, Any] = {
            "key": f"{spec['engine']}:{spec['pair_id']}",
            "pair_id": spec["pair_id"],
            "engine": spec["engine"],
            "rank": spec["rank"],
            "left": {
                "id": spec["left"],
                "title": dict((r[0], r[1]) for r in records)[spec["left"]],
            },
            "right": {
                "id": spec["right"],
                "title": dict((r[0], r[1]) for r in records)[spec["right"]],
            },
            "wording": spec["wording"],
            "meaning": spec["meaning"],
            "wording_text": f"{spec['wording']:.4f}",
            "meaning_text": f"{spec['meaning']:.4f}",
            "weak": spec.get("weak", False),
        }
        if spec.get("confirmed") is not None:
            entry["confirmed"] = spec["confirmed"]
        entries.append(entry)
    return {
        "engines": {
            ENGINE_UNUSUAL: {"key": ENGINE_UNUSUAL, "short_name": "Unusual-pairs engine"},
            ENGINE_WORDING: {"key": ENGINE_WORDING, "short_name": "Wording engine"},
        },
        "records": [
            {"id": rid, "title": title, "bridge": bridge} for rid, title, bridge in records
        ],
        "pairs": entries,
        "terms": {
            "records": dict(terms_records or {rid: [] for rid, _, _ in records}),
            "pairs": dict(terms_pairs or {spec["pair_id"]: [] for spec in pairs}),
        },
    }


TWO = [("r-a", "Alpha record about rivers", False), ("r-b", "Beta record about grain", False)]


def _one(
    engine: str = ENGINE_WORDING,
    pair_id: str = "pair-0001",
    *,
    wording: float = 0.25,
    meaning: float = 0.5,
    confirmed: bool | None = None,
    records: list[tuple[str, str, bool]] | None = None,
    shared: list[str] | None = None,
    rank: int = 1,
) -> dict[str, Any]:
    spec = {
        "engine": engine,
        "pair_id": pair_id,
        "rank": rank,
        "left": "r-a",
        "right": "r-b",
        "wording": wording,
        "meaning": meaning,
        "confirmed": confirmed,
    }
    return mini([spec], records or TWO, terms_pairs={pair_id: shared or []})


def _card(payload: dict[str, Any], key: str | None = None) -> str:
    from mindrian_eureka.hub.figures import build_figures

    figures = build_figures(payload)
    key = key or payload["pairs"][0]["key"]
    return str(figures["pairs"][key]["card"])


def _detail(payload: dict[str, Any], key: str | None = None) -> str:
    from mindrian_eureka.hub.figures import build_figures

    figures = build_figures(payload)
    key = key or payload["pairs"][0]["key"]
    return str(figures["pairs"][key]["detail"])


def _meaning_bar(svg: str) -> ET.Element:
    bars = [
        element
        for element in _shapes(svg)
        if _tag(element) == "rect" and "f-blue" in _classes(element) and _num(element, "x") == 70
    ]
    assert len(bars) == 1
    return bars[0]


def _blocks(svg: str, cls: str) -> list[ET.Element]:
    return [
        element
        for element in _shapes(svg)
        if _tag(element) == "rect" and cls in _classes(element) and _num(element, "x") >= 800
    ]


def _claim_words(text: str) -> list[str]:
    found = []
    for word in CLAIM_WORDS:
        if re.search(rf"\b{word}\b", text, re.IGNORECASE):
            found.append(word)
    return found


# --- goldens ----------------------------------------------------------------


def _golden_choices(payload: dict[str, Any], figures: dict[str, Any]) -> dict[str, str]:
    pairs = payload["pairs"]
    unusual = [pair for pair in pairs if pair["engine"] == ENGINE_UNUSUAL]
    wording = [pair for pair in pairs if pair["engine"] == ENGINE_WORDING]
    unusual_ids = {pair["pair_id"] for pair in unusual}
    wording_ids = {pair["pair_id"] for pair in wording}
    both = min(unusual, key=lambda pair: pair["rank"])
    assert both["pair_id"] in wording_ids, "the rank 1 unusual pair must be in both lists"
    wording_only = min(
        (pair for pair in wording if pair["pair_id"] not in unusual_ids), key=lambda p: p["rank"]
    )
    unusual_only = min(
        (pair for pair in unusual if pair["pair_id"] not in wording_ids), key=lambda p: p["rank"]
    )
    shared = payload["terms"]["pairs"]
    others = [pair for pair in pairs if pair["key"] != both["key"]]
    with_words = next(pair for pair in others if len(shared[pair["pair_id"]]) >= 1)
    without = next(pair for pair in others if len(shared[pair["pair_id"]]) == 0)
    sets = figures["pairs"]
    return {
        "pair-both-engines-card.svg": sets[both["key"]]["card"],
        "pair-wording-only-card.svg": sets[wording_only["key"]]["card"],
        "pair-unusual-only-card.svg": sets[unusual_only["key"]]["card"],
        "pair-both-engines-detail.svg": sets[both["key"]]["detail"],
        "pair-shared-words-detail.svg": sets[with_words["key"]]["detail"],
        "pair-no-shared-detail.svg": sets[without["key"]]["detail"],
    }


def test_goldens_match(public: dict[str, Any], public_figures: dict[str, Any]) -> None:
    choices = _golden_choices(public, public_figures)
    paths = {name: GOLDEN_DIR / name for name in choices}
    if not all(path.exists() for path in paths.values()):
        if os.environ.get(WRITE_FLAG) == "1":
            GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
            for name, svg in choices.items():
                paths[name].write_bytes(svg.encode("utf-8"))
            pytest.fail("golden written, review it")
        missing = sorted(name for name, path in paths.items() if not path.exists())
        pytest.fail(f"golden missing: {', '.join(missing)}")
    for name, svg in choices.items():
        assert paths[name].read_bytes() == svg.encode("utf-8"), name


def test_determinism_and_order_independence(public: dict[str, Any]) -> None:
    from mindrian_eureka.hub.figures import build_figures

    first = build_figures(public)
    second = build_figures(public)
    assert first == second
    reversed_payload = copy.deepcopy(public)
    reversed_payload["pairs"] = list(reversed(reversed_payload["pairs"]))
    reversed_payload["records"] = list(reversed(reversed_payload["records"]))
    reversed_payload["terms"] = {
        "records": dict(reversed(list(public["terms"]["records"].items()))),
        "pairs": dict(reversed(list(public["terms"]["pairs"].items()))),
    }
    assert build_figures(reversed_payload) == first


def test_one_card_and_one_detail_for_every_pair_key(
    public: dict[str, Any], public_figures: dict[str, Any]
) -> None:
    keys = {pair["key"] for pair in public["pairs"]}
    assert set(public_figures) == {"pairs", "legend", "labels"}
    assert set(public_figures["pairs"]) == keys
    for key in keys:
        assert set(public_figures["pairs"][key]) == {"card", "detail"}
        assert isinstance(public_figures["pairs"][key]["card"], str)
        assert isinstance(public_figures["pairs"][key]["detail"], str)
    assert set(public_figures["legend"]) == {"summary", "card", "detail", "caption"}
    assert set(public_figures["labels"]) == {
        "record_a",
        "record_b",
        "distinctive",
        "shared",
        "meaning",
        "wording",
        "none_shared",
    }
    weak = [pair["key"] for pair in public["pairs"] if pair["weak"]]
    for key in weak:
        assert key in public_figures["pairs"]


# --- safety -----------------------------------------------------------------


def _assert_safe(svg: str, tags: frozenset[str], attrs: frozenset[str]) -> None:
    assert svg.startswith("<svg ") and svg.endswith("</svg>")
    root = ET.fromstring(svg)
    assert _tag(root) == "svg"
    assert root.get("role") == "img"
    assert "hub-figure" in _classes(root)
    children = list(root)
    assert _tag(children[0]) == "title" and _tag(children[1]) == "desc"
    for element in root.iter():
        assert _tag(element) in tags, _tag(element)
        for name in element.attrib:
            assert name in attrs, name
        assert "id" not in element.attrib
        if _tag(element) not in {"text", "title", "desc"}:
            assert not (element.text or "").strip(), _tag(element)
        assert not (element.tail or "").strip(), _tag(element)
    lowered = svg.lower()
    for needle in (
        "doctype",
        "entity",
        "<image",
        "<script",
        "<foreignobject",
        "href",
        "xlink",
        "style=",
        "url(",
    ):
        assert needle not in lowered, needle
    assert re.search(r"\son[a-z]+=", lowered) is None
    without_namespace = svg.replace(f'xmlns="{SVG_NS}"', "", 1)
    assert "http" not in without_namespace.lower()


def test_safety_scan(public_figures: dict[str, Any], hostile: dict[str, Any]) -> None:
    from mindrian_eureka.hub.figures import (
        FIGURE_ATTRS,
        FIGURE_TAGS,
        build_figures,
        figure_problems,
    )

    assert len(FIGURE_TAGS) == 7 and len(FIGURE_ATTRS) == 21
    assert "id" not in FIGURE_ATTRS and "href" not in FIGURE_ATTRS and "style" not in FIGURE_ATTRS
    hostile_figures = build_figures(hostile)
    for figures in (public_figures, hostile_figures):
        for key, _, svg in _every_figure(figures):
            _assert_safe(svg, FIGURE_TAGS, FIGURE_ATTRS)
            assert figure_problems(svg) == [], key
    head = f'<svg xmlns="{SVG_NS}" viewBox="0 0 1400 934" role="img" class="hub-figure">'
    body = "<title>t</title><desc>d</desc>"
    bad = {
        "image": head + body + '<image href="x.png"/></svg>',
        "script": head + body + "<script>1</script></svg>",
        "onload": head.replace("<svg ", '<svg onload="x()" ') + body + "</svg>",
        "style": head + body + '<rect style="fill:red"/></svg>',
        "id": head + body + '<rect id="a"/></svg>',
        "anchor": head + body + '<a><rect x="1"/></a></svg>',
        "not xml": head + body + "<rect></svg>",
        "stray text": head + body + "<rect/>loose words</svg>",
        "not a string": 5,
        "wrong end": head + body,
    }
    for name, text in bad.items():
        problems = figure_problems(text)  # type: ignore[arg-type]
        assert problems, name
        assert all(isinstance(item, str) and item.endswith(".") for item in problems), name


def test_classes_are_the_vocabulary_and_fallbacks_exist(
    public_figures: dict[str, Any], hostile: dict[str, Any]
) -> None:
    from mindrian_eureka.hub.figures import CLASS_TABLE as MODULE_TABLE
    from mindrian_eureka.hub.figures import build_figures

    assert MODULE_TABLE == CLASS_TABLE
    colour = re.compile(r"#[0-9a-fA-F]{3,8}")
    for figures in (public_figures, build_figures(hostile)):
        for key, _, svg in _every_figure(figures):
            for found in colour.findall(svg):
                assert found.lower() in PALETTE_VALUES, (key, found)
            assert "rgb(" not in svg and "hsl(" not in svg
            for element in _elements(svg):
                classes = _classes(element)
                if _tag(element) == "svg":
                    assert classes == {"hub-figure"}
                    continue
                if _tag(element) in {"title", "desc"}:
                    assert not classes
                    continue
                assert classes and classes <= CLASS_TABLE, (key, classes)
                if _tag(element) == "text":
                    sizes = [TEXT_SIZES[cls] for cls in classes if cls in TEXT_SIZES]
                    assert len(sizes) == 1, (key, classes)
                    assert element.get("font-size") == str(sizes[0])
                    assert element.get("fill", "").lower() in PALETTE_VALUES
                    continue
                shape_classes = [cls for cls in classes if cls in SHAPE_CLASSES]
                assert len(shape_classes) == 1, (key, classes)
                rule = SHAPE_CLASSES[shape_classes[0]]
                if "fill" in rule:
                    expected = "none" if rule["fill"] == "none" else PALETTE[rule["fill"]].lower()
                    assert element.get("fill", "").lower() == expected, (key, classes)
                if "stroke" in rule:
                    assert element.get("stroke", "").lower() == PALETTE[rule["stroke"]].lower()
                    assert element.get("stroke-width") == str(rule["width"])
                else:
                    assert "stroke" not in element.attrib
                if "dash" in rule:
                    assert element.get("stroke-dasharray") == rule["dash"]
                if "opacity" in rule:
                    assert element.get("opacity") == rule["opacity"]


def test_size_budget(public_figures: dict[str, Any], hostile: dict[str, Any]) -> None:
    from mindrian_eureka.hub.figures import (
        CARD_HARD_MAX_BYTES,
        CARD_MAX_BYTES,
        DETAIL_MAX_BYTES,
        build_figures,
    )

    # OPP-027.svg of the target measured 5054 bytes: a hard ceiling for a card, never a goal.
    assert CARD_HARD_MAX_BYTES == 5054
    assert CARD_MAX_BYTES % 1024 == 0 and DETAIL_MAX_BYTES % 1024 == 0
    assert CARD_MAX_BYTES <= CARD_HARD_MAX_BYTES
    largest_card = largest_detail = 0
    for figures in (public_figures, build_figures(hostile)):
        for key, kind, svg in _every_figure(figures):
            size = len(svg.encode("utf-8"))
            if kind == "card":
                assert size <= CARD_MAX_BYTES, (key, size)
                assert size <= CARD_HARD_MAX_BYTES, (key, size)
                largest_card = max(largest_card, size)
            else:
                assert size <= DETAIL_MAX_BYTES, (key, size)
                largest_detail = max(largest_detail, size)
    print(f"largest card {largest_card} bytes, largest detail {largest_detail} bytes")
    assert largest_card > 0 and largest_detail > 0


# --- the card ---------------------------------------------------------------


def _data_shapes(svg: str) -> list[tuple[str, tuple[str, ...]]]:
    """Return every shape that is not the rule or the fan, as (tag, sorted attributes)."""
    out = []
    for element in _shapes(svg):
        classes = _classes(element)
        if classes & {"f-rule", "f-fan"}:
            continue
        out.append((_tag(element), tuple(sorted(element.attrib.items()))))
    return out


def _fan(svg: str) -> list[tuple[str, ...]]:
    return [
        tuple(sorted(element.attrib.items()))
        for element in _shapes(svg)
        if _classes(element) & {"f-rule", "f-fan"}
    ]


def test_card_has_no_text_and_decoration_is_seeded_by_the_pair_id() -> None:
    base = _card(_one(pair_id="pair-0001", shared=["river", "delta"]))
    assert not _texts(base)
    _, desc = _title_and_desc(base)
    assert "The thin lines are decoration" in desc
    fans = [element for element in _shapes(base) if "f-fan" in _classes(element)]
    assert len(fans) == 7
    rules = [element for element in _shapes(base) if "f-rule" in _classes(element)]
    assert len(rules) == 1
    first_byte = hashlib.sha256(b"pair-0001").digest()[0]
    assert _num(rules[0], "x1") == 1100 + 20 * (first_byte % 3)
    assert _card(_one(pair_id="pair-0001", shared=["river", "delta"])) == base
    changed = None
    for index in range(2, 40):
        other = _card(_one(pair_id=f"pair-{index:04d}", shared=["river", "delta"]))
        if _fan(other) != _fan(base):
            changed = other
            break
    assert changed is not None, "no other pair id changed the fan"
    assert _data_shapes(changed) == _data_shapes(base)


def test_card_encoding() -> None:
    from mindrian_eureka.hub.figures import scale_for

    # (a) the meaning bar width follows the scale, with a minimum of 8.
    for meaning, expected in ((0.5, 380), (0.0, BAR_MIN), (0.004, BAR_MIN), (1.0, 760), (1.4, 760)):
        bar = _meaning_bar(_card(_one(meaning=meaning)))
        assert _num(bar, "width") == expected, meaning
        assert _num(bar, "x") == 70 and _num(bar, "y") == 330 and _num(bar, "height") == 126
    assert round(CARD_TRACK * 0.5) == 380
    # (b) the wording engine scale is 0 to 1; the unusual-pairs scale spans the extremes.
    wording_card = _card(_one(ENGINE_WORDING, meaning=0.5))
    assert "on a scale from 0 to 1." in _title_and_desc(wording_card)[1]
    assert scale_for(ENGINE_WORDING, [{"wording": 3.0, "meaning": -2.0}]) == (0.0, 1.0)
    shown = [
        {"wording": 0.039096, "meaning": 1.299088, "weak": False},
        {"wording": 0.5, "meaning": 0.2, "weak": False},
    ]
    assert scale_for(ENGINE_UNUSUAL, shown) == (0.0, 1.299088)
    assert scale_for(ENGINE_UNUSUAL, [{"wording": -0.5, "meaning": 0.5}]) == (-0.5, 1.0)
    assert scale_for(ENGINE_UNUSUAL, []) == (0.0, 1.0)
    unusual = mini(
        [
            {
                "engine": ENGINE_UNUSUAL,
                "pair_id": "pair-u1",
                "rank": 1,
                "left": "r-a",
                "right": "r-b",
                "wording": 0.039096,
                "meaning": 1.299088,
            },
            {
                "engine": ENGINE_UNUSUAL,
                "pair_id": "pair-u2",
                "rank": 2,
                "left": "r-a",
                "right": "r-b",
                "wording": 0.5,
                "meaning": 0.649544,
            },
        ],
        TWO,
    )
    desc_u1 = _title_and_desc(_card(unusual, f"{ENGINE_UNUSUAL}:pair-u1"))[1]
    assert "on a scale from 0 to 1.2991." in desc_u1
    assert _num(_meaning_bar(_card(unusual, f"{ENGINE_UNUSUAL}:pair-u1")), "width") == 760
    assert _num(_meaning_bar(_card(unusual, f"{ENGINE_UNUSUAL}:pair-u2")), "width") == 380
    # (c) one ink square for each shared word, at most 8.
    for count in (0, 1, 6, 8, 9):
        words = [f"word{index}" for index in range(count)]
        svg = _card(_one(shared=words))
        squares = [
            element
            for element in _shapes(svg)
            if "f-ink" in _classes(element) and _num(element, "y") >= 700
        ]
        assert len(squares) == min(count, 8), count
        for index, square in enumerate(squares):
            assert (_num(square, "x"), _num(square, "y")) == (70 + 96 * index, 720)
            assert (_num(square, "width"), _num(square, "height")) == (64, 64)

    # (d) and (h): the cobalt block exists exactly when both engines list the pair and a
    # wording entry confirmed it.
    def both(confirmed: bool | None, wording_engine_only: bool = False) -> str:
        specs = [
            {
                "engine": ENGINE_WORDING,
                "pair_id": "pair-x",
                "rank": 1,
                "left": "r-a",
                "right": "r-b",
                "wording": 0.3,
                "meaning": 0.6,
                "confirmed": confirmed,
            }
        ]
        if not wording_engine_only:
            specs.append(
                {
                    "engine": ENGINE_UNUSUAL,
                    "pair_id": "pair-x",
                    "rank": 1,
                    "left": "r-a",
                    "right": "r-b",
                    "wording": 0.3,
                    "meaning": 0.6,
                }
            )
        return _card(mini(specs, TWO), f"{ENGINE_WORDING}:pair-x")

    assert len(_blocks(both(True), "f-blue")) == 1
    assert "The cobalt block marks that." in _title_and_desc(both(True))[1]
    for negative in (both(True, wording_engine_only=True), both(False), both(None)):
        assert _blocks(negative, "f-blue") == []
        assert "cobalt block" not in _title_and_desc(negative)[1]
    # (e) the yellow block exists exactly when a record is a Potential eureka.
    eureka_records = [("r-a", "Alpha record about rivers", True), ("r-b", "Beta", False)]
    yellow = _blocks(_card(_one(records=eureka_records)), "f-yellow")
    assert len(yellow) == 1
    assert yellow[0].get("stroke-width") == "6" and yellow[0].get("stroke") == PALETTE["ink"]
    assert _num(yellow[0], "y") == 3 and _num(yellow[0], "height") == 140
    assert "Potential eureka" in _title_and_desc(_card(_one(records=eureka_records)))[1]
    assert _blocks(_card(_one()), "f-yellow") == []
    assert "Potential eureka" not in _title_and_desc(_card(_one()))[1]
    # (f) both blocks can appear together.
    together = mini(
        [
            {
                "engine": ENGINE_WORDING,
                "pair_id": "pair-y",
                "rank": 1,
                "left": "r-a",
                "right": "r-b",
                "wording": 0.3,
                "meaning": 0.6,
                "confirmed": True,
            },
            {
                "engine": ENGINE_UNUSUAL,
                "pair_id": "pair-y",
                "rank": 1,
                "left": "r-a",
                "right": "r-b",
                "wording": 0.3,
                "meaning": 0.6,
            },
        ],
        eureka_records,
    )
    svg = _card(together, f"{ENGINE_UNUSUAL}:pair-y")
    assert len(_blocks(svg, "f-blue")) == 1 and len(_blocks(svg, "f-yellow")) == 1
    cobalt = _blocks(svg, "f-blue")[0]
    assert _num(cobalt, "y") == 150 and _num(cobalt, "height") == 140

    # (g) the markers sit at the same places whatever the scores are.
    def markers(svg: str) -> list[tuple[str, ...]]:
        return [
            tuple(sorted(element.attrib.items()))
            for element in _shapes(svg)
            if "f-panel" in _classes(element)
            or ("f-ink" in _classes(element) and _num(element, "y") < 300)
        ]

    low, high = _card(_one(wording=0.0, meaning=0.0)), _card(_one(wording=1.0, meaning=1.0))
    assert markers(low) == markers(high)
    panels = [element for element in _shapes(low) if "f-panel" in _classes(element)]
    assert [(_num(p, "x"), _num(p, "y"), _num(p, "width")) for p in panels] == [
        (70, 110, 150),
        (400, 110, 150),
    ]
    # (i) the link is dashed 28 on and 32 off.
    links = [element for element in _shapes(low) if "f-link" in _classes(element)]
    assert len(links) == 1
    assert links[0].get("stroke-dasharray") == "28 32"
    assert (_num(links[0], "x1"), _num(links[0], "x2"), _num(links[0], "y1")) == (226, 394, 185)


# --- the detail -------------------------------------------------------------


def test_detail_text_and_words() -> None:
    from mindrian_eureka.hub.figure_copy import FIGURE_COPY

    words_a = ["river", "flood", "delta", "channel", "silt"]
    words_b = ["grain", "harvest", "soil", "seed", "field"]
    payload = _one(shared=["water", "field"])
    payload["terms"]["records"] = {"r-a": words_a, "r-b": words_b}
    svg = _detail(payload)
    text = _all_text(svg)
    for needle in (
        "Alpha record about rivers",
        "Beta record about grain",
        *words_a,
        *words_b,
        "water",
        "0.50",
        "0.25",
        FIGURE_COPY["G18.label.record_a"],
        FIGURE_COPY["G18.label.record_b"],
        FIGURE_COPY["G18.label.distinctive"],
        FIGURE_COPY["G18.label.shared"],
        FIGURE_COPY["G18.label.meaning"],
        FIGURE_COPY["G18.label.wording"],
    ):
        assert needle in text, needle
    assert NO_SHARED_SENTENCE not in text
    chips_on = [element for element in _shapes(svg) if "f-chip-on" in _classes(element)]
    assert len(chips_on) == 2
    none = _detail(_one())
    assert NO_SHARED_SENTENCE in _all_text(none)
    assert FIGURE_COPY["G18.label.none_shared"] == NO_SHARED_SENTENCE
    assert not [element for element in _shapes(none) if "f-chip-on" in _classes(element)]
    many = _detail(_one(shared=[f"word{index}" for index in range(9)]))
    assert len([element for element in _shapes(many) if "f-chip-on" in _classes(element)]) == 6
    # A long title is cut with three ASCII dots after 4 lines of 22 characters.
    long_title = " ".join(f"word{index:02d}" for index in range(30))
    cut = _detail(_one(records=[("r-a", long_title, False), ("r-b", "Short", False)]))
    titles_a = [
        element
        for element in _texts(cut)
        if "f-title" in _classes(element) and _num(element, "x") < PANEL_A[1]
    ]
    assert len(titles_a) == 4
    assert (titles_a[-1].text or "").endswith("...")
    assert all(len(element.text or "") <= 22 for element in titles_a)
    assert chr(8230) not in cut
    # Dash characters of a title become hyphens; nothing else of the title changes.
    dashed = "Alpha " + chr(8211) + " beta " + chr(8212) + " gamma"
    folded = _detail(_one(records=[("r-a", dashed, False), ("r-b", "Short", False)]))
    assert chr(8211) not in folded and chr(8212) not in folded
    assert "Alpha - beta - gamma" in _all_text(folded)
    assert "Alpha - beta - gamma" in _title_and_desc(folded)[1]
    # A hostile title is escaped text, never markup.
    hostile_title = '<script>window.__pwned=1</script> "quoted" & <b>bold</b>'
    escaped = _detail(_one(records=[("r-a", hostile_title, False), ("r-b", "Short", False)]))
    assert "<script" not in escaped and "<b>" not in escaped
    assert "&lt;script&gt;" in escaped
    assert "&amp;" in escaped
    ET.fromstring(escaped)
    assert "<script>" in _title_and_desc(escaped)[1]
    # An empty title shows the fixed string.
    empty = _detail(_one(records=[("r-a", "", False), ("r-b", "   ", False)]))
    assert _all_text(empty).count(FIGURE_COPY["G18.no_title"]) == 2
    assert FIGURE_COPY["G18.no_title"] == "(no title)"
    # No text of a figure sits outside title, desc and text elements.
    for element in _elements(empty):
        if _tag(element) not in {"title", "desc", "text"}:
            assert not (element.text or "").strip()
        assert not (element.tail or "").strip()


def _container(element: ET.Element) -> tuple[float, float]:
    x, y = _num(element, "x"), _num(element, "y")
    if BAND_Y[0] <= y <= BAND_Y[1]:
        return BAND_X
    if x < PANEL_A[1]:
        return PANEL_A
    if x >= PANEL_B[0]:
        return PANEL_B
    return COLUMN


def test_text_fits_by_the_width_model(
    public_figures: dict[str, Any], hostile: dict[str, Any]
) -> None:
    from mindrian_eureka.hub.figures import build_figures

    for figures in (public_figures, build_figures(hostile)):
        for key, kind, svg in _every_figure(figures):
            if kind == "card":
                continue
            title_lines = {"a": 0, "b": 0}
            for element in _texts(svg):
                classes = _classes(element)
                size = float(element.get("font-size", "0"))
                assert size >= 28, (key, classes)
                advance = 0.6 if "f-mono" in classes else 0.58
                width = len(element.text or "") * advance * size * 1.1
                left, right = _container(element)
                x = _num(element, "x")
                assert x >= left, (key, element.text)
                assert x + width <= right, (key, element.text, x + width, right)
                if "f-title" in classes:
                    title_lines["a" if x < PANEL_A[1] else "b"] += 1
            assert max(title_lines.values()) <= 4, key


ROLE_OVERLAPS_ALLOWED = {
    frozenset({"marker", "link"}),
    frozenset({"bar", "track"}),
    frozenset({"tick", "bar"}),
    frozenset({"tick", "track"}),
}


def _role(element: ET.Element) -> str | None:
    classes = _classes(element)
    x, y = _num(element, "x"), _num(element, "y")
    if classes & {"f-paper", "f-frame", "f-rule", "f-fan", "f-band", "f-chip", "f-chip-on"}:
        return None
    if "f-panel" in classes or ("f-ink" in classes and y < 300):
        return "marker"
    if "f-link" in classes:
        return "link"
    if "f-track" in classes:
        return "track"
    if "f-tick" in classes:
        return "tick"
    if "f-ink" in classes:
        return "square"
    if classes & {"f-blue", "f-red", "f-yellow"}:
        return "block" if x >= 800 else "bar"
    raise AssertionError(f"unknown role for {classes}")


def test_shapes_stay_inside_the_frame_and_do_not_overlap(
    public_figures: dict[str, Any], hostile: dict[str, Any]
) -> None:
    from mindrian_eureka.hub.figures import build_figures

    for figures in (public_figures, build_figures(hostile)):
        for key, kind, svg in _every_figure(figures):
            shapes = _shapes(svg)
            for element in shapes:
                box = _bbox(element)
                assert box[0] >= 0 and box[1] >= 0, (key, element.attrib)
                assert box[2] <= CANVAS[0] and box[3] <= CANVAS[1], (key, element.attrib)
            data = [(element, _role(element)) for element in shapes]
            data = [(element, role) for element, role in data if role is not None]
            for index, (first, role_a) in enumerate(data):
                for second, role_b in data[index + 1 :]:
                    if role_a == role_b or frozenset({role_a, role_b}) in ROLE_OVERLAPS_ALLOWED:
                        continue
                    assert not _overlaps(_bbox(first), _bbox(second)), (
                        key,
                        role_a,
                        first.attrib,
                        role_b,
                        second.attrib,
                    )
            if kind == "detail":
                panels = [element for element in shapes if "f-panel" in _classes(element)]
                assert len(panels) == 2
                for chip in (element for element in shapes if "f-chip" in _classes(element)):
                    box = _bbox(chip)
                    assert any(
                        _bbox(panel)[0] <= box[0]
                        and box[2] <= _bbox(panel)[2]
                        and _bbox(panel)[1] <= box[1]
                        and box[3] <= _bbox(panel)[3]
                        for panel in panels
                    ), (key, chip.attrib)
                bands = [element for element in shapes if "f-band" in _classes(element)]
                assert len(bands) == 1
                band = _bbox(bands[0])
                for chip in (element for element in shapes if "f-chip-on" in _classes(element)):
                    box = _bbox(chip)
                    assert band[0] <= box[0] and box[2] <= band[2], (key, chip.attrib)
                    assert band[1] <= box[1] and box[3] <= band[3], (key, chip.attrib)


# --- honesty ----------------------------------------------------------------


def test_description_numbers_equal_the_payload(
    public: dict[str, Any], public_figures: dict[str, Any]
) -> None:
    pairs = _by_key(public)
    shared = public["terms"]["pairs"]
    for key, kind, svg in _every_figure(public_figures):
        pair = pairs[key]
        _, desc = _title_and_desc(svg)
        assert (
            f"Meaning score {pair['meaning_text']} and wording score {pair['wording_text']}" in desc
        )
        words = shared[pair["pair_id"]]
        if words:
            assert ", ".join(words) in desc, (key, words)
            if kind == "card":
                assert f"{len(words)} shared distinctive words: {', '.join(words)}." in desc
        else:
            assert "No distinctive word is shared." in desc
        agree = _agree(public, pair["pair_id"])
        sentence = "Both engines list the pair and the second signal confirmed it."
        assert (sentence in desc) == agree, key
        assert ("Potential eureka" in desc) == _eureka(public, pair), key
    assert any(_agree(public, pair["pair_id"]) for pair in public["pairs"])


def test_plain_words_and_honesty(public: dict[str, Any], public_figures: dict[str, Any]) -> None:
    from mindrian_eureka.hub.figure_copy import FIGURE_COPY

    pairs = _by_key(public)
    terms = public["terms"]
    limits = (FIGURE_COPY["G18.card.limit"], FIGURE_COPY["G18.detail.limit"])
    for key, kind, svg in _every_figure(public_figures):
        title, desc = _title_and_desc(svg)
        for text in (title, desc):
            assert text.isascii(), (key, text)
            assert chr(8211) not in text and chr(8212) not in text
        assert LABEL in desc, key
        pair = pairs[key]
        stripped = desc
        for limit in limits:
            stripped = stripped.replace(limit, "")
        for side in ("left", "right"):
            stripped = stripped.replace(
                pair[side]["title"].replace(chr(8211), "-").replace(chr(8212), "-"), ""
            )
        for word in terms["records"][pair["left"]["id"]] + terms["records"][pair["right"]["id"]]:
            stripped = re.sub(rf"\b{re.escape(word)}\b", "", stripped)
        for word in terms["pairs"][pair["pair_id"]]:
            stripped = re.sub(rf"\b{re.escape(word)}\b", "", stripped)
        assert not has_internal_name(stripped), (key, stripped)
        assert not has_internal_name(title), key
        assert _claim_words(stripped + " " + title) == [], (key, kind, stripped)
    assert _claim_words("A promising discovery.") == ["discovery", "promising"]


def test_figure_copy_module() -> None:
    from mindrian_eureka.hub.figure_copy import FIGURE_COPY

    assert FIGURE_SLOTS <= SLOT_NAMES
    slot = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
    for key, value in FIGURE_COPY.items():
        assert key.startswith("G18."), key
        assert isinstance(value, str) and value.isascii(), key
        assert chr(8211) not in value and chr(8212) not in value, key
        assert value.count("{") == value.count("}") == len(slot.findall(value)), key
        for name in slot.findall(value):
            assert name in FIGURE_SLOTS, (key, name)
    for key in (
        "G18.card.title",
        "G18.card.scores",
        "G18.card.shared",
        "G18.card.shared_none",
        "G18.card.agree",
        "G18.card.eureka",
        "G18.card.decoration",
        "G18.card.limit",
        "G18.detail.title",
        "G18.detail.record_a",
        "G18.detail.record_b",
        "G18.detail.words_a",
        "G18.detail.words_b",
        "G18.detail.scores",
        "G18.detail.shared",
        "G18.detail.shared_none",
        "G18.detail.limit",
        "G18.label.record_a",
        "G18.label.record_b",
        "G18.label.distinctive",
        "G18.label.shared",
        "G18.label.meaning",
        "G18.label.wording",
        "G18.label.none_shared",
        "G18.no_title",
        "G18.legend.summary",
        "G18.legend.caption",
        "G18.legend.card",
        "G18.legend.detail",
    ):
        assert key in FIGURE_COPY, key
    assert FIGURE_COPY["G18.card.decoration"] == "The thin lines are decoration."
    assert FIGURE_COPY["G18.label.record_a"] == "RECORD A"
    assert FIGURE_COPY["G18.label.shared"] == "WORDS BOTH RECORDS SHARE"
    assert LABEL in FIGURE_COPY["G18.card.limit"] and LABEL in FIGURE_COPY["G18.detail.limit"]
    assert "screening aid" in FIGURE_COPY["G18.detail.limit"]
    assert "decoration" in FIGURE_COPY["G18.legend.caption"]


def test_rules_document() -> None:
    from mindrian_eureka.hub.figures import CARD_MAX_BYTES, DETAIL_MAX_BYTES

    assert RULES_DOC.exists(), RULES_DOC
    text = RULES_DOC.read_text(encoding="utf-8")
    assert chr(8211) not in text and chr(8212) not in text
    for needle in (
        "card",
        "detail",
        "class vocabulary",
        "yellow",
        "cobalt block",
        "decoration",
        "screening aid",
        "book silent, proposed segment",
        "5054",
        str(CARD_MAX_BYTES),
        str(DETAIL_MAX_BYTES),
    ):
        assert needle in text.lower() if needle.islower() else needle in text, needle
