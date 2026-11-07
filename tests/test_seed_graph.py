"""Tests for the pair graph of a run (Phase 2.3, plan 03)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from mindrian_eureka.run.contracts import RunError
from mindrian_eureka.run.output import OUTPUT_WORDING
from seed_support import make_seed_run, pair_id_of, record_id
from test_hub_reader import edit_json

UNUSUAL = [(0, 1), (0, 3), (0, 5), (2, 3), (2, 5), (4, 5), (6, 7)]
WORDING = [(0, 1), (0, 2), (2, 7), (8, 9), (10, 11), (1, 3)]
DEGREES = {0: 4, 1: 2, 2: 4, 3: 3, 4: 1, 5: 3, 6: 1, 7: 2, 8: 1, 9: 1, 10: 1, 11: 1}


def graph_of(run: Path) -> Any:
    from mindrian_eureka.seed.graph import build_pair_graph
    from mindrian_eureka.seed.source import load_source

    return build_pair_graph(load_source(run).run)


@pytest.fixture
def run(tmp_path: Path) -> Path:
    return make_seed_run(tmp_path, n_records=12, unusual=UNUSUAL, wording=WORDING)


def test_pairs_are_deduplicated_across_engines(tmp_path: Path, run: Path) -> None:
    graph = graph_of(run)
    assert len(graph.nodes) == 12
    node = graph.nodes[pair_id_of(0, 1)]
    assert [entry.engine for entry in node.runs] == ["unusual_pairs", "wording_and_meaning"]
    assert (node.first_id, node.second_id) == (record_id(0), record_id(1))
    # A wording pair that lists the two records in the other order joins the same node.
    other = make_seed_run(
        tmp_path, name="flip", n_records=4, unusual=[(0, 1)], wording=[(1, 0)]
    )
    flipped = graph_of(other)
    assert len(flipped.nodes) == 1
    only = flipped.nodes[pair_id_of(0, 1)]
    assert len(only.runs) == 2
    assert (only.first_id, only.second_id) == (record_id(0), record_id(1))


def test_degrees_neighbours_and_class_counts(run: Path) -> None:
    graph = graph_of(run)
    for index, degree in DEGREES.items():
        assert graph.degree(record_id(index)) == degree
    assert graph.degree("recs/C99999") == 0
    assert graph.neighbours(record_id(0)) == [
        (record_id(1), pair_id_of(0, 1)),
        (record_id(2), pair_id_of(0, 2)),
        (record_id(3), pair_id_of(0, 3)),
        (record_id(5), pair_id_of(0, 5)),
    ]
    counts = graph.class_counts(record_id(0))
    assert counts == {"cross": 3, "licensed_licensed": 1, "open_open": 0}
    assert list(counts) == ["cross", "licensed_licensed", "open_open"]
    assert graph.class_counts(record_id(3)) == {
        "cross": 2,
        "licensed_licensed": 0,
        "open_open": 1,
    }


def test_run_without_classes_has_no_class_counts(tmp_path: Path) -> None:
    run = make_seed_run(
        tmp_path, n_records=12, unusual=UNUSUAL, wording=WORDING, with_classes=False
    )
    graph = graph_of(run)
    assert all(node.pair_class is None for node in graph.nodes.values())
    assert graph.class_counts(record_id(0)) is None
    assert graph.degree(record_id(0)) == 4


def test_conflicting_classes_are_a_damaged_run(run: Path) -> None:
    target = pair_id_of(0, 1)

    def change(doc: dict[str, Any]) -> None:
        for pair in doc["pairs"]:
            if pair["pair_id"] == target:
                assert pair["pair_class"] == "cross"
                pair["pair_class"] = "open_open"

    edit_json(run, OUTPUT_WORDING, change)
    with pytest.raises(RunError) as caught:
        graph_of(run)
    assert "eureka run again" in (caught.value.fix or "")
