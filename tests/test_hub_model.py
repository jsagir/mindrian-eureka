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


def _loaded_run(tmp_path: Path, *, n_records: int = 30, **options: object):
    return load_run(make_run_folder(tmp_path, n_records=n_records, **options))


def _pair_for(
    engine: str, pair_id: str, left: str, right: str, score: float, rank: int
) -> RunPair:
    return RunPair(
        engine=engine,
        rank=rank,
        pair_id=pair_id,
        left_id=left,
        right_id=right,
        wording=0.4,
        meaning=0.8,
        rank_score=score,
        percentile=None,
        reading="Similar meaning, different wording.",
    )


def _bridge_run(tmp_path: Path, *, with_second_engine: bool = False):
    from dataclasses import replace

    from mindrian_eureka.hub.contracts import ENGINE_WORDING

    run = _loaded_run(tmp_path, n_records=6, zero_pairs=True, clusters=2)
    ids = [record.id for record in run.records]
    unusual = (
        _pair_for(ENGINE_UNUSUAL, "ab", ids[0], ids[1], 1.0, 1),
        _pair_for(ENGINE_UNUSUAL, "ac", ids[0], ids[2], 0.9, 2),
        _pair_for(ENGINE_UNUSUAL, "bc", ids[1], ids[2], 0.8, 3),
        _pair_for(ENGINE_UNUSUAL, "de", ids[3], ids[4], 0.9, 4),
        _pair_for(ENGINE_UNUSUAL, "df", ids[3], ids[5], 0.9, 5),
        _pair_for(ENGINE_UNUSUAL, "ef", ids[4], ids[5], 0.8, 6),
        _pair_for(ENGINE_UNUSUAL, "cd", ids[2], ids[3], 0.01, 7),
    )
    wording = (
        _pair_for(ENGINE_WORDING, "ab", ids[0], ids[1], 1.0, 1),
        _pair_for(ENGINE_WORDING, "ca", ids[2], ids[0], 0.05, 2),
        _pair_for(ENGINE_WORDING, "ce", ids[2], ids[4], 0.001, 3),
    ) if with_second_engine else ()
    engines = dict(run.engines)
    engines[ENGINE_UNUSUAL] = replace(engines[ENGINE_UNUSUAL], pairs=unusual)
    engines[ENGINE_WORDING] = replace(engines[ENGINE_WORDING], pairs=wording)
    return replace(run, engines=engines)


def test_build_payload_bridges_into_two_neighborhoods(tmp_path: Path) -> None:
    from mindrian_eureka.hub.model import build_payload

    payload = build_payload(_bridge_run(tmp_path))
    bridges = payload["bridges"]
    assert bridges[0]["record_id"] == "doc002"
    assert bridges[0]["rank"] == 1
    assert bridges[0]["hoods"] == [1, 2]
    assert bridges[0]["score"] == pytest.approx(0.91)
    assert payload["records"][2]["bridge"] is True
    assert payload["records"][2]["bridge_hoods"] == [1, 2]


def test_bridge_uses_best_engine_per_record_and_ties_by_id(tmp_path: Path) -> None:
    from mindrian_eureka.hub.model import build_payload

    payload = build_payload(_bridge_run(tmp_path, with_second_engine=True))
    chosen = next(item for item in payload["bridges"] if item["record_id"] == "doc002")
    assert chosen["engine"] == ENGINE_UNUSUAL
    assert [item["record_id"] for item in payload["bridges"][:2]] == ["doc002", "doc003"]


def test_build_payload_reads_floors_and_excludes_weak_pairs(tmp_path: Path) -> None:
    from mindrian_eureka.hub.contracts import ENGINE_WORDING
    from mindrian_eureka.hub.model import build_payload

    run = _loaded_run(tmp_path, unusual_floor=0.9, wording_floor=0.0)
    payload = build_payload(run)
    assert payload["engines"][ENGINE_UNUSUAL]["floor_text"] == "0.90"
    assert payload["engines"][ENGINE_WORDING]["floor"] is None
    assert payload["engines"][ENGINE_WORDING]["floor_text"] == ""

    weak_run = _loaded_run(
        tmp_path / "weak", wording_floor=0.5, percentile_below_floor=3
    )
    weak_payload = build_payload(weak_run)
    weak_pairs = [pair for pair in weak_payload["pairs"] if pair["weak"]]
    assert len(weak_pairs) == 3
    assert weak_payload["counts"]["weak_pairs"] == 3
    weak_ids = {pair["key"] for pair in weak_pairs}
    assert all(pair["weight"] == 0.0 and pair["width"] == WIDTH_MIN for pair in weak_pairs)
    visible_pairs = [pair for pair in weak_payload["pairs"] if not pair["weak"]]
    visible_ids = {
        record_id
        for pair in visible_pairs
        for record_id in (pair["left"]["id"], pair["right"]["id"])
    }
    hood_ids = {record_id for hood in weak_payload["hoods"] for record_id in hood["record_ids"]}
    assert hood_ids == visible_ids
    assert not any(pair["key"] in weak_ids for pair in visible_pairs)


def test_build_payload_data_check_and_source_links(tmp_path: Path) -> None:
    from mindrian_eureka.hub.model import build_payload

    dropped = [
        {"id": "lost-a", "reason": "empty text", "source_file": "a.md"},
        {"id": "lost-b", "reason": "empty text", "source_file": "b.md"},
        {"id": "lost-c", "reason": "short text", "source_file": "c.md"},
    ]
    run = _loaded_run(tmp_path, copies=3, empty_text=2, dropped=dropped)
    payload = build_payload(run, file_links={"doc000": "./input/doc000.md"})
    check = payload["data_check"]
    assert check["identical_records"] == 4
    assert check["identical_groups"] == [["doc000", "doc001", "doc002", "doc003"]]
    assert check["no_text_records"] == 2
    assert check["removed_count"] == 3
    assert check["removed_text"] == "empty text (2); short text (1)"
    assert check["boilerplate"] == "not_checked"
    assert payload["records"][0]["identical_to"] == ["doc001", "doc002", "doc003"]
    assert payload["records"][28]["no_text"] is True
    assert payload["records"][0]["source_link"] == "./input/doc000.md"
    assert payload["records"][1]["source_link"] == payload["records"][1]["catalogue_link"]
    assert all(
        pair["flag_identical"]
        for pair in payload["pairs"]
        if "doc000" in (pair["left"]["id"], pair["right"]["id"])
    )


def test_build_payload_graph_threshold_zero_pairs_and_exactly_fifteen(tmp_path: Path) -> None:
    from mindrian_eureka.hub.model import build_payload

    small = build_payload(_loaded_run(tmp_path / "small", n_records=14, pairs_per_engine=91))
    assert small["graph"]["earned"] is False
    assert small["graph"]["visible_records"] < 15

    enough = build_payload(_loaded_run(tmp_path / "enough", n_records=15, pairs_per_engine=105))
    assert enough["graph"]["earned"] is True
    assert enough["graph"]["visible_records"] == 15

    empty = build_payload(_loaded_run(tmp_path / "empty", zero_pairs=True))
    assert empty["counts"]["records_in_visible_pairs"] == 0
    assert empty["graph"]["earned"] is False


def test_build_payload_is_byte_deterministic_and_keeps_hostile_text(tmp_path: Path) -> None:
    from dataclasses import replace

    from mindrian_eureka.hub.model import build_payload
    from mindrian_eureka.run.output import canonical_json

    run = _loaded_run(tmp_path, hostile=True)
    first = canonical_json(build_payload(run))
    second = canonical_json(build_payload(run))
    shuffled_engines = dict(run.engines)
    for key, engine in shuffled_engines.items():
        shuffled_engines[key] = replace(engine, pairs=tuple(reversed(engine.pairs)))
    shuffled = canonical_json(build_payload(replace(run, engines=shuffled_engines)))
    assert first == second == shuffled
    payload = build_payload(run)
    hostile_record = next(record for record in payload["records"] if "</script>" in record["text"])
    assert "<script>" in hostile_record["text"]


def test_build_payload_refuses_a_pair_with_an_unknown_record(tmp_path: Path) -> None:
    from dataclasses import replace

    from mindrian_eureka.hub.model import build_payload

    run = _bridge_run(tmp_path)
    engines = dict(run.engines)
    engine = engines[ENGINE_UNUSUAL]
    engines[ENGINE_UNUSUAL] = replace(
        engine,
        pairs=(replace(engine.pairs[0], left_id="missing-record"), *engine.pairs[1:]),
    )
    with pytest.raises(ValueError, match="missing-record"):
        build_payload(replace(run, engines=engines))
