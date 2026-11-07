"""Read a finished run folder for the seed builder (Phase 2.3).

The reader is `hub.reader.load_run`, which checks the sha256 of every file against the
manifest before it trusts a byte. This module adds the checks a seed needs: the run is a
Eureka run, it holds a room section map, and a pair id is in the run. Nothing is stored
about the machine: the source holds no path.

Import rule: the standard library, `..run.*` and `..hub.*`. No numpy.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..hub.contracts import ENGINE_KEYS, RunData, RunPair
from ..hub.reader import load_run
from ..run.contracts import Record, RunError, UsageError
from ..run.output import is_eureka_run_folder

_FIX_RERUN = "Run eureka run again with the current mapping."


@dataclass(frozen=True)
class NotInExport:
    """One fact that the export does not hold.

    Attributes:
        item: The plain name of the fact.
        section: The room section the fact belongs to.
        source: The outside source that holds the fact.
    """

    item: str
    section: str
    source: str


@dataclass(frozen=True)
class RoomMap:
    """The section map of one mapping entry, in file order.

    Attributes:
        sections: Each section name with its columns.
        not_in_export: The facts the export lacks.
    """

    sections: tuple[tuple[str, tuple[str, ...]], ...]
    not_in_export: tuple[NotInExport, ...] = ()

    @property
    def section_names(self) -> tuple[str, ...]:
        """Return the section names in map order."""
        return tuple(name for name, _ in self.sections)


@dataclass(frozen=True)
class SeedSource:
    """A verified run, ready for the seed builder.

    Attributes:
        run: The data that `load_run` returned.
        records_by_id: The records, keyed by record id.
    """

    run: RunData
    records_by_id: Mapping[str, Record]


def load_source(run_dir: Path) -> SeedSource:
    """Read and verify a finished run folder.

    Args:
        run_dir: The output folder of `eureka run`.

    Returns:
        The verified run data.

    Raises:
        UsageError: The folder is not a Eureka run, or the run has no room section map.
        RunError: A file is damaged (the hash check failed).
    """
    if not is_eureka_run_folder(run_dir):
        raise UsageError(
            "this folder is not a finished Eureka run",
            fix="Run eureka run first, then give its output folder to eureka seed.",
        )
    run = load_run(run_dir)
    if not run.room_sections:
        raise UsageError(
            "this run has no room section map",
            fix="Add room_sections to the mapping file and run eureka run again.",
        )
    return SeedSource(run=run, records_by_id={record.id: record for record in run.records})


def find_pair(source: SeedSource, pair_id: str) -> tuple[RunPair, ...]:
    """Return every entry of a pair id, in engine order.

    Raises:
        UsageError: The run has no pair with that id.
    """
    found = tuple(
        pair
        for key in ENGINE_KEYS
        for pair in source.run.engines[key].pairs
        if pair.pair_id == pair_id
    )
    if not found:
        raise UsageError(
            "This run has no pair with that id",
            fix="Check the pair id. The hub shows it under each pair.",
        )
    return found


def _damaged(what: str) -> RunError:
    return RunError(f"The room section map of the run is damaged: {what}", fix=_FIX_RERUN)


def _texts(value: Any, what: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise _damaged(what)
    if not all(isinstance(item, str) and item for item in value):
        raise _damaged(what)
    return tuple(value)


def _parse_map(block: Any) -> RoomMap:
    if not isinstance(block, dict):
        raise _damaged("a block is not an object")
    raw_sections = block.get("sections")
    if not isinstance(raw_sections, list) or not raw_sections:
        raise _damaged("a block has no sections")
    sections: list[tuple[str, tuple[str, ...]]] = []
    for item in raw_sections:
        if not isinstance(item, dict) or not isinstance(item.get("section"), str):
            raise _damaged("a section has no name")
        sections.append((item["section"], _texts(item.get("columns"), "a section has no columns")))
    names = [name for name, _ in sections]
    if len(set(names)) != len(names):
        raise _damaged("a section is listed twice")
    raw_items = block.get("not_in_export", [])
    if not isinstance(raw_items, list):
        raise _damaged("not_in_export is not a list")
    items: list[NotInExport] = []
    for item in raw_items:
        if not isinstance(item, dict) or not all(
            isinstance(item.get(key), str) and item[key] for key in ("item", "section", "source")
        ):
            raise _damaged("a not_in_export item is incomplete")
        if item["section"] not in names:
            raise _damaged("a not_in_export item names an unknown section")
        items.append(NotInExport(item=item["item"], section=item["section"], source=item["source"]))
    return RoomMap(sections=tuple(sections), not_in_export=tuple(items))


def room_map_for(source: SeedSource, record: Record) -> RoomMap:
    """Return the section map that applies to a record.

    The manifest block with the exact source file name wins; else the `*` block.

    Raises:
        RunError: No block applies, or the block is malformed.
    """
    blocks = source.run.room_sections
    block = blocks.get(record.source_file, blocks.get("*"))
    if block is None:
        raise _damaged("a record belongs to a file without a section map")
    return _parse_map(block)


def combine_maps(maps: Sequence[RoomMap]) -> RoomMap:
    """Return one map that holds the section names of all `maps` in first-seen order.

    The columns are dropped: the result serves only for ordering sections.
    """
    names: list[str] = []
    for room_map in maps:
        for name in room_map.section_names:
            if name not in names:
                names.append(name)
    return RoomMap(sections=tuple((name, ()) for name in names))
