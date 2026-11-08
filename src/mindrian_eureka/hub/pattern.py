"""Read a finished run as deck keys and sourced values (the run reading band).

Phase 2.3.1, D-04 (HUB-07). `describe_run` is a pure function of the payload: the same
payload gives the same lines. Every value is a count that the payload holds or an engine
short name that the payload holds. The function reads no clock, no random source and no
network. It uses no numeric literal other than 0, 1 and 2, so it adds no threshold of its
own. The band makes no claim of novelty, evidence, demand or value; the last line is the
fixed limit sentence G16.

Import rule: the standard library and `.contracts` only. No numpy, no `.deck`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .contracts import (
    ENGINE_KEYS,
    ENGINE_UNUSUAL,
    ENGINE_WORDING,
    PATTERN_STATES,
    PatternLine,
    PayloadPattern,
)

STATE_NONE, STATE_HIDDEN, STATE_SINGLE, STATE_GROUPED = PATTERN_STATES

# The pair classes of the run outcome rule (Phase 2.2) and the deck slot of each count.
_CLASS_SLOTS: tuple[tuple[str, str], ...] = (
    ("cross", "a"),
    ("open_open", "b"),
    ("licensed_licensed", "n"),
)


def _line(key: str, **values: int | str) -> PatternLine:
    return {"key": key, "values": dict(values)}


def _both_engines(pairs: list[Mapping[str, Any]]) -> int:
    """Count the distinct pair ids that have an entry in the list of each engine."""
    engines_by_pair: dict[str, set[str]] = {}
    for pair in pairs:
        engines_by_pair.setdefault(str(pair["pair_id"]), set()).add(str(pair["engine"]))
    return sum(
        1
        for engines in engines_by_pair.values()
        if all(key in engines for key in ENGINE_KEYS)
    )


def describe_run(payload: Mapping[str, Any]) -> PayloadPattern:
    """Return the state and the lines of the run reading band for `payload`.

    States, in the order of the rules:
    `none` when no pair was ranked; `hidden` when pairs were ranked and no record is in a
    pair that is shown; `grouped` when there are 2 or more neighborhoods or at least 1
    bridge; `single` otherwise. In `none`, `hidden` and `single` the band says in words
    that the run shows no grouping to read.

    Args:
        payload: A payload built by `build_payload` (the `pattern` key is not read).

    Returns:
        The pattern: `state` and `lines`. Each line is a deck key and its slot values.
    """
    counts = payload["counts"]
    pair_counts = counts["pairs"]
    total = sum(int(pair_counts[key]) for key in ENGINE_KEYS)
    if total == 0:
        return {"state": STATE_NONE, "lines": [_line("G17.none"), _line("G16")]}
    if int(counts["records_in_visible_pairs"]) == 0:
        return {"state": STATE_HIDDEN, "lines": [_line("G17.hidden"), _line("G16")]}

    pairs: list[Mapping[str, Any]] = list(payload["pairs"])
    hoods: list[Mapping[str, Any]] = list(payload["hoods"])
    bridges: list[Mapping[str, Any]] = list(payload["bridges"])
    lines: list[PatternLine] = [
        _line(
            "G17.read",
            records=int(counts["records"]),
            a=int(pair_counts[ENGINE_UNUSUAL]),
            b=int(pair_counts[ENGINE_WORDING]),
        )
    ]
    both = _both_engines(pairs)
    if both > 0:
        lines.append(_line("G17.both", n=both))
    lines.append(
        _line(
            "G17.spread",
            a=int(counts["records_in_visible_pairs"]),
            b=int(counts["records_in_no_pair"]),
        )
    )
    if len(hoods) >= 2 or len(bridges) >= 1:
        state = STATE_GROUPED
        # Hoods are sorted by size, largest first, so the first one is the largest.
        largest = int(hoods[0]["size"]) if hoods else 0
        lines.append(_line("G17.hoods", n=len(hoods), a=largest))
        if bridges:
            lines.append(_line("G17.bridges", n=len(bridges)))
        else:
            lines.append(_line("Gr09"))
    else:
        state = STATE_SINGLE
        lines.append(_line("G17.single"))

    weak = int(counts["weak_pairs"])
    if weak > 0:
        lines.append(_line("G17.weak", n=weak))
    identical = int(payload["data_check"]["identical_records"])
    if identical > 0:
        lines.append(_line("G17.copies", n=identical))
    if payload.get("has_pair_classes"):
        by_class = {name: 0 for name, _slot in _CLASS_SLOTS}
        for pair in pairs:
            if pair.get("weak"):
                continue
            pair_class = pair.get("pair_class")
            if isinstance(pair_class, str) and pair_class in by_class:
                by_class[pair_class] += 1
        lines.append(_line("G17.classes", **{slot: by_class[name] for name, slot in _CLASS_SLOTS}))
    engines = payload["engines"]
    for key in ENGINE_KEYS:
        engine = engines[key]
        if engine["top_k_reached"]:
            lines.append(
                _line("G17.top_k", engine=str(engine["short_name"]), n=int(engine["top_k"]))
            )
    lines.append(_line("G16"))
    return {"state": state, "lines": lines}
