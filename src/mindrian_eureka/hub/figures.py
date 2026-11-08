"""The lead figures of the hub: one card and one detail picture for every pair.

Phase 2.3.1 plan 04 (D-07, HUB-06). The hub draws every picture itself, as SVG, from
the run data and the run's own record text. The standard library does all of it. The
same run gives the same bytes: the code reads no clock, no random source and no
network. The only seed is the pair id, and it places decoration only. A person with an
image generator may replace a picture later; the generator is never needed.

Two variants of one lead:

- The card has no text. Two record markers joined by a dashed link, a meaning bar and
  a wording bar on the declared scale of the engine, one ink square for each shared
  distinctive word, a cobalt block when both engines list the pair and the second
  signal confirmed it, a yellow block only when a record of the pair is a Potential
  eureka, and a fan of thin lines seeded from the pair id. The fan is decoration and
  the description calls it decoration.
- The detail has text: each record's title (wrapped) and its 5 distinctive words as
  chips, the two scores with their bars, and a band with the words both records share,
  or the sentence that no distinctive word is shared.

Record text enters a figure in two forms only: a title (wrapped, XML-escaped, dash
characters folded to a hyphen) and words made of letters and hyphens (plan 02). The
distinctive words are a screening aid, never evidence. No picture claims novelty,
evidence, demand or value; every description ends with the limit sentence and the label
`candidate, not verified`.

Colour roles (owner ruling O-02, book `foundations/color` for yellow): cobalt is the
meaning score and the agreement block; red is the wording score; yellow marks a
Potential eureka only; ink and paper are structure. Every shape carries a class from
the vocabulary below, so the page stylesheet can theme it, and a light-palette
presentation attribute as a fallback outside the page.

The rule is written in `docs/brand/hub-figure-rules.md` and pinned by
`tests/test_hub_figures.py`.

Import rule: the standard library, `.contracts` (engine keys), `.deck` (`fill`) and
`.figure_copy` (which holds the label through `..run.contracts`). `.terms` is not
imported: the words come from the payload.
"""

from __future__ import annotations

import hashlib
import math
import xml.etree.ElementTree as ElementTree
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from html import escape
from typing import Any, TypedDict

from .contracts import ENGINE_KEYS, ENGINE_UNUSUAL, ENGINE_WORDING
from .deck import fill
from .figure_copy import FIGURE_COPY

# --- Palette and safety allow-lists -----------------------------------------

PALETTE: Mapping[str, str] = {
    "paper": "#F7F5EE",
    "white": "#FFFFFF",
    "ink": "#111111",
    "soft": "#4B4943",
    "quiet": "#ECEAE2",
    "blue": "#1F3FBF",
    "red": "#D6281F",
    "yellow": "#F2C200",
}
"""The 8 light-palette values a figure may hold (the book's colour tokens)."""

SVG_NS = "http://www.w3.org/2000/svg"

FIGURE_TAGS: frozenset[str] = frozenset({"svg", "title", "desc", "rect", "line", "circle", "text"})
"""The 7 element names a figure may hold."""

FIGURE_ATTRS: frozenset[str] = frozenset(
    {
        "xmlns",
        "viewBox",
        "role",
        "class",
        "x",
        "y",
        "width",
        "height",
        "x1",
        "y1",
        "x2",
        "y2",
        "cx",
        "cy",
        "r",
        "fill",
        "stroke",
        "stroke-width",
        "stroke-dasharray",
        "opacity",
        "font-size",
    }
)
"""The 21 attribute names a figure may hold. No id, no href, no style, no handler."""

_TEXT_TAGS = frozenset({"text", "title", "desc"})
_FORBIDDEN_TEXT = (
    ("<!", "a declaration, a comment or a CDATA section"),
    ("<?", "a processing instruction"),
    ("<image", "an image element"),
    ("<script", "a script element"),
    ("<foreignobject", "a foreignObject element"),
)
_MAX_PARSE_CHARS = 1_000_000

# --- Size caps --------------------------------------------------------------

CARD_HARD_MAX_BYTES = 5054
"""The size of OPP-027.svg, the one hand-built SVG of the target (PROVEN). A hard
ceiling for a card only, never a goal."""

CARD_MAX_BYTES = 4096
"""The working cap of a card: the largest measured card rounded up to the next 1024
bytes. The prototype measured 1426 to 1608 bytes without fallback attributes; this
generator measured 2432 to 3117 bytes on the public and the hostile payload (Task 2).
Task 4 of plan 04 re-measures on the goldens."""

DETAIL_MAX_BYTES = 7168
"""The working cap of a detail: the largest measured detail rounded up to the next 1024
bytes. The prototype measured 3318 to 3819 bytes without fallback attributes; this
generator measured 4762 to 6713 bytes on the public and the hostile payload (Task 2).
Task 4 of plan 04 re-measures on the goldens."""

# --- The class vocabulary (plan 03 writes the CSS from the same table) ------

# class: (fill token or "none" or None, stroke token or None, stroke width, dash, opacity)
_SHAPE_RULES: Mapping[str, tuple[str | None, str | None, int | None, str | None, str | None]] = {
    "f-paper": ("paper", None, None, None, None),
    "f-frame": ("none", "ink", 6, None, None),
    "f-rule": (None, "ink", 6, None, None),
    "f-panel": ("white", "ink", 5, None, None),
    "f-ink": ("ink", None, None, None, None),
    "f-blue": ("blue", None, None, None, None),
    "f-red": ("red", None, None, None, None),
    "f-yellow": ("yellow", "ink", 6, None, None),
    "f-tick": (None, "ink", 2, None, ".35"),
    "f-fan": (None, "ink", 2, None, ".55"),
    "f-link": (None, "ink", 8, "28 32", None),
    "f-track": ("quiet", "ink", 3, None, None),
    "f-band": ("ink", None, None, None, None),
    "f-chip": ("paper", "ink", 3, None, None),
    "f-chip-on": ("paper", "paper", 3, None, None),
}
_TEXT_SIZES: Mapping[str, int] = {"f-mono": 28, "f-title": 36, "f-body": 34, "f-num": 72}
_TEXT_FILLS: Mapping[str, str] = {
    "f-soft": "soft",
    "f-blue-t": "blue",
    "f-red-t": "red",
    "f-band-t": "paper",
    "f-chip-t": "ink",
}
CLASS_TABLE: frozenset[str] = (
    frozenset(_SHAPE_RULES) | frozenset(_TEXT_SIZES) | frozenset(_TEXT_FILLS)
)
"""Every class a figure may set, the root's `hub-figure` aside."""

# --- Canvas and layout, in canvas units -------------------------------------

CANVAS_W = 1400
CANVAS_H = 934
FRAME_INSET = 3

# The card.
MARKER_XS = (70, 400)
MARKER_Y = 110
MARKER_SIZE = 150
MARKER_CORNER = 50
LINK_Y = 185
LINK_X1 = 226
LINK_X2 = 394
TICK_XS = (70, 450, 830)
TICK_Y1 = 300
TICK_Y2 = 650
BAR_X = 70
MEANING_BAR_Y = 330
WORDING_BAR_Y = 500
BAR_H = 126
CARD_TRACK = 760
BAR_MIN = 8
SQUARE_Y = 720
SQUARE_SIZE = 64
SQUARE_PITCH = 96
SQUARES_MAX = 8
RULE_BASE = 1100
RULE_STEP = 20
RULE_CHOICES = 3
FAN_ORIGIN = (850, 467)
FAN_LINES = 7
FAN_Y_BASE = 330
FAN_Y_STEP = 60
FAN_Y_CHOICES = 5
FAN_Y_SLOPE = 24
FAN_END_GAP = 20
BLOCK_H = 140
COBALT_BLOCK_Y = 150
YELLOW_BLOCK_Y = 3

# The detail.
PANEL_XS = (50, 830)
PANEL_Y = 100
PANEL_W = 520
PANEL_H = 570
STRIP_H = 22
PAD = 14
PANEL_LABEL_Y = 166
TITLE_Y = 214
TITLE_PITCH = 44
TITLE_WIDTH = 22
TITLE_LINES = 4
WORDS_LABEL_Y = 410
CHIP_Y = 426
CHIP_H = 52
CHIP_PITCH = 62
CHIP_GAP = 10
CHIP_CHAR = 18
CHIP_PAD = 30
CHIP_TEXT_DX = 15
CHIP_TEXT_DY = 36
CHIP_TEXT_MAX = 27
COLUMN_X = 600
MEANING_LABEL_Y = 236
MEANING_TRACK_Y = 250
TRACK_W = 200
TRACK_H = 36
MEANING_NUM_Y = 352
DETAIL_LINK_Y = 400
DETAIL_LINK_X1 = 570
DETAIL_LINK_X2 = 830
WORDING_LABEL_Y = 452
WORDING_TRACK_Y = 466
WORDING_NUM_Y = 568
DETAIL_BAR_MIN = 4
BAND_X = 50
BAND_Y = 702
BAND_W = 1300
BAND_H = 210
BAND_PAD = 28
BAND_LABEL_Y = 750
BAND_CHIP_Y = 770
BAND_CHIPS_MAX = 6
BAND_SENTENCE_YS = (818, 866)
DETAIL_BLOCK_Y = 3
DETAIL_BLOCK_H = 70
DETAIL_BLOCK_W = 297
DETAIL_COBALT_X = 800
DETAIL_YELLOW_X = 1100

_DASHES = (chr(8211), chr(8212))


# --- Result types -----------------------------------------------------------


class FigureSet(TypedDict):
    """The two pictures of one pair."""

    card: str
    detail: str


class FigureLegend(TypedDict):
    """The legend a page prints beside the pictures."""

    summary: str
    card: str
    detail: str
    caption: str


class FigureLabels(TypedDict):
    """The fixed words drawn inside a detail figure, for the HTML twin of plan 08."""

    record_a: str
    record_b: str
    distinctive: str
    shared: str
    meaning: str
    wording: str
    none_shared: str


class FiguresResult(TypedDict):
    """The output of `build_figures`."""

    pairs: dict[str, FigureSet]
    legend: FigureLegend
    labels: FigureLabels


@dataclass(frozen=True)
class Lead:
    """Everything the two drawing functions need about one pair.

    Attributes:
        pair_id: The stable id of the pair (the only seed of the decoration).
        rank: The rank inside the engine.
        engine_name: The engine's short name in a sentence, for example `wording engine`.
        left_title: The title of record A, as the run holds it.
        right_title: The title of record B.
        words_a: The distinctive words of record A, at most 5.
        words_b: The distinctive words of record B, at most 5.
        shared: The words both records share, at most 6.
        meaning: The meaning score.
        wording: The wording score.
        meaning_text: The 4-decimal text of the meaning score, from the payload.
        wording_text: The 4-decimal text of the wording score, from the payload.
        lo: The low end of the engine's scale.
        hi: The high end of the engine's scale.
        agree: Both engines list the pair and a wording entry confirmed it.
        eureka: A record of the pair is a Potential eureka.
    """

    pair_id: str
    rank: int
    engine_name: str
    left_title: str
    right_title: str
    words_a: tuple[str, ...]
    words_b: tuple[str, ...]
    shared: tuple[str, ...]
    meaning: float
    wording: float
    meaning_text: str
    wording_text: str
    lo: float
    hi: float
    agree: bool
    eureka: bool


# --- Small helpers ----------------------------------------------------------


def round_half_up(value: float) -> int:
    """Return `value` rounded to the nearest whole number, halves up."""
    return int(math.floor(value + 0.5))


def _num(value: float) -> str:
    """Write a coordinate: a whole number when it is one, else a short decimal."""
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}"


def number_text(value: float) -> str:
    """Write a scale end in plain words: `0`, `1` or a 4-decimal number."""
    if value == int(value):
        return str(int(value))
    return f"{value:.4f}"


def fold_title(text: str) -> str:
    """Return a title with the en dash and the em dash replaced by a hyphen. No other change."""
    for dash in _DASHES:
        text = text.replace(dash, "-")
    return text


def wrap(text: str, width: int, lines: int) -> list[str]:
    """Wrap `text` to at most `lines` rows of at most `width` characters.

    Words are kept whole when they fit; a word longer than `width` is split by
    characters. When the text needs more rows than `lines`, the last kept row is cut and
    ends with three ASCII dots.
    """
    rows: list[str] = []
    current = ""
    for word in text.split():
        while len(word) > width:
            if current:
                rows.append(current)
                current = ""
            rows.append(word[:width])
            word = word[width:]
        if not word:
            continue
        if not current:
            current = word
        elif len(current) + 1 + len(word) <= width:
            current = f"{current} {word}"
        else:
            rows.append(current)
            current = word
    if current:
        rows.append(current)
    if len(rows) > lines:
        rows = rows[:lines]
        rows[-1] = rows[-1][: width - 3].rstrip() + "..."
    return rows


def seed(pair_id: str) -> bytes:
    """Return the sha256 digest of the pair id: the only seed of the decoration."""
    return hashlib.sha256(pair_id.encode("utf-8")).digest()


def scale_for(engine_key: str, shown_pairs: Iterable[Mapping[str, Any]]) -> tuple[float, float]:
    """Return the `(lo, hi)` scale of an engine's score bars.

    The wording engine declares a 0 to 1 scale. The unusual-pairs engine puts both scores
    on a common scale that is not 0 to 1, so its ends are the smallest and the largest of
    0, 1 and every wording or meaning score of its shown pairs.
    """
    if engine_key == ENGINE_WORDING:
        return (0.0, 1.0)
    values = [0.0, 1.0]
    for pair in shown_pairs:
        values.append(float(pair["wording"]))
        values.append(float(pair["meaning"]))
    return (min(values), max(values))


def bar_width(score: float, lo: float, hi: float, track: int, minimum: int) -> int:
    """Return the length of a score bar in whole units on a track of `track` units."""
    ratio = (score - lo) / (hi - lo) if hi > lo else 0.0
    ratio = min(1.0, max(0.0, ratio))
    return max(minimum, round_half_up(track * ratio))


def agree(pair_id: str, engines_of_pair: Iterable[str], confirmed_ids: Iterable[str]) -> bool:
    """Return True when both engines list the pair and a wording entry confirmed it."""
    return set(engines_of_pair) == set(ENGINE_KEYS) and pair_id in set(confirmed_ids)


def eureka(left_id: str, right_id: str, bridge_ids: Iterable[str]) -> bool:
    """Return True when a record of the pair is a Potential eureka."""
    bridges = set(bridge_ids)
    return left_id in bridges or right_id in bridges


def _engine_name(short_name: str) -> str:
    """Write the engine's short name inside a sentence: the first letter in lower case."""
    return short_name[:1].lower() + short_name[1:] if short_name else "engine"


# --- Element writer ---------------------------------------------------------


def _element(tag: str, attrs: Sequence[tuple[str, str]], text: str | None = None) -> str:
    parts = "".join(f' {name}="{value}"' for name, value in attrs)
    if text is None:
        return f"<{tag}{parts}/>"
    return f"<{tag}{parts}>{escape(text, quote=True)}</{tag}>"


def _shape(tag: str, cls: str, geometry: Sequence[tuple[str, float]]) -> str:
    fill_token, stroke_token, width, dash, opacity = _SHAPE_RULES[cls]
    attrs: list[tuple[str, str]] = [("class", cls)]
    attrs.extend((name, _num(value)) for name, value in geometry)
    if fill_token == "none":
        attrs.append(("fill", "none"))
    elif fill_token is not None:
        attrs.append(("fill", PALETTE[fill_token]))
    if stroke_token is not None:
        attrs.append(("stroke", PALETTE[stroke_token]))
        attrs.append(("stroke-width", str(width)))
    if dash is not None:
        attrs.append(("stroke-dasharray", dash))
    if opacity is not None:
        attrs.append(("opacity", opacity))
    return _element(tag, attrs)


def _rect(cls: str, x: float, y: float, width: float, height: float) -> str:
    return _shape("rect", cls, (("x", x), ("y", y), ("width", width), ("height", height)))


def _line(cls: str, x1: float, y1: float, x2: float, y2: float) -> str:
    return _shape("line", cls, (("x1", x1), ("y1", y1), ("x2", x2), ("y2", y2)))


def _text(classes: str, x: float, y: float, text: str) -> str:
    names = classes.split()
    size = next(_TEXT_SIZES[name] for name in names if name in _TEXT_SIZES)
    fill_token = next((_TEXT_FILLS[name] for name in names if name in _TEXT_FILLS), "ink")
    attrs = [
        ("class", classes),
        ("x", _num(x)),
        ("y", _num(y)),
        ("font-size", str(size)),
        ("fill", PALETTE[fill_token]),
    ]
    return _element("text", attrs, text)


def _svg(title: str, desc: str, body: Iterable[str]) -> str:
    head = _element(
        "svg",
        (
            ("xmlns", SVG_NS),
            ("viewBox", f"0 0 {CANVAS_W} {CANVAS_H}"),
            ("role", "img"),
            ("class", "hub-figure"),
        ),
    )[:-2]
    return (
        head
        + ">"
        + _element("title", (), title)
        + _element("desc", (), desc)
        + "".join(body)
        + "</svg>"
    )


def _ground() -> list[str]:
    return [
        _rect("f-paper", 0, 0, CANVAS_W, CANVAS_H),
        _rect(
            "f-frame",
            FRAME_INSET,
            FRAME_INSET,
            CANVAS_W - 2 * FRAME_INSET,
            CANVAS_H - 2 * FRAME_INSET,
        ),
    ]


def _words(words: Sequence[str]) -> str:
    return ", ".join(words) if words else "none"


def _scores_sentence(key: str, lead: Lead) -> str:
    return fill(
        FIGURE_COPY[key],
        x=lead.meaning_text,
        y=lead.wording_text,
        a=number_text(lead.lo),
        b=number_text(lead.hi),
    )


def _marks(lead: Lead) -> list[str]:
    sentences = []
    if lead.agree:
        sentences.append(FIGURE_COPY["G18.card.agree"])
    if lead.eureka:
        sentences.append(FIGURE_COPY["G18.card.eureka"])
    return sentences


# --- The card ---------------------------------------------------------------


def card_figure(lead: Lead) -> str:
    """Draw the card variant of a lead: no text, data shapes and seeded decoration."""
    digest = seed(lead.pair_id)
    rule_x = RULE_BASE + RULE_STEP * (digest[0] % RULE_CHOICES)
    body = _ground()
    body.append(_line("f-rule", rule_x, 0, rule_x, CANVAS_H))
    for index in range(FAN_LINES):
        y2 = FAN_Y_BASE + FAN_Y_STEP * (digest[index + 2] % FAN_Y_CHOICES) + FAN_Y_SLOPE * index
        body.append(_line("f-fan", FAN_ORIGIN[0], FAN_ORIGIN[1], rule_x - FAN_END_GAP, y2))
    for marker_x in MARKER_XS:
        body.append(_rect("f-panel", marker_x, MARKER_Y, MARKER_SIZE, MARKER_SIZE))
        body.append(_rect("f-ink", marker_x, MARKER_Y, MARKER_CORNER, MARKER_CORNER))
    body.append(_line("f-link", LINK_X1, LINK_Y, LINK_X2, LINK_Y))
    for tick_x in TICK_XS:
        body.append(_line("f-tick", tick_x, TICK_Y1, tick_x, TICK_Y2))
    meaning_w = bar_width(lead.meaning, lead.lo, lead.hi, CARD_TRACK, BAR_MIN)
    wording_w = bar_width(lead.wording, lead.lo, lead.hi, CARD_TRACK, BAR_MIN)
    body.append(_rect("f-blue", BAR_X, MEANING_BAR_Y, meaning_w, BAR_H))
    body.append(_rect("f-red", BAR_X, WORDING_BAR_Y, wording_w, BAR_H))
    for index in range(min(len(lead.shared), SQUARES_MAX)):
        body.append(
            _rect("f-ink", BAR_X + SQUARE_PITCH * index, SQUARE_Y, SQUARE_SIZE, SQUARE_SIZE)
        )
    block_x = rule_x + FRAME_INSET
    block_w = CANVAS_W - FRAME_INSET - block_x
    if lead.agree:
        body.append(_rect("f-blue", block_x, COBALT_BLOCK_Y, block_w, BLOCK_H))
    if lead.eureka:
        body.append(_rect("f-yellow", block_x, YELLOW_BLOCK_Y, block_w, BLOCK_H))
    title = fill(FIGURE_COPY["G18.card.title"], n=lead.rank, engine=lead.engine_name)
    shared = (
        fill(FIGURE_COPY["G18.card.shared"], n=len(lead.shared), list=", ".join(lead.shared))
        if lead.shared
        else FIGURE_COPY["G18.card.shared_none"]
    )
    desc = " ".join(
        [
            _scores_sentence("G18.card.scores", lead),
            shared,
            *_marks(lead),
            FIGURE_COPY["G18.card.decoration"],
            FIGURE_COPY["G18.card.limit"],
        ]
    )
    return _svg(title, desc, body)


# --- The detail -------------------------------------------------------------


def _chip_text(word: str) -> str:
    if len(word) > CHIP_TEXT_MAX:
        return word[: CHIP_TEXT_MAX - 3] + "..."
    return word


def _chips(
    words: Sequence[str],
    cls: str,
    x: float,
    y: float,
    right: float,
    bottom: float,
) -> list[str]:
    """Draw word chips from (x, y), wrapping before `right`. A chip below `bottom` is
    not drawn; the description still lists every word."""
    out: list[str] = []
    cx, cy = x, y
    for word in words:
        text = _chip_text(word)
        width = CHIP_CHAR * len(text) + CHIP_PAD
        if cx + width > right and cx > x:
            cx, cy = x, cy + CHIP_PITCH
        if cy + CHIP_H > bottom:
            break
        out.append(_rect(cls, cx, cy, width, CHIP_H))
        out.append(_text("f-mono f-chip-t", cx + CHIP_TEXT_DX, cy + CHIP_TEXT_DY, text))
        cx += width + CHIP_GAP
    return out


def _title_rows(title: str) -> list[str]:
    folded = fold_title(title)
    if not folded.strip():
        folded = FIGURE_COPY["G18.no_title"]
    return wrap(folded, TITLE_WIDTH, TITLE_LINES)


def _panel(x: float, label: str, title: str, words: Sequence[str]) -> list[str]:
    out = [
        _rect("f-panel", x, PANEL_Y, PANEL_W, PANEL_H),
        _rect("f-ink", x, PANEL_Y, PANEL_W, STRIP_H),
        _text("f-mono f-soft", x + PAD, PANEL_LABEL_Y, label),
    ]
    for index, row in enumerate(_title_rows(title)):
        out.append(_text("f-title", x + PAD, TITLE_Y + TITLE_PITCH * index, row))
    out.append(_text("f-mono f-soft", x + PAD, WORDS_LABEL_Y, FIGURE_COPY["G18.label.distinctive"]))
    out.extend(_chips(words, "f-chip", x + PAD, CHIP_Y, x + PANEL_W - PAD, PANEL_Y + PANEL_H - PAD))
    return out


def _score_column(lead: Lead) -> list[str]:
    meaning_w = bar_width(lead.meaning, lead.lo, lead.hi, TRACK_W, DETAIL_BAR_MIN)
    wording_w = bar_width(lead.wording, lead.lo, lead.hi, TRACK_W, DETAIL_BAR_MIN)
    return [
        _line("f-link", DETAIL_LINK_X1, DETAIL_LINK_Y, DETAIL_LINK_X2, DETAIL_LINK_Y),
        _text("f-mono f-soft", COLUMN_X, MEANING_LABEL_Y, FIGURE_COPY["G18.label.meaning"]),
        _rect("f-track", COLUMN_X, MEANING_TRACK_Y, TRACK_W, TRACK_H),
        _rect("f-blue", COLUMN_X, MEANING_TRACK_Y, meaning_w, TRACK_H),
        _text("f-num f-blue-t", COLUMN_X, MEANING_NUM_Y, format(lead.meaning, ".2f")),
        _text("f-mono f-soft", COLUMN_X, WORDING_LABEL_Y, FIGURE_COPY["G18.label.wording"]),
        _rect("f-track", COLUMN_X, WORDING_TRACK_Y, TRACK_W, TRACK_H),
        _rect("f-red", COLUMN_X, WORDING_TRACK_Y, wording_w, TRACK_H),
        _text("f-num f-red-t", COLUMN_X, WORDING_NUM_Y, format(lead.wording, ".2f")),
    ]


def _band(shared: Sequence[str]) -> list[str]:
    out = [
        _rect("f-band", BAND_X, BAND_Y, BAND_W, BAND_H),
        _text("f-mono f-band-t", BAND_X + BAND_PAD, BAND_LABEL_Y, FIGURE_COPY["G18.label.shared"]),
    ]
    if shared:
        out.extend(
            _chips(
                shared[:BAND_CHIPS_MAX],
                "f-chip-on",
                BAND_X + BAND_PAD,
                BAND_CHIP_Y,
                BAND_X + BAND_W - BAND_PAD,
                BAND_Y + BAND_H - PAD,
            )
        )
    else:
        sentences = FIGURE_COPY["G18.label.none_shared"].split(". ")
        for index, sentence in enumerate(sentences):
            text = sentence if sentence.endswith(".") else sentence + "."
            out.append(_text("f-body f-band-t", BAND_X + BAND_PAD, BAND_SENTENCE_YS[index], text))
    return out


def detail_figure(lead: Lead) -> str:
    """Draw the detail variant of a lead: titles, words, scores and the shared band."""
    body = _ground()
    body.extend(
        _panel(PANEL_XS[0], FIGURE_COPY["G18.label.record_a"], lead.left_title, lead.words_a)
    )
    body.extend(
        _panel(PANEL_XS[1], FIGURE_COPY["G18.label.record_b"], lead.right_title, lead.words_b)
    )
    body.extend(_score_column(lead))
    body.extend(_band(lead.shared))
    if lead.agree:
        body.append(
            _rect("f-blue", DETAIL_COBALT_X, DETAIL_BLOCK_Y, DETAIL_BLOCK_W, DETAIL_BLOCK_H)
        )
    if lead.eureka:
        body.append(
            _rect("f-yellow", DETAIL_YELLOW_X, DETAIL_BLOCK_Y, DETAIL_BLOCK_W, DETAIL_BLOCK_H)
        )
    title = fill(FIGURE_COPY["G18.detail.title"], n=lead.rank, engine=lead.engine_name)
    shared = (
        fill(FIGURE_COPY["G18.detail.shared"], list=", ".join(lead.shared))
        if lead.shared
        else FIGURE_COPY["G18.detail.shared_none"]
    )
    desc = " ".join(
        [
            fill(FIGURE_COPY["G18.detail.record_a"], title=_desc_title(lead.left_title)),
            fill(FIGURE_COPY["G18.detail.record_b"], title=_desc_title(lead.right_title)),
            fill(FIGURE_COPY["G18.detail.words_a"], list=_words(lead.words_a)),
            fill(FIGURE_COPY["G18.detail.words_b"], list=_words(lead.words_b)),
            _scores_sentence("G18.detail.scores", lead),
            shared,
            *_marks(lead),
            FIGURE_COPY["G18.detail.limit"],
        ]
    )
    return _svg(title, desc, body)


def _desc_title(title: str) -> str:
    folded = fold_title(title).strip()
    return folded if folded else FIGURE_COPY["G18.no_title"]


# --- Legend, labels and the whole payload section ---------------------------


def legend_texts() -> FigureLegend:
    """Return the legend strings a page prints beside the pictures."""
    return {
        "summary": FIGURE_COPY["G18.legend.summary"],
        "card": FIGURE_COPY["G18.legend.card"],
        "detail": FIGURE_COPY["G18.legend.detail"],
        "caption": FIGURE_COPY["G18.legend.caption"],
    }


def label_texts() -> FigureLabels:
    """Return the fixed words drawn inside a detail figure."""
    return {
        "record_a": FIGURE_COPY["G18.label.record_a"],
        "record_b": FIGURE_COPY["G18.label.record_b"],
        "distinctive": FIGURE_COPY["G18.label.distinctive"],
        "shared": FIGURE_COPY["G18.label.shared"],
        "meaning": FIGURE_COPY["G18.label.meaning"],
        "wording": FIGURE_COPY["G18.label.wording"],
        "none_shared": FIGURE_COPY["G18.label.none_shared"],
    }


def build_figures(payload: Mapping[str, Any]) -> FiguresResult:
    """Draw the card and the detail of every pair of the payload.

    Reads `pairs`, `records`, `engines` and `terms` of the payload. Every input is sorted
    by key or id before use, so the order of the payload lists cannot change a byte.

    Args:
        payload: The hub payload, with the `terms` of plan 02 and without `figures`.

    Returns:
        `{"pairs": {key: {"card", "detail"}}, "legend": {...}, "labels": {...}}`.
    """
    pairs = sorted(payload["pairs"], key=lambda item: str(item["key"]))
    records = {str(record["id"]): record for record in payload["records"]}
    terms = payload.get("terms") or {"records": {}, "pairs": {}}
    word_lists: Mapping[str, Sequence[str]] = terms.get("records", {})
    shared_lists: Mapping[str, Sequence[str]] = terms.get("pairs", {})
    engines_of: dict[str, set[str]] = {}
    confirmed: set[str] = set()
    for pair in pairs:
        engines_of.setdefault(str(pair["pair_id"]), set()).add(str(pair["engine"]))
        if pair["engine"] == ENGINE_WORDING and pair.get("confirmed") is True:
            confirmed.add(str(pair["pair_id"]))
    bridges = sorted(rid for rid, record in records.items() if record.get("bridge"))
    scales = {
        key: scale_for(
            key, [pair for pair in pairs if pair["engine"] == key and not pair.get("weak", False)]
        )
        for key in (ENGINE_UNUSUAL, ENGINE_WORDING)
    }
    engine_names = {key: _engine_name(str(payload["engines"][key]["short_name"])) for key in scales}
    out: dict[str, FigureSet] = {}
    for pair in pairs:
        pair_id = str(pair["pair_id"])
        left_id, right_id = str(pair["left"]["id"]), str(pair["right"]["id"])
        lo, hi = scales[str(pair["engine"])]
        lead = Lead(
            pair_id=pair_id,
            rank=int(pair["rank"]),
            engine_name=engine_names[str(pair["engine"])],
            left_title=str(records[left_id]["title"]),
            right_title=str(records[right_id]["title"]),
            words_a=tuple(word_lists.get(left_id, ())),
            words_b=tuple(word_lists.get(right_id, ())),
            shared=tuple(shared_lists.get(pair_id, ())),
            meaning=float(pair["meaning"]),
            wording=float(pair["wording"]),
            meaning_text=str(pair["meaning_text"]),
            wording_text=str(pair["wording_text"]),
            lo=lo,
            hi=hi,
            agree=agree(pair_id, engines_of[pair_id], confirmed),
            eureka=eureka(left_id, right_id, bridges),
        )
        out[str(pair["key"])] = {"card": card_figure(lead), "detail": detail_figure(lead)}
    return {"pairs": out, "legend": legend_texts(), "labels": label_texts()}


# --- Safety check -----------------------------------------------------------


def _local(tag: str) -> str:
    return tag.split("}", 1)[1] if tag.startswith("{") else tag


def figure_problems(svg: object) -> list[str]:
    """Return plain sentences for every safety problem of a figure. Never raises.

    Checks: a string that starts with `<svg ` and ends with `</svg>`; no declaration,
    comment, processing instruction, image, script or foreignObject text; well-formed
    XML in the SVG namespace; only the 7 tags and the 21 attributes; `role="img"`; a
    `title` then a `desc` as the first children; no `id`; text only inside `text`,
    `title` and `desc`.
    """
    if not isinstance(svg, str):
        return ["The figure is not a string."]
    if len(svg) > _MAX_PARSE_CHARS:
        return [f"The figure is longer than {_MAX_PARSE_CHARS} characters."]
    problems: list[str] = []
    if not svg.startswith("<svg "):
        problems.append("The figure does not start with an svg tag.")
    if not svg.endswith("</svg>"):
        problems.append("The figure does not end with the svg closing tag.")
    lowered = svg.lower()
    for needle, name in _FORBIDDEN_TEXT:
        if needle in lowered:
            problems.append(f"The figure holds {name}.")
    if problems:
        return problems
    try:
        root = ElementTree.fromstring(svg)
    except ElementTree.ParseError:
        return ["The figure is not well-formed XML."]
    if root.tag != f"{{{SVG_NS}}}svg":
        problems.append("The root element is not svg in the SVG namespace.")
    if root.get("role") != "img":
        problems.append("The root element does not have role img.")
    children = list(root)
    if len(children) < 2 or _local(children[0].tag) != "title" or _local(children[1].tag) != "desc":
        problems.append("The first two children are not a title and a desc.")
    for element in root.iter():
        tag = _local(element.tag)
        if not element.tag.startswith(f"{{{SVG_NS}}}"):
            problems.append(f"The element {tag} is outside the SVG namespace.")
        if tag not in FIGURE_TAGS:
            problems.append(f"The element {tag} is not allowed.")
        for name in element.attrib:
            if name == "id":
                problems.append("An element has an id attribute.")
            elif name not in FIGURE_ATTRS:
                problems.append(f"The attribute {_local(name)} is not allowed.")
        if tag not in _TEXT_TAGS and (element.text or "").strip():
            problems.append(f"The element {tag} holds text.")
        if (element.tail or "").strip():
            problems.append(f"Text follows the element {tag}.")
    return problems
