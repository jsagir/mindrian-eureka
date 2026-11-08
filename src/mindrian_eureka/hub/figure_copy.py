"""The strings of the lead figures (family G18 of the copy deck numbering).

These strings are not part of `deck.py`: they travel in the payload, inside `figures`,
so a locked hub keeps them with the data. The titles and descriptions are filled by the
generator with real numbers and words from the run. The labels are the fixed words
drawn inside a detail figure. The legends are the words a page prints beside the
pictures. Every string is ASCII, holds no dash character and uses only the slot names
`engine`, `n`, `x`, `y`, `z`, `a`, `b`, `list` and `title` of the deck.

Import rule: the standard library and `..run.contracts` for `LABEL` only.
"""

from __future__ import annotations

from ..run.contracts import LABEL

FIGURE_SLOTS: frozenset[str] = frozenset({"engine", "n", "x", "y", "z", "a", "b", "list", "title"})
"""The slot names a figure string may use. A subset of the deck's `SLOT_NAMES`."""

FIGURE_COPY: dict[str, str] = {
    # --- the card (the words of each record inside; the description repeats them) ---
    "G18.card.title": (
        "Pair {n} of the {engine}: the words of each record, the scores and the shared words"
    ),
    "G18.card.scores": "Meaning score {x} and wording score {y}, on a scale from {a} to {b}.",
    "G18.card.words_a": "Record A words: {list}.",
    "G18.card.words_b": "Record B words: {list}.",
    "G18.card.shared": "{n} shared distinctive words: {list}.",
    "G18.card.shared_none": "No distinctive word is shared.",
    "G18.card.agree": (
        "Both engines list the pair and the second signal confirmed it. "
        "The cobalt block marks that."
    ),
    "G18.card.eureka": "A record of the pair is a Potential eureka. The yellow block marks that.",
    "G18.card.rule": "The vertical rule is structure, not data.",
    "G18.card.limit": (
        "This is a screening picture, not evidence. It does not show that the pair is new, "
        "wanted or valuable. It is a " + LABEL + "."
    ),
    # --- the detail (text inside) ----------------------------------------------
    "G18.detail.title": (
        "The core of pair {n} of the {engine}: two records, their words and what they share"
    ),
    "G18.detail.record_a": "Record A: {title}.",
    "G18.detail.record_b": "Record B: {title}.",
    "G18.detail.words_a": "Distinctive words of record A: {list}.",
    "G18.detail.words_b": "Distinctive words of record B: {list}.",
    "G18.detail.scores": "Meaning score {x} and wording score {y}, on a scale from {a} to {b}.",
    "G18.detail.shared": "Words that both records share: {list}.",
    "G18.detail.shared_none": "No distinctive word is shared. The link is in meaning only.",
    "G18.detail.limit": (
        "The words are a screening aid, not evidence. This does not show that the pair is "
        "new, wanted or valuable. It is a " + LABEL + "."
    ),
    # --- the labels drawn inside a detail figure --------------------------------
    "G18.label.record_a": "RECORD A",
    "G18.label.record_b": "RECORD B",
    "G18.label.distinctive": "DISTINCTIVE WORDS",
    "G18.label.shared": "WORDS BOTH RECORDS SHARE",
    "G18.label.meaning": "MEANING",
    "G18.label.wording": "WORDING",
    "G18.label.none_shared": "No distinctive word is shared. The link is in meaning only.",
    "G18.no_title": "(no title)",
    # --- the legend a page prints beside the pictures ---------------------------
    "G18.legend.summary": "How to read the small pictures",
    "G18.legend.caption": (
        "Small words: the most distinctive words of each record, record A at the left and "
        "record B at the right. Chip on the dashed line: the words both records share. "
        "Cobalt bar: meaning score. Red bar: wording score. Ink squares: one for each shared "
        "distinctive word. Cobalt block: both engines list the pair and the second signal "
        "confirmed it. Yellow block: a Potential eureka."
    ),
    "G18.legend.card": (
        "Each small picture shows one pair. The two squares at the top, record A at the left "
        "and record B at the right, stand for the two records and the dashed line between "
        "them is the proposed pair. Under each square are the most distinctive words of that "
        "record, and the chip on the dashed line holds the words both records share. The "
        "cobalt bar is the meaning score and the red bar is the wording score, on the scale "
        "of the engine that ranks the pair. Each ink square is one distinctive word that both "
        "records share. A cobalt block means that both engines list the pair and the second "
        "signal confirmed it. A yellow block means that one record is a Potential eureka. "
        "Distinctive words are a screening aid, not evidence. The picture does not show that "
        "a pair is new, wanted or valuable."
    ),
    "G18.legend.detail": (
        "The big picture shows the core of one pair. Each record has its title and its 5 "
        "most distinctive words, the words that stand out in this collection. The cobalt bar "
        "is the meaning score and the red bar is the wording score. The black band lists the "
        "distinctive words that both records share. Distinctive words are a screening aid, "
        "not evidence. The picture does not show that a pair is new, wanted or valuable."
    ),
}
