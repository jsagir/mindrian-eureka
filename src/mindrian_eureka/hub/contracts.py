"""Shared contracts of the opportunity hub.

This module holds every hub constant, schema id, limit, regex, run type and payload
type. Later hub modules import these names and never retype them.

Import rule: the standard library, `..run.contracts` and `..run.output` only. Importing
this module never loads numpy, torch or cryptography.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, NotRequired, TypedDict

from ..run.contracts import Record
from ..run.output import canonical_json

# --- Schema ids and file names ----------------------------------------------

HUB_MANIFEST_SCHEMA = "eureka.hub-manifest.v1"
HUB_DATA_SCHEMA = "eureka.hub-data.v1"
HUB_ENVELOPE_SCHEMA = "eureka.hub-envelope.v1"
HUB_SUMMARY_SCHEMA = "eureka.hub-summary.v1"

OUTPUT_HUB_HTML = "hub.html"
OUTPUT_HUB_DATA = "hub-data.js"
OUTPUT_HUB_COPY = "hub-copy.js"
OUTPUT_HUB_MANIFEST = "hub-manifest.json"
DEFAULT_HUB_OUT = "eureka-hub"

VIEW_NAMES: tuple[str, ...] = ("bank", "graph", "catalogue")

ENGINE_UNUSUAL = "unusual_pairs"
ENGINE_WORDING = "wording_and_meaning"
ENGINE_KEYS: tuple[str, ...] = (ENGINE_UNUSUAL, ENGINE_WORDING)

# Theo face states (D-20) and the output path of each face file.
FACE_FILES: Mapping[str, str] = MappingProxyType(
    {
        "Handover": "assets/faces/theo-handover.svg",
        "Limit": "assets/faces/theo-limit.svg",
        "Boundary": "assets/faces/theo-boundary.svg",
        "Rest": "assets/faces/theo-rest.svg",
    }
)
LOCKUP_FILE = "assets/brand/mos-lockup-paper-v2.svg"

# --- Limits -----------------------------------------------------------------

# Copied into the payload as `config`.
HUB_CONFIG: Mapping[str, int] = MappingProxyType(
    {
        "bank_page": 25,
        "catalogue_page": 50,
        "panel_text_chars": 600,
        "find_max": 8,
        "tour_max": 16,
        "graph_min_records": 15,
    }
)

# The no-script pre-render (ungated build only).
NOSCRIPT_PAIRS_PER_ENGINE = 50
NOSCRIPT_RECORDS = 200

# Line width of a pair in the map (UI-SPEC 6.2): from the cut-off to the best pair.
WIDTH_MIN = 0.15
WIDTH_MAX = 0.5
WIDTH_CROSSING = 1.6

# --- Colours that Python writes (UI-SPEC 4) ---------------------------------

NEIGHBORHOOD_TINTS: tuple[str, ...] = (
    "#5b7bd6",
    "#c9645c",
    "#4f8f7a",
    "#8a6bb8",
    "#b07a45",
    "#3f8fb0",
    "#b5608f",
    "#6f7f8f",
    "#a8584f",
    "#5e6fa8",
    "#4d7f5f",
    "#8c5f8f",
    "#6a94a4",
    "#a67b5b",
    "#57709c",
    "#9c6b6b",
    "#6b8f8a",
    "#9e8a4a",
    "#7b6ea6",
    "#a07090",
    "#708a60",
)
DIM_COLOR = "#d8d4c8"

# --- Text rules -------------------------------------------------------------

# The two dash code points are built from numbers, so this file holds no literal dash.
DASH_CHARS = chr(8211) + chr(8212)

# A bare engine code as a whole word, an identifier that starts with one of the two
# internal prefixes, or a file name that ends in .py. The class split keeps this file
# clear of its own scan.
INTERNAL_NAME = re.compile(
    r"\b(?:R[S]|H[S]I)\b|\b(?i:r[s]_|h[s]i_)\w*|[\w./\\-]+\.py\b",
)


def has_dash(text: str) -> bool:
    """Return True when `text` holds an en dash or an em dash."""
    return any(char in text for char in DASH_CHARS)


def has_internal_name(text: str) -> bool:
    """Return True when `text` holds an internal engine name, identifier or file name."""
    return INTERNAL_NAME.search(text) is not None


# --- Run types (what the reader returns) ------------------------------------


@dataclass(frozen=True)
class RunPair:
    """One ranked pair as stored in a pair file.

    Attributes:
        engine: The engine key.
        rank: The rank inside the engine, 1 is best.
        pair_id: The stable id of the pair.
        left_id: The id of the first record.
        right_id: The id of the second record.
        wording: The wording score.
        meaning: The meaning score.
        rank_score: The rank score.
        percentile: The percentile of the pair, or None when the engine gives none.
        reading: One of the fixed reading sentences of the run.
        pair_class: The pair class of the run's outcome rule, or None when the run has
            no rule (Phase 2.2, D-02).
        left_extras: The carried cells of the left record; empty without carry columns.
        right_extras: The carried cells of the right record; empty without carry columns.
        confirmed: The second signal flag of a wording-engine pair (`scores.second_signal
            .confirmed`), or None when the pair file has no boolean flag (Phase 2.3.1).
    """

    engine: str
    rank: int
    pair_id: str
    left_id: str
    right_id: str
    wording: float
    meaning: float
    rank_score: float
    percentile: float | None
    reading: str
    pair_class: str | None = None
    left_extras: Mapping[str, str] = field(default_factory=dict)
    right_extras: Mapping[str, str] = field(default_factory=dict)
    confirmed: bool | None = None


@dataclass(frozen=True)
class EngineRun:
    """The data of one engine in a run.

    Attributes:
        key: The engine key.
        name: The full engine name.
        score_meaning: The score-meaning text of the manifest, verbatim.
        notes: The engine notes, without notes that carry an internal name.
        min_percentile: The cut-off of the engine from the manifest settings.
        top_k: The number of pairs that was requested.
        top_k_reached: True when the engine returned `top_k` pairs.
        pairs: The pairs, in rank order.
    """

    key: str
    name: str
    score_meaning: str
    notes: tuple[str, ...]
    min_percentile: float
    top_k: int
    top_k_reached: bool
    pairs: tuple[RunPair, ...]


@dataclass(frozen=True)
class RunData:
    """Everything the hub reads from a finished run folder.

    Attributes:
        manifest_sha256: The sha256 of the whole manifest file.
        tool_version: The tool version from the manifest.
        records: The records, in file order.
        engines: The two engines, keyed by engine key.
        records_read: The number of records read before drops.
        dropped: The records removed before ranking, as the manifest lists them.
        caps_hit: The limits that were reached, as the manifest lists them.
        dropped_note_count: The number of engine notes the reader dropped.
        tool: The `tool` section of the manifest, verbatim (name, version, engines).
        room_sections: The manifest `settings.run.room_sections`, verbatim; empty when the
            run had no section map (Phase 2.3).
        corpus_sha256: The sha256 that the manifest lists for the corpus file; empty when
            not set.
    """

    manifest_sha256: str
    tool_version: str
    records: tuple[Record, ...]
    engines: dict[str, EngineRun]
    records_read: int
    dropped: tuple[dict[str, Any], ...]
    caps_hit: tuple[dict[str, Any], ...]
    dropped_note_count: int
    tool: Mapping[str, Any] = field(default_factory=dict)
    room_sections: Mapping[str, Any] = field(default_factory=dict)
    corpus_sha256: str = ""


# --- Payload types (what hub-data.js carries) -------------------------------


class PairSide(TypedDict):
    """One end of a pair in the payload."""

    id: str
    title: str
    source_file: str
    source_link: str


class PayloadPair(TypedDict):
    """One pair in the payload."""

    key: str
    pair_id: str
    engine: str
    rank: int
    left: PairSide
    right: PairSide
    wording: float
    meaning: float
    rank_score: float
    wording_text: str
    meaning_text: str
    rank_score_text: str
    percentile: float | None
    reading: str
    reading_kind: str
    label: str
    weak: bool
    weight: float
    width: float
    crosses: bool
    flag_identical: bool
    flag_no_text: bool
    pair_class: NotRequired[str]
    left_extras: NotRequired[dict[str, str]]
    right_extras: NotRequired[dict[str, str]]
    seed_command: NotRequired[str]
    confirmed: NotRequired[bool]


# The kinds of the three fixed reading sentences of a run (Phase 2.3.1): the pages pick
# the guidance line from the kind, never from the sentence text.
READING_KINDS: tuple[str, ...] = ("meaning", "wording", "agree")


class PayloadRecord(TypedDict):
    """One record in the payload."""

    id: str
    title: str
    text: str
    source_ref: str
    source_file: str
    text_sha256: str
    hood: int | None
    pair_keys: list[str]
    pair_count: int
    visible_pair_count: int
    bridge: bool
    bridge_rank: int | None
    bridge_hoods: list[int]
    identical_to: list[str]
    no_text: bool
    source_link: str
    catalogue_link: str
    file_link: str | None
    label: str


class PayloadEngine(TypedDict):
    """One engine in the payload."""

    key: str
    name: str
    short_name: str
    score_meaning: str
    notes: list[str]
    floor: float | None
    floor_text: str
    pairs: int
    top_k: int
    top_k_reached: bool
    weak: int


class PayloadHood(TypedDict):
    """One neighborhood in the payload."""

    number: int
    size: int
    tint: str
    record_ids: list[str]


class PayloadBridge(TypedDict):
    """One potential eureka in the payload."""

    record_id: str
    rank: int
    engine: str
    score: float
    score_text: str
    hoods: list[int]


class PayloadDataCheck(TypedDict):
    """The data check of the payload."""

    identical_records: int
    identical_groups: list[list[str]]
    no_text_records: int
    removed_count: int
    removed: list[dict[str, str]]
    removed_text: str
    boilerplate: str


class PayloadGraph(TypedDict):
    """The graph state of the payload."""

    earned: bool
    visible_records: int
    min_records: int
    not_drawn: int


class PayloadCounts(TypedDict):
    """The counts of the payload."""

    records: int
    pairs: dict[str, int]
    hoods: int
    records_in_visible_pairs: int
    records_in_no_pair: int
    weak_pairs: int


# The states of the run reading band (Phase 2.3.1, D-04), in this fixed order.
PATTERN_STATES: tuple[str, ...] = ("none", "hidden", "single", "grouped")


class PatternLine(TypedDict):
    """One line of the run reading band: a deck key and the values of its slots."""

    key: str
    values: dict[str, int | str]


class PayloadPattern(TypedDict):
    """The run reading band: a state and its lines, built from the payload only."""

    state: str
    lines: list[PatternLine]


class PayloadTerms(TypedDict):
    """The distinctive words of a run (Phase 2.3.1 plan 02): a screening aid, not evidence.

    Attributes:
        records: The record id to its 5 most distinctive words, best first.
        pairs: The pair id to the words both records share, at most 6.
    """

    records: dict[str, list[str]]
    pairs: dict[str, list[str]]


class PayloadFigureSet(TypedDict):
    """The two pictures of one pair (Phase 2.3.1 plan 04), as SVG text."""

    card: str
    detail: str


class PayloadLegend(TypedDict):
    """The legend a page prints beside the pictures."""

    summary: str
    card: str
    detail: str
    caption: str


class PayloadLabels(TypedDict):
    """The fixed words drawn inside a detail figure, for the HTML twin of the detail."""

    record_a: str
    record_b: str
    distinctive: str
    shared: str
    meaning: str
    wording: str
    none_shared: str


class PayloadFigures(TypedDict):
    """The figures of a run: one card and one detail for each pair key, plus the words."""

    pairs: dict[str, PayloadFigureSet]
    legend: PayloadLegend
    labels: PayloadLabels


class Payload(TypedDict):
    """The whole payload of `hub-data.js` (`window.HUB`)."""

    schema: str
    label: str
    tool_version: str
    run_fingerprint: str
    config: dict[str, int]
    counts: PayloadCounts
    engines: dict[str, PayloadEngine]
    records: list[PayloadRecord]
    pairs: list[PayloadPair]
    hoods: list[PayloadHood]
    bridges: list[PayloadBridge]
    data_check: PayloadDataCheck
    graph: PayloadGraph
    has_pair_classes: NotRequired[bool]
    has_seed_commands: NotRequired[bool]
    pattern: NotRequired[PayloadPattern]
    terms: NotRequired[PayloadTerms]
    figures: NotRequired[PayloadFigures]


# --- Functions --------------------------------------------------------------


def is_hub_folder(path: Path) -> bool:
    """Return True when `path` is a folder with a valid hub manifest.

    Args:
        path: The folder to test.

    Returns:
        True when `hub-manifest.json` parses and carries the hub manifest schema id.
    """
    manifest = path / OUTPUT_HUB_MANIFEST
    if not path.is_dir() or not manifest.is_file():
        return False
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and data.get("schema_version") == HUB_MANIFEST_SCHEMA


def deep_link(record_id: str) -> str:
    """Return the fragment that opens a record.

    View names and the prefixes used by page chrome get the `#record:` form.
    An ID already starting with `record:` gets the same prefix so the routing
    escape remains distinct from the original record ID.

    Args:
        record_id: The id of the record.

    Returns:
        The fragment, with the leading hash sign.
    """
    if record_id in VIEW_NAMES or record_id.startswith(
        ("hub-", "bank-", "graph-", "catalogue-", "record:")
    ):
        return f"#record:{record_id}"
    return f"#{record_id}"


_NAME_OK = re.compile(r"^[A-Z][A-Z0-9_]*$")
_JSON_STRING = re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"', re.DOTALL)
# Characters that are escaped inside JSON strings. The angle brackets are added to the
# characters named in the plan, because a closing script tag needs them.
_ESCAPES = {
    ord("{"): "\\u007b",
    ord("}"): "\\u007d",
    ord("&"): "\\u0026",
    ord("<"): "\\u003c",
    ord(">"): "\\u003e",
    0x2028: "\\u2028",
    0x2029: "\\u2029",
}


def _escape_match(match: re.Match[str]) -> str:
    return match.group(0).translate(_ESCAPES)


def js_assignment(name: str, value: object, *, digits: int | None = 6) -> bytes:
    """Return a JavaScript file that sets `window.NAME` to `value`.

    The JSON text is the canonical JSON of `value`. Inside its strings the characters
    `{`, `}`, `&`, `<`, `>`, U+2028 and U+2029 are written as `\\uXXXX` escapes, so the
    file can never close a script element and never breaks a line. The escapes change
    no value: `json.loads` returns the same data.

    Args:
        name: The property name, in capital letters, digits and underscores.
        value: Any JSON-like value.
        digits: The number of decimals for floats, or None for no rounding.

    Returns:
        The bytes to write: the assignment, a semicolon and one LF.

    Raises:
        ValueError: The name is not valid, or the value holds NaN or infinity.
    """
    if not _NAME_OK.match(name):
        raise ValueError(f"invalid property name: {name}")
    text = canonical_json(value, digits=digits).decode("utf-8").rstrip("\n")
    safe = _JSON_STRING.sub(_escape_match, text)
    return f"window.{name} = {safe};\n".encode()
