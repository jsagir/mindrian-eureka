"""Tests for the cluster seed builder (Phase 2.3, plan 03)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest
from hub_support import tree_hash
from mindrian_eureka.run.contracts import LABEL, UsageError
from mindrian_eureka.run.output import canonical_json
from seed_support import make_seed_run, pair_id_of, record_id

UNUSUAL = [(0, 1), (0, 3), (0, 5), (2, 3), (2, 5), (4, 5), (6, 7)]
WORDING = [(0, 1), (0, 2), (2, 7), (8, 9), (10, 11), (1, 3)]
SPINE = 0
NEIGHBOURS = [1, 2, 3, 5]


@pytest.fixture
def run(tmp_path: Path) -> Path:
    return make_seed_run(tmp_path, n_records=12, unusual=UNUSUAL, wording=WORDING)


def build(run: Path, index: int, min_degree: int = 3) -> Any:
    from mindrian_eureka.seed.builder import build_cluster_seed
    from mindrian_eureka.seed.graph import build_pair_graph
    from mindrian_eureka.seed.source import load_source

    source = load_source(run)
    graph = build_pair_graph(source.run)
    return build_cluster_seed(source, graph, record_id(index), min_degree=min_degree)


def title_of(index: int) -> str:
    # The synthetic records with index 3 mod 4 have an empty title, so the id shows.
    return record_id(index) if index % 4 == 3 else f"Synthetic title {index + 1}"


def test_cluster_of_record_0(run: Path) -> None:
    from mindrian_eureka.seed.builder import build_pair_seed
    from mindrian_eureka.seed.sections import merge_lists, section_lists
    from mindrian_eureka.seed.source import load_source, room_map_for

    seed = build(run, SPINE)
    doc = seed.document
    pair_ids = sorted(pair_id_of(SPINE, n) for n in NEIGHBOURS)
    assert seed.kind == "cluster"
    assert doc["seed_kind"] == "cluster"
    assert doc["label"] == LABEL
    assert doc["selection"] == {
        "spine_record_id": record_id(0),
        "degree": 4,
        "min_degree": 3,
        "pair_ids": pair_ids,
    }
    roles = [(item["record_id"], item["role"]) for item in doc["records"]]
    assert roles == [
        (record_id(0), "spine"),
        (record_id(1), "neighbour"),
        (record_id(2), "neighbour"),
        (record_id(3), "neighbour"),
        (record_id(5), "neighbour"),
    ]
    assert [pair["pair_id"] for pair in doc["pairs"]] == pair_ids
    entries = doc["bank_entries"]
    assert [entry["pair_id"] for entry in entries] == pair_ids
    for entry in entries:
        neighbour = entry["neighbour_id"]
        assert neighbour != record_id(0)
        assert entry["review_status"] == "proposed"
        assert entry["statement"]["critic"] == "pending"
        assert entry["statement"]["banked"] is False
        assert entry["statement"]["label"] == LABEL
        fields = entry["statement"]["fields"]
        assert fields["tech_a"] == title_of(0)
        assert fields["tech_b"] == title_of(int(neighbour[-5:]) - 1)
        assert {entry["left_id"], entry["right_id"]} == {record_id(0), neighbour}
    assert len(doc["pairs"]) == 4
    assert len(seed.evidence) == 5
    # The spine alone fills known and feed_next.
    lists = [*doc["known"].values(), *doc["feed_next"].values()]
    assert lists
    assert {item["record_id"] for entries_ in lists for item in entries_} == {record_id(0)}
    source = load_source(run)
    spine = source.records_by_id[record_id(0)]
    room_map = room_map_for(source, spine)
    expected_known, expected_feed = merge_lists(
        [section_lists(spine, room_map)], room_map.section_names
    )
    assert doc["known"] == expected_known
    assert doc["feed_next"] == expected_feed
    # A pair seed of the same spine record sees the same spine entries.
    pair_doc = build_pair_seed(source, pair_id_of(0, 2)).document
    spine_in_pair = [
        item
        for entries_ in pair_doc["known"].values()
        for item in entries_
        if item["record_id"] == record_id(0)
    ]
    spine_in_cluster = [
        item
        for entries_ in doc["known"].values()
        for item in entries_
        if item["record_id"] == record_id(0)
    ]
    assert spine_in_pair == spine_in_cluster
    assert [item["record_id"] for item in doc["source_refs"]] == [
        item["record_id"] for item in doc["records"]
    ]
    assert len(doc["source_refs"]) == 5
    assert seed.default_out_name == (
        "eureka-seed-cluster-" + hashlib.sha256(record_id(0).encode()).hexdigest()[:12]
    )


def test_cluster_validates_and_is_deterministic(tmp_path: Path, run: Path) -> None:
    from mindrian_eureka.seed.builder import validate_seed

    first = build(run, SPINE)
    validate_seed(first.document)
    second = build(run, SPINE)
    assert canonical_json(first.document) == canonical_json(second.document)
    assert [item.data for item in first.evidence] == [item.data for item in second.evidence]
    # A second run folder with the engine lists in the other order gives the same bytes
    # once the manifest-bound fields are set aside (the pair files differ, so their hashes do).
    reordered = make_seed_run(
        tmp_path,
        name="reordered",
        n_records=12,
        unusual=list(reversed(UNUSUAL)),
        wording=list(reversed(WORDING)),
    )
    other = build(reordered, SPINE)
    bound = ("manifest_sha256", "scope_id", "pairs", "bank_entries")

    def stable(doc: dict[str, Any]) -> bytes:
        return canonical_json({k: v for k, v in doc.items() if k not in bound})

    assert stable(first.document) == stable(other.document)
    assert [item["pair_id"] for item in other.document["pairs"]] == [
        item["pair_id"] for item in first.document["pairs"]
    ]
    assert [item.data for item in first.evidence] == [item.data for item in other.evidence]


def test_min_degree(run: Path) -> None:
    with pytest.raises(UsageError) as caught:
        build(run, 4)
    message = caught.value.message
    assert "1 pair(s)" in message and "at least 3" in message
    fix = caught.value.fix or ""
    assert "--min-degree" in fix and "--pair" in fix
    seed = build(run, 4, min_degree=1)
    assert seed.document["selection"]["degree"] == 1
    assert seed.document["selection"]["min_degree"] == 1
    assert len(seed.document["bank_entries"]) == 1
    assert [item["role"] for item in seed.document["records"]] == ["spine", "neighbour"]
    with pytest.raises(UsageError) as unknown:
        build(run, 40)
    assert "no record with that id" in unknown.value.message
    assert "records.jsonl" in (unknown.value.fix or "")


def test_cluster_writes_through_write_seed(tmp_path: Path, run: Path) -> None:
    from mindrian_eureka.seed.builder import build_pair_seed, is_seed_folder, write_seed
    from mindrian_eureka.seed.source import load_source

    before = tree_hash(run)
    out = tmp_path / "cluster-out"
    summary = write_seed(build(run, SPINE), run, out)
    files = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert "seed.json" in files
    assert len([name for name in files if name.startswith("evidence/")]) == 5
    assert len(files) == 6
    assert summary.kind == "cluster" and summary.records == 5 and summary.bank_entries == 4
    assert is_seed_folder(out)
    pair = build_pair_seed(load_source(run), pair_id_of(0, 2))
    write_seed(pair, run, out)
    after = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert len(after) == 3
    assert is_seed_folder(out)
    # The run folder is never written.
    assert tree_hash(run) == before
    assert not any(p.name.startswith("seed") for p in run.iterdir())
