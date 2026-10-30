"""Validate the hub payload's labels, source links and authored copy.

Import rule: the standard library and `.contracts` only. No numpy.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import NotRequired, get_origin, get_type_hints

from ..run.contracts import LABEL
from .contracts import (
    ENGINE_KEYS,
    PairSide,
    Payload,
    PayloadBridge,
    PayloadCounts,
    PayloadDataCheck,
    PayloadEngine,
    PayloadGraph,
    PayloadHood,
    PayloadPair,
    PayloadRecord,
    has_dash,
    has_internal_name,
)

_BAD_LINK_PREFIXES = ("http:", "https:", "javascript:", "//")


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
    return problems
