"""The candidate list of a run: where a person can start a room (Phase 2.3, D-03).

The list holds counts and classes. Pairs of two records that sit on different sides of the
outcome rule come first, then pairs of two open records, then records that sit in many
pairs. Ties break by record id. The list claims no value and ranks no room by expected
value: the sort key is the sum of two degrees and the ids, and nothing else.

Import rule: the standard library, `..hub.contracts`, `..run.contracts`, `.graph` and
`.contracts`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

from ..hub.contracts import ENGINE_KEYS
from ..run.contracts import (
    LABEL,
    PAIR_CLASS_CROSS,
    PAIR_CLASS_LICENSED_LICENSED,
    PAIR_CLASS_OPEN_OPEN,
    SUMMARY_LINE,
)
from .contracts import RUN_PLACEHOLDER
from .graph import PairGraph, PairNode

CANDIDATES_SCHEMA = "eureka.seed-candidates.v1"
GROUP_CROSS = PAIR_CLASS_CROSS
GROUP_OPEN_OPEN = PAIR_CLASS_OPEN_OPEN
GROUP_UNCLASSED = "unclassed"

_GROUP_TITLES = {
    GROUP_CROSS: "Open next to licensed (cross)",
    GROUP_OPEN_OPEN: "Both open (open_open)",
    GROUP_UNCLASSED: "Pairs (no class)",
}
_MORE = "and {count} more. Use --limit 0 to see all."
_NOT_A_RANKING = "These are counts and classes. They do not rank rooms by value."
_NEXT = (
    f"Pick one, then run: eureka seed {RUN_PLACEHOLDER} --pair <pair id> "
    f"or eureka seed {RUN_PLACEHOLDER} --cluster <record id>"
)
SPINES_KEY = "spines"
_CLASS_ORDER = (PAIR_CLASS_CROSS, PAIR_CLASS_OPEN_OPEN, PAIR_CLASS_LICENSED_LICENSED)
_Row = TypeVar("_Row")


@dataclass(frozen=True)
class PairCandidate:
    """One pair in the list.

    Attributes:
        pair_id: The id of the pair.
        left_id: The smaller record id.
        right_id: The larger record id.
        left_degree: The number of pairs that hold the left record.
        right_degree: The number of pairs that hold the right record.
        engines: The engine keys that list the pair, in engine order.
        pair_class: The class of the pair, or None.
    """

    pair_id: str
    left_id: str
    right_id: str
    left_degree: int
    right_degree: int
    engines: tuple[str, ...]
    pair_class: str | None


@dataclass(frozen=True)
class SpineCandidate:
    """One record that sits in enough pairs to start a cluster.

    Attributes:
        record_id: The record id.
        degree: The number of distinct pairs that hold the record.
        classes: The number of pairs in each class, or None when the run has no classes.
    """

    record_id: str
    degree: int
    classes: Mapping[str, int] | None


@dataclass(frozen=True)
class CandidateList:
    """The candidates of a run.

    Attributes:
        groups: The pair groups in listing order, name to the sorted pairs.
        spines: The spine records, by degree (high first) then record id.
        min_degree: The minimum degree of a spine.
        record_count: The number of records that sit in at least one pair.
        pair_count: The number of distinct pairs.
    """

    groups: Mapping[str, tuple[PairCandidate, ...]]
    spines: tuple[SpineCandidate, ...]
    min_degree: int
    record_count: int
    pair_count: int


def _candidate(graph: PairGraph, node: PairNode) -> PairCandidate:
    present = {entry.engine for entry in node.runs}
    return PairCandidate(
        pair_id=node.pair_id,
        left_id=node.first_id,
        right_id=node.second_id,
        left_degree=graph.degree(node.first_id),
        right_degree=graph.degree(node.second_id),
        engines=tuple(key for key in ENGINE_KEYS if key in present),
        pair_class=node.pair_class,
    )


def _pair_key(item: PairCandidate) -> tuple[int, str, str]:
    return (-(item.left_degree + item.right_degree), item.left_id, item.right_id)


def build_candidates(graph: PairGraph, min_degree: int) -> CandidateList:
    """Build the candidate list.

    Args:
        graph: The pair graph of the run.
        min_degree: The minimum degree of a spine record.

    Returns:
        The list. Pairs of class licensed_licensed are in no group.
    """
    items = [_candidate(graph, node) for node in graph.nodes.values()]
    groups: dict[str, tuple[PairCandidate, ...]]
    if graph.has_classes():
        groups = {
            name: tuple(sorted((i for i in items if i.pair_class == name), key=_pair_key))
            for name in (GROUP_CROSS, GROUP_OPEN_OPEN)
        }
    else:
        groups = {GROUP_UNCLASSED: tuple(sorted(items, key=_pair_key))}
    spines = [
        SpineCandidate(record_id=record_id, degree=graph.degree(record_id),
                       classes=graph.class_counts(record_id))
        for record_id in graph.incident
        if graph.degree(record_id) >= min_degree
    ]
    spines.sort(key=lambda spine: (-spine.degree, spine.record_id))
    return CandidateList(
        groups=groups,
        spines=tuple(spines),
        min_degree=min_degree,
        record_count=len(graph.incident),
        pair_count=len(graph.nodes),
    )


def _cut(rows: Sequence[_Row], limit: int) -> tuple[Sequence[_Row], int]:
    if limit == 0 or len(rows) <= limit:
        return rows, 0
    return rows[:limit], len(rows) - limit


def _pair_line(item: PairCandidate) -> str:
    return (
        f"  {item.pair_id}  {item.left_id}  {item.right_id}  "
        f"degree {item.left_degree} and {item.right_degree}  "
        f"listed by {len(item.engines)} engine(s)"
    )


def _spine_line(item: SpineCandidate) -> str:
    line = f"  {item.record_id}  degree {item.degree}"
    if item.classes is not None:
        parts = ", ".join(f"{name} {item.classes[name]}" for name in _CLASS_ORDER)
        line += f"  {parts}"
    return line



def render_text(candidates: CandidateList, limit: int) -> str:
    """Return the terminal text of the list. The last line is the shared status line.

    Args:
        candidates: The list.
        limit: The most rows to show in each group and in the spine part; 0 shows all.
    """
    blocks: list[list[str]] = [[f"Seed candidates for this run ({LABEL})"]]
    for name, rows in candidates.groups.items():
        shown, hidden = _cut(rows, limit)
        block = [f"{_GROUP_TITLES[name]}: {len(rows)} pairs"]
        block += [_pair_line(item) for item in shown]
        if hidden:
            block.append("  " + _MORE.format(count=hidden))
        blocks.append(block)
    shown_spines, hidden_spines = _cut(candidates.spines, limit)
    spine_block = [f"Records with {candidates.min_degree} or more pairs: {len(candidates.spines)}"]
    spine_block += [_spine_line(item) for item in shown_spines]
    if hidden_spines:
        spine_block.append("  " + _MORE.format(count=hidden_spines))
    blocks.append(spine_block)
    blocks.append([_NOT_A_RANKING, _NEXT, SUMMARY_LINE])
    lines: list[str] = []
    for index, block in enumerate(blocks):
        if index:
            lines.append("")
        lines.extend(block)
    return "\n".join(lines)


def to_json_dict(candidates: CandidateList, limit: int) -> dict[str, Any]:
    """Return the list as a JSON-ready dictionary. It holds no machine path.

    Args:
        candidates: The list.
        limit: The most rows to show in each group and in the spine part; 0 shows all.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    hidden: dict[str, int] = {}
    for name, rows in candidates.groups.items():
        shown, cut = _cut(rows, limit)
        groups[name] = [
            {
                "pair_id": item.pair_id,
                "left_id": item.left_id,
                "right_id": item.right_id,
                "left_degree": item.left_degree,
                "right_degree": item.right_degree,
                "engines": list(item.engines),
                **({"pair_class": item.pair_class} if item.pair_class is not None else {}),
            }
            for item in shown
        ]
        hidden[name] = cut
    shown_spines, cut_spines = _cut(candidates.spines, limit)
    hidden[SPINES_KEY] = cut_spines
    spines: list[dict[str, Any]] = []
    for spine in shown_spines:
        entry: dict[str, Any] = {"record_id": spine.record_id, "degree": spine.degree}
        if spine.classes is not None:
            entry["classes"] = dict(spine.classes)
        spines.append(entry)
    return {
        "schema": CANDIDATES_SCHEMA,
        "label": LABEL,
        "counts": {
            "records": candidates.record_count,
            "pairs": candidates.pair_count,
            "min_degree": candidates.min_degree,
        },
        "groups": groups,
        "spines": spines,
        "hidden": hidden,
        "summary_line": SUMMARY_LINE,
    }
