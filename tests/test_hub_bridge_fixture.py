"""Exercise synthetic Potential eureka coverage and the honest real empty state."""

from __future__ import annotations

import copy
import json
import tomllib
from pathlib import Path
from unittest.mock import patch

import pytest
from hashing_stub import HashingEncoder
from hub_support import build_run_folder_with_potential_eureka, tree_hash
from mindrian_eureka.hub.assets import all_assets
from mindrian_eureka.hub.deck import DECK, fill
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.page import render_page
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.hub.verify import verify_payload
from mindrian_eureka.run.contracts import LABEL

REPO = Path(__file__).resolve().parents[1]
PUBLIC = REPO / "tests/fixtures/hub_public"
MARKER = "synthetic test fixture, not a finding"
EXPECTED_BRIDGES = ["synthetic-b-000", "synthetic-z-connector"]


def _file_bytes(folder: Path) -> dict[str, bytes]:
    return {
        path.relative_to(folder).as_posix(): path.read_bytes()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def test_synthetic_model_has_two_neighborhoods_earned_graph_and_stable_bridge_order(
    tmp_path: Path,
) -> None:
    first = build_payload(load_run(build_run_folder_with_potential_eureka(tmp_path / "first")))
    second = build_payload(load_run(build_run_folder_with_potential_eureka(tmp_path / "second")))
    assert len(first["hoods"]) == 2
    assert first["graph"]["visible_records"] == 21 and first["graph"]["earned"]
    assert [item["record_id"] for item in first["bridges"]] == EXPECTED_BRIDGES
    assert [item["rank"] for item in first["bridges"]] == [1, 2]
    assert first == second
    assert first["engines"]["unusual_pairs"]["floor"] == 0.9
    assert first["engines"]["wording_and_meaning"]["floor"] is None
    assert first["counts"]["weak_pairs"] == 0
    for bridge in first["bridges"]:
        assert len(bridge["hoods"]) >= 2


def test_two_synthetic_builds_have_identical_files_and_bytes(tmp_path: Path) -> None:
    first = build_run_folder_with_potential_eureka(tmp_path / "one")
    second = build_run_folder_with_potential_eureka(tmp_path / "two", name="different-run-name")
    assert _file_bytes(first) == _file_bytes(second)
    assert tree_hash(first) == tree_hash(second)
    assert set(_file_bytes(first)) == {
        "corpus/records.jsonl",
        "unusual-pairs.json",
        "wording-and-meaning-pairs.json",
        "ranked-pairs.md",
        "manifest.json",
    }


def test_potential_eureka_payload_binds_candidate_status_and_source(tmp_path: Path) -> None:
    payload = build_payload(load_run(build_run_folder_with_potential_eureka(tmp_path)))
    assert verify_payload(payload) == []
    assert DECK["P06.eureka"] == "Potential eureka"
    records = {record["id"]: record for record in payload["records"]}
    pairs = {pair["key"]: pair for pair in payload["pairs"]}
    for bridge in payload["bridges"]:
        record = records[bridge["record_id"]]
        assert record["bridge"] and record["bridge_rank"] == bridge["rank"]
        assert record["label"] == LABEL and record["source_link"]
        assert fill(DECK["Gr15"], ID=record["id"]) == "Potential eureka " + record["id"]
        for key in record["pair_keys"]:
            assert pairs[key]["label"] == LABEL
            assert all(pairs[key][side]["source_link"] for side in ("left", "right"))


@pytest.mark.parametrize("field", ["label", "source_link"])
def test_potential_eureka_cannot_lose_qualifier_or_source(tmp_path: Path, field: str) -> None:
    payload = build_payload(load_run(build_run_folder_with_potential_eureka(tmp_path)))
    altered = copy.deepcopy(payload)
    record = next(record for record in altered["records"] if record["bridge"])
    record[field] = ""
    assert any(record["id"] in problem for problem in verify_payload(altered))


def test_helper_uses_existing_encoder_stub_without_model_or_network(
    tmp_path: Path,
    no_network: list[object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbid_model(*args: object, **kwargs: object) -> None:
        raise AssertionError("A synthetic fixture must not load a real model")

    monkeypatch.setattr("mindrian_eureka.run.engines.load_local_encode", forbid_model)
    with patch.object(
        HashingEncoder, "encode", autospec=True, side_effect=HashingEncoder.encode
    ) as encode:
        folder = build_run_folder_with_potential_eureka(tmp_path)
    assert encode.call_count == 1
    assert len(encode.call_args.args[1]) == 21
    assert not no_network
    manifest = json.loads((folder / "manifest.json").read_text())
    assert MARKER in manifest["model"]["name"] and manifest["model"]["snapshot"] is None


def test_synthetic_data_is_marked_and_never_changes_the_public_example(tmp_path: Path) -> None:
    before = tree_hash(PUBLIC)
    run = load_run(build_run_folder_with_potential_eureka(tmp_path))
    assert tree_hash(PUBLIC) == before
    for record in run.records:
        assert record.id.startswith("synthetic-")
        assert record.title.lower().startswith("synthetic test fixture")
        assert "not a finding" in record.title and MARKER in record.text
    config = tomllib.loads((REPO / "pyproject.toml").read_text())
    assert config["tool"]["setuptools"]["packages"]["find"]["where"] == ["src"]
    assert not any("synthetic-potential-eureka" in item.output_path for item in all_assets())
    assert all(MARKER in note for engine in run.engines.values() for note in engine.notes)


def test_real_public_example_keeps_honest_none_and_actual_cutoff_copy() -> None:
    payload = build_payload(load_run(PUBLIC / "run"))
    assert payload["bridges"] == [] and payload["counts"]["weak_pairs"] == 0
    content = render_page(payload, files={item.output_path for item in all_assets()}).decode()
    assert DECK["Gr09"] in content
    assert (
        fill(DECK["B05.one.unusual_pairs"], floor=payload["engines"]["unusual_pairs"]["floor_text"])
        in content
    )
    assert DECK["B06"] in content
    # P06.hidden describes an actual weak row, not an absence of bridge records.
    assert DECK["P06.hidden"] == "Hidden by default"
    assert DECK["P06.hidden"] not in content
