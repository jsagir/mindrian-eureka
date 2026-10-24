"""Tests for the shared test scaffold (hashing encoder and fixtures)."""

from __future__ import annotations

import csv
import json
import os
import socket
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
from conftest import InputSet
from hashing_stub import EMBED_DIM, HashingEncoder, hashing_encode

TESTS_DIR = str(Path(__file__).resolve().parent)


def test_hashing_encode_shape_and_unit_norm() -> None:
    vectors = hashing_encode(["alpha beta gamma", "delta epsilon", "alpha"])
    assert vectors.shape == (3, EMBED_DIM)
    assert EMBED_DIM == 64
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0)


def test_hashing_encode_is_deterministic_in_process() -> None:
    first = hashing_encode(["same words here"])
    second = hashing_encode(["same words here"])
    assert first.tobytes() == second.tobytes()


def test_hashing_encode_is_deterministic_across_processes() -> None:
    code = (
        f"import sys; sys.path.insert(0, {TESTS_DIR!r});"
        "from hashing_stub import hashing_encode;"
        "sys.stdout.buffer.write(hashing_encode(['same words here']).tobytes())"
    )
    other = subprocess.run(
        [sys.executable, "-I", "-c", code], capture_output=True, check=True
    ).stdout
    # The subprocess needs numpy from the same interpreter; compare the raw bytes.
    assert other == hashing_encode(["same words here"]).tobytes()


def test_empty_text_gives_finite_unit_vector() -> None:
    vector = hashing_encode([""])[0]
    assert np.all(np.isfinite(vector))
    assert float(np.linalg.norm(vector)) == pytest.approx(1.0)


def test_hashing_encoder_class_matches_interface() -> None:
    encoder = HashingEncoder("some/path", allow_download=False, revision=None)
    assert encoder.name == "sentence-transformers"
    assert encoder.version == "some/path"
    assert encoder.encode(["a b"], cancel_check=None).shape == (1, EMBED_DIM)


def test_isolated_env_sets_variables_and_leaves_folders_absent(
    isolated_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert os.environ["HOME"] == str(isolated_env)
    assert os.environ["USERPROFILE"] == str(isolated_env)
    cache = Path(os.environ["MINDRIAN_EUREKA_CACHE_DIR"])
    data = Path(os.environ["MINDRIAN_EUREKA_DATA_DIR"])
    assert cache.parent == isolated_env
    assert data.parent == isolated_env
    assert not cache.exists()
    assert not data.exists()
    assert Path(os.environ["HF_HOME"]).parent == isolated_env
    for name in ("HF_HUB_CACHE", "MINDRIAN_EUREKA_RS_MODEL_PATH", "NO_COLOR", "HF_HUB_OFFLINE"):
        assert name not in os.environ


def test_fake_model_dir_has_four_files(fake_model_dir: Path) -> None:
    names = sorted(path.name for path in fake_model_dir.iterdir())
    assert names == ["config.json", "model.safetensors", "modules.json", "tokenizer.json"]


def test_no_network_records_and_raises(no_network: list[object]) -> None:
    with pytest.raises(RuntimeError, match="network call blocked"):
        socket.create_connection(("example.com", 80))
    assert no_network == [("example.com", 80)]


def test_hashing_encoder_fixture_patches_runner(hashing_encoder: type[HashingEncoder]) -> None:
    import mindrian_eureka.opportunity_pairs.runner as runner

    assert runner.SentenceTransformerEncoder is hashing_encoder


@pytest.mark.parametrize("kind", ["csv", "markdown"])
def test_tmp_inputs_gives_32_ids(tmp_inputs: Callable[..., InputSet], kind: str) -> None:
    inputs = tmp_inputs(kind)
    assert len(inputs.ids) == 32
    assert inputs.ids == sorted(inputs.ids)
    assert inputs.folder.is_dir()
    assert inputs.kind == kind


def test_tmp_inputs_markdown_layout(tmp_inputs: Callable[..., InputSet]) -> None:
    inputs = tmp_inputs("markdown", count=5)
    files = sorted((inputs.folder / "synthetic").glob("*.md"))
    assert len(files) == 5
    assert inputs.mapping_flags == []
    assert inputs.mapping_file is None
    assert files[0].read_text(encoding="utf-8").startswith("# ")
    assert all(item.startswith("synthetic/") for item in inputs.ids)


def test_tmp_inputs_csv_header_and_mapping(tmp_inputs: Callable[..., InputSet]) -> None:
    inputs = tmp_inputs("csv", name="csvset")
    with (inputs.folder / "records.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == ["case_id", "title", "description", "state_code"]
    assert len(rows) == 33
    assert {row[3] for row in rows[1:]} == {"1", "2", "3", "4"}
    assert inputs.mapping_file is not None
    assert inputs.mapping_file.parent == inputs.folder.parent
    mapping = json.loads(inputs.mapping_file.read_text(encoding="utf-8"))
    assert mapping["schema_version"] == "eureka.run-mapping.v1"
    entry = mapping["files"]["*"]
    assert entry["text_columns"] == ["description"]
    assert inputs.mapping_flags == [
        "--id-column", "case_id", "--title-column", "title", "--text-column", "description",
    ]
    assert all(item.startswith("records/") for item in inputs.ids)


def test_tmp_inputs_count_is_capped_at_32(tmp_inputs: Callable[..., InputSet]) -> None:
    assert len(tmp_inputs("markdown", count=99).ids) == 32
