"""Validate the hub payload's labels, source links, authored copy, words and figures.

Import rule: the standard library, `.contracts`, `.deck` (the key set of the run
reading band) and `.figures` (the safety check and the size caps of a figure) only. No
numpy.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import NotRequired, get_origin, get_type_hints

from ..run.contracts import LABEL
from .contracts import (
    ENGINE_KEYS,
    PATTERN_STATES,
    READING_KINDS,
    PairSide,
    PatternLine,
    Payload,
    PayloadBridge,
    PayloadCounts,
    PayloadDataCheck,
    PayloadEngine,
    PayloadFigures,
    PayloadFigureSet,
    PayloadGraph,
    PayloadHood,
    PayloadLabels,
    PayloadLegend,
    PayloadPair,
    PayloadPattern,
    PayloadRecord,
    PayloadTerms,
    has_dash,
    has_internal_name,
)
from .deck import DECK
from .figures import CARD_MAX_BYTES, DETAIL_MAX_BYTES, figure_problems

_BAD_LINK_PREFIXES = ("http:", "https:", "javascript:", "//")
# A distinctive word: lower-case letters and hyphens, 4 characters or more (plan 02).
_WORD = re.compile(r"^[a-z][a-z-]{3,}$")
_TERM_LIMITS = {"records": 5, "pairs": 6}


def _typed_dict_keys(shape: object) -> tuple[set[str], set[str]]:
    """Return the required keys and the optional (`NotRequired`) keys of a TypedDict.

    The contracts module keeps its annotations as strings, so `__optional_keys__` is
    empty there; `get_type_hints` evaluates them and keeps the `NotRequired` wrapper.
    """
    try:
        hints: Mapping[str, object] = get_type_hints(shape, include_extras=True)
    except (NameError, TypeError):
        annotations = getattr(shape, "__annotations__", {})
        hints = annotations if isinstance(annotations, dict) else {}
    required: set[str] = set()
    optional: set[str] = set()
    for key, hint in hints.items():
        if get_origin(hint) is NotRequired:
            optional.add(key)
        else:
            required.add(key)
    return required, optional


def _check_keys(
    value: object, shape: object, path: str, problems: list[str]
) -> Mapping[str, object] | None:
    if not isinstance(value, Mapping):
        problems.append(f"{path} is not an object with the required keys.")
        return None
    required, optional = _typed_dict_keys(shape)
    actual = set(value)
    missing = sorted(required - actual)
    extra = sorted(actual - required - optional)
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append(f"missing {', '.join(missing)}")
        if extra:
            details.append(f"extra {', '.join(extra)}")
        problems.append(f"{path} keys differ from its typed shape: {'; '.join(details)}.")
    return value


def _check_copy(path: str, value: object, problems: list[str]) -> None:
    if not isinstance(value, str):
        return
    if has_dash(value):
        problems.append(f"{path} contains a dash character.")
    if has_internal_name(value):
        problems.append(f"{path} contains an internal name.")


def _check_link(path: str, value: object, problems: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        problems.append(f"{path} has no source link.")
    elif value.lower().startswith(_BAD_LINK_PREFIXES):
        problems.append(f"{path} has a disallowed source link: {value}.")


def _objects(value: object) -> Sequence[object]:
    return value if isinstance(value, list) else ()


def _check_pattern(value: object, problems: list[str]) -> None:
    """Check the run reading band (Phase 2.3.1, D-04): shape, state, keys and values."""
    pattern = _check_keys(value, PayloadPattern, "pattern", problems)
    if pattern is None:
        return
    if pattern.get("state") not in PATTERN_STATES:
        problems.append(f"pattern state is not one of {', '.join(PATTERN_STATES)}.")
    for index, item in enumerate(_objects(pattern.get("lines"))):
        path = f"pattern lines[{index}]"
        line = _check_keys(item, PatternLine, path, problems)
        if line is None:
            continue
        key = line.get("key")
        if key not in DECK:
            problems.append(f"{path} key {key} is not a deck key.")
        values = line.get("values")
        if not isinstance(values, Mapping):
            problems.append(f"{path} values is not an object.")
            continue
        for slot, slot_value in values.items():
            if isinstance(slot_value, bool) or not isinstance(slot_value, int | str):
                problems.append(f"{path} value {slot} is not an int or a string.")
            _check_copy(f"{path} value {slot}", slot_value, problems)


def _check_terms(
    value: object, record_ids: set[str], pair_ids: set[str], problems: list[str]
) -> None:
    """Check the distinctive words (Phase 2.3.1 plan 02): ids, list lengths and word shape."""
    terms = _check_keys(value, PayloadTerms, "terms", problems)
    if terms is None:
        return
    known = {"records": record_ids, "pairs": pair_ids}
    for section, limit in _TERM_LIMITS.items():
        lists = terms.get(section)
        if not isinstance(lists, Mapping):
            problems.append(f"terms {section} is not an object.")
            continue
        for item_id, words in lists.items():
            path = f"terms {section} {item_id}"
            if item_id not in known[section]:
                problems.append(f"{path} is not an id of the payload.")
            if not isinstance(words, list):
                problems.append(f"{path} is not a list of words.")
                continue
            if len(words) > limit:
                problems.append(f"{path} holds more than {limit} words.")
            for word in words:
                if not isinstance(word, str) or not _WORD.match(word):
                    problems.append(f"{path} holds a word that is not lower-case letters.")
                    break


def _check_figure(path: str, value: object, cap: int, problems: list[str]) -> None:
    if not isinstance(value, str):
        problems.append(f"{path} is not a string.")
        return
    size = len(value.encode("utf-8"))
    if size > cap:
        problems.append(f"{path} is {size} bytes, above the cap of {cap} bytes.")
        return
    for sentence in figure_problems(value):
        problems.append(f"{path}: {sentence}")


def _check_figures(value: object, pair_keys: set[str], problems: list[str]) -> None:
    """Check the figures (Phase 2.3.1 plan 04): key set, safety, size, legend and labels."""
    figures = _check_keys(value, PayloadFigures, "figures", problems)
    if figures is None:
        return
    sets = figures.get("pairs")
    if not isinstance(sets, Mapping):
        problems.append("figures pairs is not an object.")
    else:
        missing = sorted(pair_keys - set(sets))
        extra = sorted(set(sets) - pair_keys)
        if missing or extra:
            details: list[str] = []
            if missing:
                details.append(f"missing {', '.join(missing)}")
            if extra:
                details.append(f"extra {', '.join(extra)}")
            problems.append(f"figures pairs keys differ from the pair keys: {'; '.join(details)}.")
        for key in sorted(sets):
            figure_set = _check_keys(sets[key], PayloadFigureSet, f"figure {key}", problems)
            if figure_set is None:
                continue
            _check_figure(f"figure {key} card", figure_set.get("card"), CARD_MAX_BYTES, problems)
            _check_figure(
                f"figure {key} detail", figure_set.get("detail"), DETAIL_MAX_BYTES, problems
            )
    for section, shape in (("legend", PayloadLegend), ("labels", PayloadLabels)):
        strings = _check_keys(figures.get(section), shape, f"figures {section}", problems)
        if strings is None:
            continue
        for name, text in strings.items():
            if not isinstance(text, str) or not text:
                problems.append(f"figures {section} {name} is not a string.")
            _check_copy(f"figures {section} {name}", text, problems)


def verify_payload(payload: Payload) -> list[str]:
    """Return deterministic problems with payload shape, labels, links or copy.

    Args:
        payload: Payload built by `build_payload`.

    Returns:
        Plain problem sentences, or an empty list when all checks pass.
    """
    problems: list[str] = []
    top = _check_keys(payload, Payload, "payload", problems)
    if top is None:
        return problems

    counts = _check_keys(top.get("counts"), PayloadCounts, "counts", problems)
    if counts is not None:
        pair_counts = counts.get("pairs")
        if not isinstance(pair_counts, Mapping):
            problems.append("counts.pairs is not an object.")
        elif set(pair_counts) != set(ENGINE_KEYS):
            missing = sorted(set(ENGINE_KEYS) - set(pair_counts))
            extra = sorted(set(pair_counts) - set(ENGINE_KEYS))
            problems.append(
                "counts.pairs keys differ from the required engines: "
                f"missing {', '.join(missing)}; extra {', '.join(extra)}."
            )

    engines = top.get("engines")
    if not isinstance(engines, Mapping):
        problems.append("engines is not an object.")
    else:
        missing_engines = sorted(set(ENGINE_KEYS) - set(engines))
        extra_engines = sorted(set(engines) - set(ENGINE_KEYS))
        if missing_engines or extra_engines:
            problems.append(
                "engine keys differ from the required engines: "
                f"missing {', '.join(missing_engines)}; extra {', '.join(extra_engines)}."
            )
        for engine_key in ENGINE_KEYS:
            engine = _check_keys(
                engines.get(engine_key), PayloadEngine, f"engine {engine_key}", problems
            )
            if engine is None:
                continue
            for field in ("name", "short_name", "score_meaning", "floor_text"):
                _check_copy(f"engine {engine_key} {field}", engine.get(field), problems)
            for note in _objects(engine.get("notes")):
                _check_copy(f"engine {engine_key} note", note, problems)

    for record_value in _objects(top.get("records")):
        record_id = (
            record_value.get("id", "unknown")
            if isinstance(record_value, Mapping)
            else "unknown"
        )
        record = _check_keys(record_value, PayloadRecord, f"record {record_id}", problems)
        if record is None:
            continue
        if record.get("label") != LABEL:
            problems.append(f"record {record_id} does not have the required label.")
        _check_link(f"record {record_id}", record.get("source_link"), problems)

    for pair_value in _objects(top.get("pairs")):
        pair_key = (
            pair_value.get("key", "unknown")
            if isinstance(pair_value, Mapping)
            else "unknown"
        )
        pair = _check_keys(pair_value, PayloadPair, f"pair {pair_key}", problems)
        if pair is None:
            continue
        if pair.get("label") != LABEL:
            problems.append(f"pair {pair_key} does not have the required label.")
        _check_copy(f"pair {pair_key} reading", pair.get("reading"), problems)
        if pair.get("reading_kind") not in READING_KINDS:
            kinds = ", ".join(READING_KINDS)
            problems.append(f"pair {pair_key} reading kind is not one of {kinds}.")
        if "confirmed" in pair and not isinstance(pair.get("confirmed"), bool):
            problems.append(f"pair {pair_key} confirmed is not a boolean.")
        for side_name in ("left", "right"):
            side = _check_keys(
                pair.get(side_name), PairSide, f"pair {pair_key} {side_name}", problems
            )
            if side is not None:
                _check_link(
                    f"pair {pair_key} {side_name}", side.get("source_link"), problems
                )

    for section_name, shape in (
        ("hoods", PayloadHood),
        ("bridges", PayloadBridge),
    ):
        for index, item in enumerate(_objects(top.get(section_name))):
            _check_keys(item, shape, f"{section_name}[{index}]", problems)

    data_check = _check_keys(
        top.get("data_check"), PayloadDataCheck, "data_check", problems
    )
    if data_check is not None:
        _check_copy("data_check removed_text", data_check.get("removed_text"), problems)
        for index, item in enumerate(_objects(data_check.get("removed"))):
            if isinstance(item, Mapping):
                _check_copy(
                    f"data_check removed[{index}] reason", item.get("reason"), problems
                )

    _check_keys(top.get("graph"), PayloadGraph, "graph", problems)
    _check_copy("tool_version", top.get("tool_version"), problems)
    if "pattern" in top:
        _check_pattern(top.get("pattern"), problems)
    if "terms" in top or "figures" in top:
        record_ids = {
            str(record.get("id"))
            for record in _objects(top.get("records"))
            if isinstance(record, Mapping)
        }
        pairs = [pair for pair in _objects(top.get("pairs")) if isinstance(pair, Mapping)]
        pair_ids = {str(pair.get("pair_id")) for pair in pairs}
        pair_keys = {str(pair.get("key")) for pair in pairs}
        if "terms" in top:
            _check_terms(top.get("terms"), record_ids, pair_ids, problems)
        if "figures" in top:
            _check_figures(top.get("figures"), pair_keys, problems)
    return problems
