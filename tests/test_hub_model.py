"""Deterministic model tests for the opportunity hub."""

from __future__ import annotations

import random
from pathlib import Path

import pytest
from hub_support import make_run_folder
from mindrian_eureka.hub.contracts import (
    ENGINE_UNUSUAL,
    NEIGHBORHOOD_TINTS,
    WIDTH_CROSSING,
    WIDTH_MAX,
    WIDTH_MIN,
    RunPair,
)
from mindrian_eureka.hub.model import engine_weights, label_propagation, number_hoods, pair_widths
from mindrian_eureka.hub.reader import load_run


def _pair(
    pair_id: str,
    left_id: str,
    right_id: str,
    score: float,
    *,
    engine: str = ENGINE_UNUSUAL,
) -> RunPair:
    return RunPair(
        engine=engine,
        rank=1,
        pair_id=pair_id,
        left_id=left_id,
        right_id=right_id,
        wording=0.2,
        meaning=0.4,
        rank_score=score,
        percentile=None,
        reading="Wording and meaning agree on this pair.",
    )


def _edges(pairs: tuple[RunPair, ...]) -> tuple[dict[tuple[str, str], float], list[str]]:
    weights = engine_weights(pairs)
    edges: dict[tuple[str, str], float] = {}
    nodes: set[str] = set()
    for pair in pairs:
        first, second = sorted((pair.left_id, pair.right_id))
        nodes.update((first, second))
        key = f"{pair.engine}:{pair.pair_id}"
        edges[(first, second)] = edges.get((first, second), 0.0) + weights[key]
    return edges, sorted(nodes)


def test_weights_are_normalized_inside_each_engine() -> None:
    pairs = (
        _pair("u1", "a", "b", 2.0),
        _pair("u2", "b", "c", 1.0),
        _pair("w1", "c", "d", 10.0, engine="wording_and_meaning"),
        _pair("w2", "d", "e", 5.0, engine="wording_and_meaning"),
    )
    assert engine_weights(pairs) == {
        "unusual_pairs:u1": 1.0,
        "unusual_pairs:u2": 0.5,
        "wording_and_meaning:w1": 1.0,
        "wording_and_meaning:w2": 0.5,
    }


def test_two_triangles_joined_by_a_weak_edge_make_two_numbered_hoods() -> None:
    pairs = (
        _pair("ab", "a", "b", 1.0),
        _pair("ac", "a", "c", 1.0),
        _pair("bc", "b", "c", 1.0),
        _pair("de", "d", "e", 0.9),
        _pair("df", "d", "f", 0.9),
        _pair("ef", "e", "f", 0.9),
        _pair("cd", "c", "d", 0.01),
    )
    edges, nodes = _edges(pairs)
    labels = label_propagation(edges, nodes)
    hoods = number_hoods(labels)
    assert [(hood["number"], hood["record_ids"]) for hood in hoods] == [
        (1, ["a", "b", "c"]),
        (2, ["d", "e", "f"]),
    ]


def test_equal_weight_path_has_a_fixed_labeling() -> None:
    edges = {("a", "b"): 1.0, ("b", "c"): 1.0, ("c", "d"): 1.0}
    assert label_propagation(edges, ["a", "b", "c", "d"]) == {
        "a": "b",
        "b": "b",
        "c": "b",
        "d": "b",
    }


def test_shuffling_pairs_does_not_change_hoods_or_widths() -> None:
    pairs = (
        _pair("ab", "a", "b", 1.0),
        _pair("ac", "a", "c", 0.7),
        _pair("bc", "b", "c", 0.5),
        _pair("de", "d", "e", 0.9),
        _pair("df", "d", "f", 0.8),
        _pair("ef", "e", "f", 0.6),
        _pair("cd", "c", "d", 0.01),
    )
    expected_edges, expected_nodes = _edges(pairs)
    expected_labels = label_propagation(expected_edges, expected_nodes)
    expected_widths = pair_widths(pairs, expected_labels)
    for seed in range(20):
        shuffled = list(pairs)
        random.Random(seed).shuffle(shuffled)
        shuffled_pairs = tuple(shuffled)
        edges, nodes = _edges(shuffled_pairs)
        labels = label_propagation(edges, nodes)
        assert number_hoods(labels) == number_hoods(expected_labels)
        assert pair_widths(shuffled_pairs, labels) == expected_widths


def test_isolated_node_and_empty_edges_make_no_hoods() -> None:
    assert label_propagation({}, ["isolated"]) == {}
    assert number_hoods({}) == []


def test_zero_maximum_score_has_zero_weight() -> None:
    pair = _pair("zero", "a", "b", 0.0)
    assert engine_weights((pair,)) == {"unusual_pairs:zero": 0.0}


def test_pair_widths_cover_crossing_normal_and_single_score() -> None:
    first = _pair("first", "a", "b", 0.2)
    middle = _pair("middle", "b", "c", 0.5)
    last = _pair("last", "c", "d", 0.8)
    pairs = (first, middle, last)
    widths = pair_widths(pairs, {"a": "a", "b": "a", "c": "c", "d": "c"})
    assert widths["unusual_pairs:first"] == WIDTH_MIN
    assert widths["unusual_pairs:middle"] == WIDTH_CROSSING
    assert widths["unusual_pairs:last"] == WIDTH_MAX

    normal = pair_widths(pairs, {"a": "a", "b": "a", "c": "a", "d": "a"})
    assert normal["unusual_pairs:first"] == WIDTH_MIN
    assert normal["unusual_pairs:middle"] == pytest.approx(0.325)
    assert normal["unusual_pairs:last"] == WIDTH_MAX
    assert pair_widths((middle,), {"b": "b", "c": "b"})[
        "unusual_pairs:middle"
    ] == WIDTH_MAX


def test_neighborhood_tint_cycles_at_number_22() -> None:
    labels = {f"id-{index:02d}": f"id-{index:02d}" for index in range(22)}
    hoods = number_hoods(labels)
    assert hoods[0]["tint"] == NEIGHBORHOOD_TINTS[0]
    assert hoods[21]["number"] == 22
    assert hoods[21]["tint"] == NEIGHBORHOOD_TINTS[0]


def test_weights_work_with_a_loaded_run_folder(tmp_path: Path) -> None:
    folder = make_run_folder(tmp_path, n_records=12, pairs_per_engine=8)
    run = load_run(folder)
    pairs = run.engines[ENGINE_UNUSUAL].pairs
    weights = engine_weights(pairs)
    assert len(weights) == len(pairs)
    assert all(0.0 <= weight <= 1.0 for weight in weights.values())
