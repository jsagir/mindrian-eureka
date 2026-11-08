"""The distinctive words of each record of a run, and the words two records share.

Import rule: the standard library only. This module imports no other hub module. It
takes any object with the attributes `id`, `title` and `text`.

The words are a screening aid for a person who decides where to start reading. They are
never evidence. A word list makes no claim of novelty, demand or value. The rule is
written in `docs/brand/hub-terms-rules.md` and pinned by `tests/test_hub_terms.py`.

Deterministic: the same records give the same lists. No clock, no random source, no file,
no network and no model is used. Every input is sorted by id before use, so the order of
the input cannot change the output. Scores are rounded to `SCORE_DECIMALS` before the sort,
so a last-bit difference of a platform cannot change an order. Ties are broken by the word.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from typing import Protocol, TypedDict

TOP_N = 5
"""The number of distinctive words shown for a record."""

DEPTH = 30
"""The length of the depth list of a record, from which the shared words of a pair come."""

SHARED_MAX = 6
"""The largest number of shared words of a pair."""

SCORE_DECIMALS = 9
"""Scores are rounded to this many decimals before the sort."""

# Source: the owner brief of 2026-11-08 and the prototype build script (build_preview2.py,
# outside the repo), as item 7 of plan 02.3.1-02. Lower case, no hyphen, 180 words or fewer.
STOP_WORDS: frozenset[str] = frozenset(
    (
        "a about above after again all also an and any are as at be because been before being "
        "between both but by can could did do does doing down during each few for from further "
        "had has have having he her here hers him his how i if in into is it its just may more "
        "most much must no nor not now of off on once only or other our out over own same she "
        "should so some such than that the their them then there these they this those through "
        "to too under until up use used uses using very was we were what when where which while "
        "who whom why will with would you your paper papers show shows shown present presents "
        "propose proposed approach method methods result results based new however thus one two "
        "three first second via within without cannot study studies work works given general "
        "case cases number set sets problem problems model models"
    ).split()
)

_TOKEN = re.compile(r"[a-z][a-z-]{3,}")
_ES_ENDINGS = ("ses", "xes", "zes", "ches", "shes")
_KEEP_S_ENDINGS = ("ss", "us", "is")


class RecordLike(Protocol):
    """Any object with a record id, a title and a text."""

    @property
    def id(self) -> str: ...

    @property
    def title(self) -> str: ...

    @property
    def text(self) -> str: ...


class TermsResult(TypedDict):
    """The output of `build_terms`.

    Attributes:
        records: The record id to its first `TOP_N` distinctive words, best first.
        pairs: The pair id to the words both records share, at most `SHARED_MAX`.
    """

    records: dict[str, list[str]]
    pairs: dict[str, list[str]]


def fold(word: str) -> str:
    """Fold a light plural (item 3 of the rule). The word is already lower case.

    In this order: `ies` to `y` when the length is above 5; else drop `es` after `ses`,
    `xes`, `zes`, `ches` or `shes` when the length is above 5; else drop a final `s` that
    does not follow `s`, `u` or `i` when the length is above 4.
    """
    if word.endswith("ies") and len(word) > 5:
        return word[:-3] + "y"
    if word.endswith(_ES_ENDINGS) and len(word) > 5:
        return word[:-2]
    if word.endswith("s") and not word.endswith(_KEEP_S_ENDINGS) and len(word) > 4:
        return word[:-1]
    return word


def tokens(text: str) -> list[str]:
    """Return the tokens of a text (items 1 and 2 of the rule), in text order.

    A token is a run of a letter and 3 or more letters or hyphens, in lower case, with the
    hyphens of both ends removed and the plural folded. A token in `STOP_WORDS` or with 3
    letters or fewer is dropped. Text in another script and digits give no token.
    """
    out: list[str] = []
    for match in _TOKEN.findall(text.lower()):
        word = fold(match.strip("-"))
        if len(word) > 3 and word not in STOP_WORDS:
            out.append(word)
    return out


def record_text(record: RecordLike) -> str:
    """Return the text of a record for the rule: its title, one space, its text."""
    return f"{record.title} {record.text}"


def rank_records(records: Sequence[RecordLike]) -> dict[str, list[str]]:
    """Return, for each record id, every word of the record ordered best first.

    Items 4 and 5 of the rule: `score = tf * log((N + 1) / (df + 0.5))`, with the natural
    logarithm; the sort key is `(-round(score, SCORE_DECIMALS), word)`.
    """
    by_id = {record.id: record for record in sorted(records, key=lambda item: item.id)}
    counts = {rid: Counter(tokens(record_text(record))) for rid, record in by_id.items()}
    document_frequency: Counter[str] = Counter()
    for count in counts.values():
        document_frequency.update(count.keys())
    total = len(by_id)
    ranked: dict[str, list[str]] = {}
    for rid, count in counts.items():
        scores = {
            word: round(
                tf * math.log((total + 1) / (document_frequency[word] + 0.5)), SCORE_DECIMALS
            )
            for word, tf in count.items()
        }
        ranked[rid] = sorted(scores, key=lambda word: (-scores[word], word))
    return ranked


def shared_words(rank_a: Sequence[str], rank_b: Sequence[str]) -> list[str]:
    """Return the words in the depth lists of both records (item 6 of the rule).

    The depth list is the first `DEPTH` words. The order is by the larger rank of the two
    (0 is first), then by the word. At most `SHARED_MAX` words are kept.
    """
    depth_a = {word: rank for rank, word in enumerate(rank_a[:DEPTH])}
    depth_b = {word: rank for rank, word in enumerate(rank_b[:DEPTH])}
    both = [word for word in depth_a if word in depth_b]
    both.sort(key=lambda word: (max(depth_a[word], depth_b[word]), word))
    return both[:SHARED_MAX]


def build_terms(
    records: Sequence[RecordLike], pairs: Iterable[tuple[str, str, str]]
) -> TermsResult:
    """Return the distinctive words of every record and the shared words of every pair.

    Args:
        records: Objects with `id`, `title` and `text`. Any order.
        pairs: Triples `(pair_id, left_id, right_id)`. Any order. The same pair id given
            twice (one from each engine) appears once in the output.

    Returns:
        `{"records": {id: first TOP_N words}, "pairs": {pair_id: shared words}}`. A record
        with no token maps to an empty list. A pair id whose record is unknown maps to an
        empty list.
    """
    ranked = rank_records(records)
    unique_pairs = sorted({(pair_id, left, right) for pair_id, left, right in pairs})
    pair_words: dict[str, list[str]] = {}
    for pair_id, left, right in unique_pairs:
        if pair_id in pair_words:
            continue
        pair_words[pair_id] = shared_words(ranked.get(left, []), ranked.get(right, []))
    return {
        "records": {rid: words[:TOP_N] for rid, words in ranked.items()},
        "pairs": pair_words,
    }
