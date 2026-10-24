"""Build deterministic graph model values from hub run data.

Import rule: the standard library, `.contracts`, and `..run.output` for the
4-decimal score text helper only. Do not import numpy.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..run.output import _score
from .contracts import (
    NEIGHBORHOOD_TINTS,
    WIDTH_CROSSING,
    WIDTH_MAX,
    WIDTH_MIN,
    PayloadHood,
    RunPair,
)


def pair_key(pair: RunPair) -> str:
    """Return the stable payload key of a pair."""
    return f"{pair.engine}:{pair.pair_id}"


def score_text(value: float) -> str:
    """Format a score with the same four decimals used in ranked-pairs.md."""
    return _score({"score": value}, "score")


def engine_weights(pairs: Sequence[RunPair]) -> dict[str, float]:
    """Normalize nonnegative rank scores within each engine.

    Args:
        pairs: Visible pairs to normalize.

    Returns:
        A mapping from engine-and-pair key to a weight between zero and one.
    """
    maxima: dict[str, float] = {}
    for pair in pairs:
        score = max(pair.rank_score, 0.0)
        maxima[pair.engine] = max(maxima.get(pair.engine, 0.0), score)

    weights: dict[str, float] = {}
    for pair in sorted(pairs, key=pair_key):
        maximum = maxima[pair.engine]
        score = max(pair.rank_score, 0.0)
        weights[pair_key(pair)] = score / maximum if maximum > 0.0 else 0.0
    return weights


def label_propagation(
    edges: Mapping[tuple[str, str], float], nodes: Sequence[str]
) -> dict[str, str]:
    """Group connected visible records with sorted, weighted label propagation.

    Args:
        edges: Pairwise weights keyed by a pair of record IDs.
        nodes: Candidate record IDs. IDs with no incident edge are omitted.

    Returns:
        A mapping from each connected record ID to its stable final label.
    """
    adjacency: dict[str, dict[str, float]] = {}
    for (first, second), weight in sorted(edges.items()):
        first_neighbors = adjacency.setdefault(first, {})
        first_neighbors[second] = first_neighbors.get(second, 0.0) + weight
        second_neighbors = adjacency.setdefault(second, {})
        second_neighbors[first] = second_neighbors.get(first, 0.0) + weight

    ordered_nodes = [node for node in sorted(set(nodes)) if adjacency.get(node)]
    labels = {node: node for node in ordered_nodes}
    for _ in range(100):
        changed = False
        for node in ordered_nodes:
            totals: dict[str, float] = {}
            for neighbor in sorted(adjacency[node]):
                label = labels[neighbor]
                totals[label] = totals.get(label, 0.0) + adjacency[node][neighbor]
            if not totals:
                continue
            largest = max(totals.values())
            current = labels[node]
            if totals.get(current) == largest:
                next_label = current
            else:
                next_label = min(label for label, total in totals.items() if total == largest)
            if next_label != current:
                labels[node] = next_label
                changed = True
        if not changed:
            break
    return labels


def number_hoods(labels: Mapping[str, str]) -> list[PayloadHood]:
    """Number label groups by size and lowest record ID, then assign book tints.

    Args:
        labels: The final record-to-label mapping.

    Returns:
        Neighborhoods ordered by descending size, then by their lowest record ID.
    """
    groups: dict[str, list[str]] = {}
    for record_id in sorted(labels):
        groups.setdefault(labels[record_id], []).append(record_id)
    ordered = sorted(groups.values(), key=lambda record_ids: (-len(record_ids), record_ids[0]))
    return [
        {
            "number": number,
            "size": len(record_ids),
            "tint": NEIGHBORHOOD_TINTS[(number - 1) % len(NEIGHBORHOOD_TINTS)],
            "record_ids": record_ids,
        }
        for number, record_ids in enumerate(ordered, start=1)
    ]


def pair_widths(pairs: Sequence[RunPair], labels: Mapping[str, str]) -> dict[str, float]:
    """Scale visible pair widths and mark cross-neighborhood pairs.

    Args:
        pairs: Pairs that pass their engine's visibility floor.
        labels: The final neighborhood label for each visible record.

    Returns:
        A mapping from engine-and-pair key to its drawing width.
    """
    ranges: dict[str, tuple[float, float]] = {}
    for engine in sorted({pair.engine for pair in pairs}):
        scores = [pair.rank_score for pair in pairs if pair.engine == engine]
        ranges[engine] = (min(scores), max(scores))

    widths: dict[str, float] = {}
    for pair in sorted(pairs, key=pair_key):
        if labels.get(pair.left_id) != labels.get(pair.right_id):
            widths[pair_key(pair)] = WIDTH_CROSSING
            continue
        low, high = ranges[pair.engine]
        if high == low:
            widths[pair_key(pair)] = WIDTH_MAX
        else:
            ratio = (pair.rank_score - low) / (high - low)
            widths[pair_key(pair)] = WIDTH_MIN + (WIDTH_MAX - WIDTH_MIN) * ratio
    return widths
