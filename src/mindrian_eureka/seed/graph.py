"""The pair graph of a finished run (Phase 2.3, D-03).

A run lists pairs in two engines. The same pair can sit in both lists, and the two
engines may name its two records in opposite order. The graph keeps one node for each pair
id. The degree of a record is the number of distinct pairs that hold it. The graph reads
ids and classes only. It reads no record text.

Import rule: the standard library, `..hub.contracts` and `..run.contracts`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ..hub.contracts import ENGINE_KEYS, RunData, RunPair
from ..run.contracts import PAIR_CLASSES, RunError

_FIX_RERUN = "Run eureka run again."


@dataclass(frozen=True)
class PairNode:
    """One distinct pair of the run.

    Attributes:
        pair_id: The stable id of the pair.
        first_id: The smaller of the two record ids.
        second_id: The larger of the two record ids.
        pair_class: The class of the pair, or None when the run has no outcome rule.
        runs: The entries of the pair in the engine lists, in engine order.
    """

    pair_id: str
    first_id: str
    second_id: str
    pair_class: str | None
    runs: tuple[RunPair, ...]


@dataclass(frozen=True)
class PairGraph:
    """The distinct pairs of a run and the records they join.

    Attributes:
        nodes: The pair nodes, keyed by pair id.
        incident: For each record id, the sorted pair ids that hold the record.
    """

    nodes: Mapping[str, PairNode]
    incident: Mapping[str, tuple[str, ...]]

    def degree(self, record_id: str) -> int:
        """Return the number of distinct pairs that hold the record (0 when none)."""
        return len(self.incident.get(record_id, ()))

    def neighbours(self, record_id: str) -> list[tuple[str, str]]:
        """Return the paired records as (neighbour id, pair id), sorted by id then pair id."""
        result: list[tuple[str, str]] = []
        for pair_id in self.incident.get(record_id, ()):
            node = self.nodes[pair_id]
            other = node.second_id if node.first_id == record_id else node.first_id
            result.append((other, pair_id))
        return sorted(result)

    def has_classes(self) -> bool:
        """Return True when at least one pair has a class."""
        return any(node.pair_class is not None for node in self.nodes.values())

    def class_counts(self, record_id: str) -> dict[str, int] | None:
        """Return the number of pairs of the record in each class, or None without classes."""
        if not self.has_classes():
            return None
        counts = dict.fromkeys(sorted(PAIR_CLASSES), 0)
        for pair_id in self.incident.get(record_id, ()):
            pair_class = self.nodes[pair_id].pair_class
            if pair_class is not None:
                counts[pair_class] += 1
        return counts


def build_pair_graph(run: RunData) -> PairGraph:
    """Build the pair graph of a run.

    Args:
        run: The verified run data.

    Returns:
        The graph. One node for each pair id; the engines are merged.

    Raises:
        RunError: One pair id names different records or classes in the two engines.
    """
    grouped: dict[str, list[RunPair]] = {}
    for key in ENGINE_KEYS:
        for entry in run.engines[key].pairs:
            grouped.setdefault(entry.pair_id, []).append(entry)
    nodes: dict[str, PairNode] = {}
    incident: dict[str, list[str]] = {}
    for pair_id in sorted(grouped):
        entries = grouped[pair_id]
        first = entries[0]
        ids = tuple(sorted((first.left_id, first.right_id)))
        for entry in entries[1:]:
            if tuple(sorted((entry.left_id, entry.right_id))) != ids:
                raise RunError(
                    "The two engines of the run name different records for one pair",
                    fix=_FIX_RERUN,
                )
            if entry.pair_class != first.pair_class:
                raise RunError(
                    "The two engines of the run give different classes to one pair",
                    fix=_FIX_RERUN,
                )
        nodes[pair_id] = PairNode(
            pair_id=pair_id,
            first_id=ids[0],
            second_id=ids[1],
            pair_class=first.pair_class,
            runs=tuple(entries),
        )
        for record_id in set(ids):
            incident.setdefault(record_id, []).append(pair_id)
    return PairGraph(
        nodes=nodes,
        incident={record_id: tuple(sorted(items)) for record_id, items in incident.items()},
    )
