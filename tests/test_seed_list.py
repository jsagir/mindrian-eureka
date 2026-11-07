"""Tests for the candidate list and the cluster and list flags (Phase 2.3, plan 03)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from hub_support import tree_hash
from mindrian_eureka.cli import main
from mindrian_eureka.run.contracts import LABEL, SUMMARY_LINE
from seed_support import make_seed_run, pair_id_of, record_id

UNUSUAL = [(0, 1), (0, 3), (0, 5), (2, 3), (2, 5), (4, 5), (6, 7)]
WORDING = [(0, 1), (0, 2), (2, 7), (8, 9), (10, 11), (1, 3)]
SWAPPED_UNUSUAL = [(0, 1), (3, 0), (0, 5), (2, 3), (5, 2), (4, 5), (6, 7)]

# The expected rows, written by hand from the topology of the plan.
# (low index, high index, degree of low, degree of high, engines listing the pair)
CROSS = [
    (0, 3, 4, 3, 1), (0, 5, 4, 3, 1), (2, 3, 4, 3, 1), (2, 5, 4, 3, 1),
    (0, 1, 4, 2, 2), (2, 7, 4, 2, 1),
    (4, 5, 1, 3, 1), (6, 7, 1, 2, 1), (8, 9, 1, 1, 1), (10, 11, 1, 1, 1),
]
OPEN_OPEN = [(1, 3, 2, 3, 1)]
UNCLASSED = [
    (0, 2, 4, 4, 1),
    (0, 3, 4, 3, 1), (0, 5, 4, 3, 1), (2, 3, 4, 3, 1), (2, 5, 4, 3, 1),
    (0, 1, 4, 2, 2), (2, 7, 4, 2, 1),
    (1, 3, 2, 3, 1), (4, 5, 1, 3, 1), (6, 7, 1, 2, 1), (8, 9, 1, 1, 1), (10, 11, 1, 1, 1),
]
# (record index, degree, cross, open_open, licensed_licensed)
SPINES = [(0, 4, 3, 0, 1), (2, 4, 3, 0, 1), (3, 3, 2, 1, 0), (5, 3, 3, 0, 0)]


def make(tmp_path: Path, name: str = "run", **kwargs: Any) -> Path:
    options: dict[str, Any] = {"n_records": 12, "unusual": UNUSUAL, "wording": WORDING}
    options.update(kwargs)
    return make_seed_run(tmp_path, name=name, **options)


def candidates_of(run: Path, min_degree: int = 3) -> Any:
    from mindrian_eureka.seed.candidates import build_candidates
    from mindrian_eureka.seed.graph import build_pair_graph
    from mindrian_eureka.seed.source import load_source

    return build_candidates(build_pair_graph(load_source(run).run), min_degree)


def row_ids(rows: Any) -> list[tuple[str, str, str]]:
    return [(row.pair_id, row.left_id, row.right_id) for row in rows]


def expected_ids(rows: list[tuple[int, int, int, int, int]]) -> list[tuple[str, str, str]]:
    return [(pair_id_of(i, j), record_id(i), record_id(j)) for i, j, *_ in rows]


def run_main(argv: list[str]) -> int:
    try:
        return main(argv)
    except SystemExit as stop:
        assert isinstance(stop.code, int)
        return stop.code


@pytest.fixture
def run(tmp_path: Path) -> Path:
    return make(tmp_path)


def test_candidate_order_matches_the_topology_section(run: Path) -> None:
    result = candidates_of(run)
    assert list(result.groups) == ["cross", "open_open"]
    assert row_ids(result.groups["cross"]) == expected_ids(CROSS)
    assert row_ids(result.groups["open_open"]) == expected_ids(OPEN_OPEN)
    for group, expected in (("cross", CROSS), ("open_open", OPEN_OPEN)):
        for row, (_i, _j, left_degree, right_degree, engines) in zip(
            result.groups[group], expected, strict=True
        ):
            assert (row.left_degree, row.right_degree) == (left_degree, right_degree)
            assert len(row.engines) == engines
    both = next(row for row in result.groups["cross"] if row.pair_id == pair_id_of(0, 1))
    assert both.engines == ("unusual_pairs", "wording_and_meaning")
    only = next(row for row in result.groups["cross"] if row.pair_id == pair_id_of(2, 7))
    assert only.engines == ("wording_and_meaning",)
    listed = {row.pair_id for rows in result.groups.values() for row in rows}
    assert pair_id_of(0, 2) not in listed
    assert result.min_degree == 3
    assert [(s.record_id, s.degree) for s in result.spines] == [
        (record_id(i), degree) for i, degree, *_ in SPINES
    ]
    for spine, (_i, _degree, cross, open_open, licensed) in zip(
        result.spines, SPINES, strict=True
    ):
        assert spine.classes == {
            "cross": cross,
            "licensed_licensed": licensed,
            "open_open": open_open,
        }


def test_tie_breaks_by_record_id(tmp_path: Path, run: Path) -> None:
    result = candidates_of(run)
    degrees = [(s.record_id, s.degree) for s in result.spines]
    assert degrees[:2] == [(record_id(0), 4), (record_id(2), 4)]
    assert degrees[2:] == [(record_id(3), 3), (record_id(5), 3)]
    swapped = make(tmp_path, name="swapped", unusual=SWAPPED_UNUSUAL)
    again = candidates_of(swapped)
    assert row_ids(again.groups["cross"]) == row_ids(result.groups["cross"])
    assert [s.record_id for s in again.spines] == [s.record_id for s in result.spines]


def test_run_without_classes(tmp_path: Path) -> None:
    run = make(tmp_path, with_classes=False)
    result = candidates_of(run)
    assert list(result.groups) == ["unclassed"]
    assert row_ids(result.groups["unclassed"]) == expected_ids(UNCLASSED)
    assert all(spine.classes is None for spine in result.spines)
    assert [s.record_id for s in result.spines] == [record_id(i) for i, *_ in SPINES]


def text_lines(run: Path, limit: int = 25) -> list[str]:
    from mindrian_eureka.seed.candidates import render_text

    return render_text(candidates_of(run), limit).split("\n")


def row_line(i: int, j: int, left_degree: int, right_degree: int, engines: int) -> str:
    return (
        f"  {pair_id_of(i, j)}  {record_id(i)}  {record_id(j)}  "
        f"degree {left_degree} and {right_degree}  listed by {engines} engine(s)"
    )


def test_text_output_lines(run: Path) -> None:
    lines = text_lines(run)
    expected = [f"Seed candidates for this run ({LABEL})", ""]
    expected.append("Open next to licensed (cross): 10 pairs")
    expected += [row_line(*row) for row in CROSS]
    expected += ["", "Both open (open_open): 1 pairs"]
    expected += [row_line(*row) for row in OPEN_OPEN]
    expected += ["", "Records with 3 or more pairs: 4"]
    for i, degree, cross, open_open, licensed in SPINES:
        expected.append(
            f"  {record_id(i)}  degree {degree}  cross {cross}, open_open {open_open}, "
            f"licensed_licensed {licensed}"
        )
    expected += [
        "",
        "These are counts and classes. They do not rank rooms by value.",
        "Pick one, then run: eureka seed RUN_FOLDER --pair <pair id> or "
        "eureka seed RUN_FOLDER --cluster <record id>",
        SUMMARY_LINE,
    ]
    assert lines == expected
    assert lines[-1] == SUMMARY_LINE
    text = "\n".join(lines)
    assert "–" not in text and "—" not in text
    assert "Synthetic title" not in text and "Inactive" not in text
    assert "pebbles" not in text


def test_text_limit(run: Path) -> None:
    lines = text_lines(run, 2)
    start = lines.index("Open next to licensed (cross): 10 pairs")
    assert lines[start + 1 : start + 3] == [row_line(*row) for row in CROSS[:2]]
    assert lines[start + 3].strip() == "and 8 more. Use --limit 0 to see all."
    assert sum(line.strip() == "and 2 more. Use --limit 0 to see all." for line in lines) == 1
    assert sum(line_has_pair(line) for line in lines) == 3
    everything = text_lines(run, 0)
    assert sum(line_has_pair(line) for line in everything) == 11
    assert not any(line.strip().startswith("and ") for line in everything)


def line_has_pair(line: str) -> bool:
    return line.startswith("  pair-")


def test_text_without_classes(tmp_path: Path) -> None:
    run = make(tmp_path, with_classes=False)
    lines = text_lines(run)
    assert "Pairs (no class): 12 pairs" in lines
    assert not any("(cross)" in line or "(open_open)" in line for line in lines)
    assert f"  {record_id(0)}  degree 4" in lines
    assert not any("licensed_licensed" in line for line in lines)


def test_json_output(run: Path, tmp_path: Path) -> None:
    from mindrian_eureka.run.output import canonical_json
    from mindrian_eureka.seed.candidates import to_json_dict

    data = to_json_dict(candidates_of(run), 2)
    raw = canonical_json(data).decode("utf-8")
    assert data["schema"] == "eureka.seed-candidates.v1"
    assert data["label"] == LABEL
    assert data["counts"] == {"records": 12, "pairs": 12, "min_degree": 3}
    assert list(data["groups"]) == ["cross", "open_open"]
    assert [item["pair_id"] for item in data["groups"]["cross"]] == [
        pair_id_of(i, j) for i, j, *_ in CROSS[:2]
    ]
    first = data["groups"]["cross"][0]
    assert first["left_id"] == record_id(0) and first["right_id"] == record_id(3)
    assert first["left_degree"] == 4 and first["right_degree"] == 3
    assert first["engines"] == ["unusual_pairs"]
    assert [item["record_id"] for item in data["spines"]] == [record_id(0), record_id(2)]
    assert data["spines"][0]["classes"] == {
        "cross": 3,
        "licensed_licensed": 1,
        "open_open": 0,
    }
    assert data["hidden"] == {"cross": 8, "open_open": 0, "spines": 2}
    assert data["summary_line"] == SUMMARY_LINE
    assert str(tmp_path) not in raw and "/home/" not in raw


def tree_files(base: Path) -> set[str]:
    return {p.relative_to(base).as_posix() for p in base.rglob("*")}


def test_cli_cluster_and_list(
    tmp_path: Path, run: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "cluster-out"
    assert main(["seed", str(run), "--cluster", record_id(0), "--out", str(out)]) == 0
    printed = capsys.readouterr().out
    assert "Kind: cluster. Records: 5. Evidence files: 5. Bank entries: 4." in printed
    document = json.loads((out / "seed.json").read_text(encoding="utf-8"))
    assert document["seed_kind"] == "cluster"
    assert main(["seed", str(run), "--list"]) == 0
    from mindrian_eureka.seed.candidates import render_text, to_json_dict

    assert capsys.readouterr().out.rstrip("\n") == render_text(candidates_of(run), 25)
    assert main(["seed", str(run), "--list", "--json", "--limit", "2"]) == 0
    assert json.loads(capsys.readouterr().out) == to_json_dict(candidates_of(run), 2)
    assert main(["seed", str(run), "--list", "--min-degree", "4", "--limit", "0"]) == 0
    assert capsys.readouterr().out.rstrip("\n") == render_text(candidates_of(run, 4), 0)
    assert run_main(["seed", str(run), "--list", "--out", str(tmp_path / "x")]) == 2
    assert run_main(["seed", str(run), "--pair", pair_id_of(0, 1), "--min-degree", "3"]) == 2
    assert run_main(["seed", str(run), "--cluster", record_id(4)]) == 2
    assert run_main(["seed", str(run), "--list", "--min-degree", "0"]) == 2
    assert run_main(["seed", str(run), "--list", "--limit", "-1"]) == 2
    assert run_main(["seed", str(run), "--pair", pair_id_of(0, 1), "--cluster", record_id(0)]) == 2
    assert run_main(["seed", str(run)]) == 2
    err = capsys.readouterr().err
    assert "--min-degree" in err and "--pair" in err
    assert not (tmp_path / "x").exists()
    # A lower minimum lets a smaller cluster through.
    small = tmp_path / "small"
    assert main(["seed", str(run), "--cluster", record_id(4), "--min-degree", "1",
                 "--out", str(small)]) == 0


def test_list_is_read_only(tmp_path: Path, run: Path) -> None:
    before_tree = tree_hash(run)
    before_files = tree_files(tmp_path)
    assert main(["seed", str(run), "--list"]) == 0
    assert main(["seed", str(run), "--list", "--json"]) == 0
    assert tree_files(tmp_path) == before_files
    assert tree_hash(run) == before_tree
    assert main(["seed", str(run), "--cluster", record_id(0), "--out", str(tmp_path / "o")]) == 0
    assert tree_hash(run) == before_tree


def test_list_makes_no_network_call(
    run: Path, no_network: list[object], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["seed", str(run), "--list"]) == 0
    assert main(["seed", str(run), "--cluster", record_id(0), "--out", str(run.parent / "n")]) == 0
    capsys.readouterr()
    assert no_network == []
