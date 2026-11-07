"""The `known` and `feed_next` lists of a seed (Phase 2.3, D-02).

A mapped column that is filled goes to `known`. A mapped column that is blank goes to
`feed_next` with a one-line reason. Each `not_in_export` item goes to `feed_next` too.
There is no inference and no model. The lists come from the cell states of the run.

Import rule: the standard library, `..run.contracts` and `.source`, `.contracts`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ..run.contracts import (
    CELL_BLANK,
    CELL_CARRIED,
    CELL_EXPORT_ONLY,
    CELL_TEXT,
    Record,
    RunError,
)
from .contracts import (
    HELD_CARRIED,
    HELD_EXPORT_ONLY,
    HELD_RECORD_TEXT,
    REASON_BLANK,
    REASON_NOT_IN_EXPORT,
)
from .source import RoomMap

Lists = dict[str, list[dict[str, str]]]

_FIX_RERUN = "Run eureka run again with the current mapping."
_HELD = {
    CELL_TEXT: HELD_RECORD_TEXT,
    CELL_CARRIED: HELD_CARRIED,
    CELL_EXPORT_ONLY: HELD_EXPORT_ONLY,
}


def section_lists(record: Record, room_map: RoomMap) -> tuple[Lists, Lists]:
    """Return `known` and `feed_next` for one record.

    Args:
        record: The record, with its cell states.
        room_map: The section map that applies to the record.

    Returns:
        The two dictionaries, section name to a list of entries. A section without entries
        is left out.

    Raises:
        RunError: A mapped column has no cell state in the record, or a carried column has
            no carried value.
    """
    known: Lists = {}
    feed_next: Lists = {}
    for section, columns in room_map.sections:
        for column in columns:
            state = record.room_cells.get(column)
            if state is None:
                raise RunError(
                    f"The record {record.id} has no cell state for the mapped column {column}",
                    fix=_FIX_RERUN,
                )
            if state == CELL_BLANK:
                feed_next.setdefault(section, []).append(
                    {"record_id": record.id, "column": column, "reason": REASON_BLANK}
                )
                continue
            entry = {"record_id": record.id, "column": column, "held_in": _HELD[state]}
            if state == CELL_CARRIED:
                value = record.extras.get(column, "")
                if not value:
                    raise RunError(
                        f"The record {record.id} has no carried value for the column {column}",
                        fix=_FIX_RERUN,
                    )
                entry["value"] = value
            known.setdefault(section, []).append(entry)
        for missing in room_map.not_in_export:
            if missing.section != section:
                continue
            feed_next.setdefault(section, []).append(
                {
                    "record_id": record.id,
                    "item": missing.item,
                    "source": missing.source,
                    "reason": REASON_NOT_IN_EXPORT.format(source=missing.source),
                }
            )
    return known, feed_next


def merge_lists(
    per_record: Sequence[tuple[Lists, Lists]], order: Sequence[str]
) -> tuple[Lists, Lists]:
    """Combine the lists of several records. Sections follow `order`; records keep their order."""
    known: Lists = {}
    feed_next: Lists = {}
    for section in order:
        for record_known, record_feed in per_record:
            if section in record_known:
                known.setdefault(section, []).extend(record_known[section])
            if section in record_feed:
                feed_next.setdefault(section, []).extend(record_feed[section])
    return known, feed_next


def order_sections(
    known: dict[str, Any], feed_next: dict[str, Any], room_map: RoomMap
) -> list[str]:
    """Return the suggested section order.

    Sections with at least one `known` entry come first, then the other sections of the
    map. Each group keeps the order of the map. A section that only `feed_next` names, and
    that the map does not list, comes last.
    """
    names = list(room_map.section_names)
    for section in (*known, *feed_next):
        if section not in names:
            names.append(section)
    filled = [name for name in names if known.get(name)]
    return [*filled, *(name for name in names if name not in filled)]
