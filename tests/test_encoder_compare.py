"""Tests of the encoder comparison harness `scripts/encoder-compare.py` and its page.

The harness runs on the CPU here. Unit tests use small numpy arrays and a fake encoder, so no
model loads there. One gated test loads the real MiniLM model. The record tests tie the page
`docs/encoder-comparison.md` to the log `docs/encoder-evidence/cpu-compare-log.json`, so a
number that the log does not hold cannot stay on the page.
"""

from __future__ import annotations

import getpass
import hashlib
import importlib.util
import json
import re
import socket
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import numpy as np
import pytest
from mindrian_eureka.encoder_spec import profile_spec
from mindrian_eureka.run import project as run_project
from mindrian_eureka.run.contracts import Record

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "encoder-compare.py"
SPIKE_SCRIPT = ROOT / "scripts" / "encoder-spike.py"
RECORDS = ROOT / "examples" / "public-example" / "reference-run" / "corpus" / "records.jsonl"
REFERENCE_RUN = ROOT / "examples" / "public-example" / "reference-run"
PAGE = ROOT / "docs" / "encoder-comparison.md"
CPU_LOG = ROOT / "docs" / "encoder-evidence" / "cpu-compare-log.json"
# After the owner run, the harness writes the merged log to `compare-log.json`; the page then
# follows that file. Until it exists, the page follows the CPU log.
MERGED_LOG = ROOT / "docs" / "encoder-evidence" / "compare-log.json"
LOG = MERGED_LOG if MERGED_LOG.is_file() else CPU_LOG
VECTORS = ROOT / "docs" / "encoder-evidence" / "minilm-cpu-vectors.npz"
START = "<!-- compare-table:start -->"
END = "<!-- compare-table:end -->"
SCHEMA = "eureka.encoder-compare-log.v1"
HEADER_ROW = (
    "| Measure | MiniLM (cpu-default) | mdbr-leaf-ir | Nemotron-3-Embed-1B-BF16 | Source |"
)


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def compare() -> ModuleType:
    return load_module("encoder_compare", SCRIPT)


@pytest.fixture(scope="module")
def records(compare: ModuleType) -> list[dict[str, Any]]:
    return compare.load_records(RECORDS)


class FakeEncoder:
    """An encoder with the `encode_raw` call of the real one and a spec. No model."""

    def __init__(self, width: int = 8, seed: int = 0) -> None:
        self.width = width
        self.seed = seed
        self.spec = profile_spec("cpu-default")
        self.calls: list[int] = []

    def encode_raw(self, texts: list[str]) -> np.ndarray:
        self.calls.append(len(texts))
        rows = []
        for text in texts:
            digest = hashlib.sha256(f"{self.seed}|{text}".encode()).digest()
            state = np.random.RandomState(int.from_bytes(digest[:4], "big"))
            rows.append(state.standard_normal(self.width))
        return np.asarray(rows, dtype=np.float32)


def fake_vectors_file(path: Path, ids: list[str], width: int = 8, fingerprint: str | None = None):
    state = np.random.RandomState(5)
    vectors = state.standard_normal((len(ids), width)).astype(np.float32)
    payload: dict[str, Any] = {"ids": np.array(ids), "vectors": vectors}
    if fingerprint is not None:
        payload["fingerprint"] = np.array(fingerprint)
    np.savez(path, **payload)
    return vectors


# --- text and pair rules ---------------------------------------------------------------------


def test_model_text_and_pair_key_match_production(compare: ModuleType) -> None:
    record = Record(
        id="a", title="T", text="body", source_ref="r", source_file="f", text_sha256="0" * 64
    )
    assert compare.model_text({"title": "T", "text": "body"}) == record.model_text
    assert compare.model_text({"title": "", "text": "  body  "}) == "body"
    assert compare.pair_key("b", "a") == compare.pair_key("a", "b")
    assert compare.pair_key("a", "b") == run_project._pair_id("a", "b")


def test_load_records_reads_the_36_records(records: list[dict[str, Any]]) -> None:
    assert len(records) == 36
    assert all(item.get("record_type") == "record" for item in records)
    ids = [item["id"] for item in records]
    assert len(set(ids)) == 36


# --- dense top pairs and overlap -------------------------------------------------------------


def test_dense_top_pairs(compare: ModuleType) -> None:
    ids = ["r0", "r1", "r2", "r3"]
    vectors = np.array(
        [[1.0, 0.0], [0.96, 0.28], [0.0, 1.0], [-1.0, 0.0]], dtype=np.float64
    )
    expected = [
        compare.pair_key("r0", "r1"),  # cosine 0.96
        compare.pair_key("r1", "r2"),  # cosine 0.28
        compare.pair_key("r0", "r2"),  # cosine 0.0, tie with (r2, r3): lower index pair first
        compare.pair_key("r2", "r3"),  # cosine 0.0
    ]
    assert compare.dense_top_pairs(vectors, ids, k=3) == expected[:3]
    assert compare.dense_top_pairs(vectors * 7.5, ids, k=3) == expected[:3]
    everything = compare.dense_top_pairs(vectors, ids, k=100)
    assert len(everything) == 6
    assert everything[:4] == expected
    with pytest.raises(ValueError):
        compare.dense_top_pairs(np.ones((1, 3)), ["only"], k=3)


def test_overlap_matrix(compare: ModuleType) -> None:
    tops = {
        "one": ["a", "b", "c", "d"],
        "two": ["a", "b", "x", "y"],
        "three": ["w", "x", "y", "z"],
    }
    matrix = compare.overlap_matrix(tops)
    assert matrix["one"]["one"] == 1.0
    assert matrix["one"]["two"] == 0.5
    assert matrix["two"]["one"] == 0.5
    assert matrix["one"]["three"] == 0.0
    assert matrix["two"]["three"] == 0.5
    for left in tops:
        for right in tops:
            assert matrix[left][right] == matrix[right][left]
    from mindrian_eureka.example.check import ranking_overlap

    assert matrix["two"]["three"] == ranking_overlap(tops["two"], tops["three"])


# --- the folder probe ------------------------------------------------------------------------


def test_probe_folder_reports_what_is_missing(compare: ModuleType, tmp_path: Path) -> None:
    onnx_only = tmp_path / "onnx-only"
    (onnx_only / "onnx").mkdir(parents=True)
    for name in ("config.json", "tokenizer.json", "onnx/model_quantized.onnx"):
        (onnx_only / name).write_text("x")
    ok, reason = compare.probe_sentence_folder(onnx_only)
    assert ok is False
    assert "modules.json" in reason
    assert "model.safetensors" in reason
    assert "ONNX files only" in reason

    good = tmp_path / "good"
    good.mkdir()
    for name in ("config.json", "modules.json", "model.safetensors", "tokenizer.json"):
        (good / name).write_text("x")
    assert compare.probe_sentence_folder(good) == (True, "")

    ok, reason = compare.probe_sentence_folder(tmp_path / "absent")
    assert ok is False
    assert "not found" in reason


# --- the log ---------------------------------------------------------------------------------


def make_log(
    compare: ModuleType,
    records: list[dict[str, Any]],
    tmp_path: Path,
    vectors_in: dict[str, Path] | None = None,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    missing_folder = tmp_path / "no-mdbr-folder"
    return compare.build_log(
        records,
        minilm=(FakeEncoder(), 1.25),
        mdbr_dir=missing_folder,
        vectors_in=vectors_in or {},
        repeats=2,
        top_k=200,
        recorded_on="2026-01-01",
    )


def test_not_run_columns_carry_a_reason(
    compare: ModuleType, records: list[dict[str, Any]], tmp_path: Path
) -> None:
    log, _vectors = make_log(compare, records, tmp_path)
    assert log["columns"]["minilm"]["status"] == "run"
    for name in ("mdbr_leaf_ir", "nemotron"):
        column = log["columns"][name]
        assert column["status"] == "not_run"
        assert column["reason"]
        for key in (
            "dimension",
            "fingerprint",
            "load_seconds",
            "median_seconds",
            "texts_per_second",
            "top_pairs_count",
        ):
            assert column[key] is None
    reason = log["columns"]["nemotron"]["reason"]
    assert "owner" in reason
    assert "05-08" in reason
    assert set(log["overlap"]) == {"minilm"}


def test_vectors_in_fills_a_column(
    compare: ModuleType, records: list[dict[str, Any]], tmp_path: Path
) -> None:
    ids = [item["id"] for item in records]
    path = tmp_path / "nemotron.npz"
    fingerprint = "sha256:" + "ab" * 32
    fake_vectors_file(path, ids, width=8, fingerprint=fingerprint)
    log, _vectors = make_log(compare, records, tmp_path, {"nemotron": path})
    column = log["columns"]["nemotron"]
    assert column["status"] == "from_file"
    assert column["dimension"] == 8
    assert column["fingerprint"] == fingerprint
    assert column["texts_per_second"] is None
    assert column["top_pairs_count"] == 200
    assert 0.0 <= log["overlap"]["minilm"]["nemotron"] <= 1.0
    assert log["overlap"]["minilm"]["nemotron"] == log["overlap"]["nemotron"]["minilm"]

    wrong = tmp_path / "wrong.npz"
    swapped = list(ids)
    swapped[3] = "not-a-record"
    fake_vectors_file(wrong, swapped)
    with pytest.raises(ValueError, match="not-a-record"):
        make_log(compare, records, tmp_path, {"nemotron": wrong})


def test_render_table_is_stable_and_marks_every_gap(
    compare: ModuleType, records: list[dict[str, Any]], tmp_path: Path
) -> None:
    log, _vectors = make_log(compare, records, tmp_path)
    text = compare.render_table(log)
    assert text == compare.render_table(log)
    lines = text.split("\n")
    assert lines[0] == HEADER_ROW
    rows = [line for line in lines[2:] if line.strip()]
    assert rows
    assert all(line.count("|") == 6 for line in rows)
    for line in rows:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        assert cells[2] == "NOT RUN"
        assert cells[3] == "NOT RUN"
    allowed: set[str] = set()

    def collect(node: Any) -> None:
        if isinstance(node, dict):
            for item in node.values():
                collect(item)
        elif isinstance(node, list):
            for item in node:
                collect(item)
        elif isinstance(node, (int, float)) and not isinstance(node, bool):
            allowed.update({f"{node:.2f}", f"{node:.4f}", str(int(node))})

    collect(log)
    for line in rows:
        for cell in [part.strip() for part in line.strip("|").split("|")][1:4]:
            for number in re.findall(r"\d+(?:\.\d+)?", cell):
                assert number in allowed, (number, line)

    filled = tmp_path / "nemotron.npz"
    fake_vectors_file(filled, [item["id"] for item in records], width=8)
    log2, _ = make_log(compare, records, tmp_path, {"nemotron": filled})
    rows2 = compare.render_table(log2)
    assert "| 8 |" in rows2 or " 8 | " in rows2


# --- the page and the log on disk ------------------------------------------------------------


def page_table() -> str:
    text = PAGE.read_text(encoding="utf-8")
    assert text.count(START) == 1
    assert text.count(END) == 1
    between = text.split(START, 1)[1].split(END, 1)[0]
    return between.strip("\n")


def test_page_table_equals_the_render_of_the_log(compare: ModuleType) -> None:
    log = json.loads(LOG.read_text(encoding="utf-8"))
    assert log["schema_version"] == SCHEMA
    assert page_table() == compare.render_table(log)
    text = PAGE.read_text(encoding="utf-8")
    assert "candidate, not verified" in text
    assert "The owner decides" in text
    assert "docs/encoder-evidence/cpu-compare-log.json" in text
    assert "\u2014" not in text
    assert "\u2013" not in text
    for heading in (
        "# Encoder comparison on the 36-record example",
        "## What this compares",
        "## How it was measured",
        "## Results",
        "## What the numbers do not show",
        "## Next step and who decides",
    ):
        assert heading in text


def test_no_invented_nemotron_number() -> None:
    log = json.loads(LOG.read_text(encoding="utf-8"))
    if log["columns"]["nemotron"]["status"] != "not_run":
        pytest.skip("The Nemotron column holds a vectors file from the owner run.")
    for line in page_table().split("\n")[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        assert cells[3] == "NOT RUN"
        assert not re.search(r"\d", cells[3])


def test_log_matches_the_machine_facts() -> None:
    log = json.loads(LOG.read_text(encoding="utf-8"))
    assert log["records"] == 36
    assert log["pairs"] == 630
    assert log["top_k"] == 200
    column = log["columns"]["minilm"]
    assert column["status"] == "run"
    with np.load(VECTORS, allow_pickle=False) as data:
        assert len(data["ids"]) == 36
        assert data["vectors"].shape == (36, column["dimension"])
        stored = str(data["fingerprint"])
        assert str(data["encoding_rule"]) == log["encoding_rule"]
    assert column["fingerprint"] == stored
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", stored)
    assert len(column["loadavg_before"]) == 3
    assert len(column["loadavg_after"]) == 3
    assert set(log["computer"]) == {"machine", "cores", "system"}


def test_npz_layout_agrees_with_the_spike_script(
    compare: ModuleType, records: list[dict[str, Any]]
) -> None:
    """The spike script reads `ids` and `vectors` of this file. Run its own drift code on it."""
    spike = load_module("encoder_spike_for_compare", SPIKE_SCRIPT)
    spike_records = spike.read_records(RECORDS)
    spike_ids = [item["id"] for item in spike_records]
    assert spike_ids == [item["id"] for item in records]
    texts = [spike.model_text(item) for item in spike_records]
    assert texts == [compare.model_text(item) for item in records]
    assert spike.pair_key("x", "y") == compare.pair_key("x", "y")

    with np.load(VECTORS, allow_pickle=False) as data:
        saved = np.asarray(data["vectors"])
        assert [str(item) for item in data["ids"]] == spike_ids
    assert saved.dtype == np.float32

    class Backend:
        def __init__(self) -> None:
            self.embedded: list[list[str]] = []
            self.unloaded: list[Any] = []

        def load(self, model_id: str, path: str, dtype: str, attention: str | None) -> Any:
            return SimpleNamespace(model=None, load_seconds=0.0, native_max_seq_length=None)

        def embed(self, handle: Any, texts_in: list[str], batch: int, repeats: int) -> Any:
            self.embedded.append(texts_in)
            return {"vectors": saved, "seconds": [1.0], "peak_allocated_bytes": 0}

        def unload(self, handle: Any) -> None:
            self.unloaded.append(handle)

    backend = Backend()
    args = SimpleNamespace(cpu_vectors=str(VECTORS), minilm_dir="unused-folder")
    log: dict[str, Any] = spike.skeleton_log()
    ok = spike.run_minilm_drift(backend, args, spike_records, spike_ids, log, ())
    assert ok is True
    assert log["drift"]["minilm_gpu_vs_cpu"]["error"] is None
    assert log["drift"]["minilm_gpu_vs_cpu"]["top200_overlap"] == 1.0
    assert backend.embedded == [texts]


def test_real_minilm_run_reproduces_the_saved_vectors(compare: ModuleType) -> None:
    pytest.importorskip("sentence_transformers")
    from mindrian_eureka import models
    from mindrian_eureka.opportunity_pairs.encoders import make_encoder

    resolution = models.discover_model()
    if not resolution.ok:
        pytest.skip("The MiniLM model folder is not on this computer.")
    torch = pytest.importorskip("torch")
    torch.set_num_threads(1)
    items = compare.load_records(RECORDS)
    texts = [compare.model_text(item) for item in items]
    ids = [item["id"] for item in items]
    encoder = make_encoder(profile_spec("cpu-default"), model_path=str(resolution.path))
    fresh = compare.encode_whole(encoder, texts)
    assert fresh.dtype == np.float32
    with np.load(VECTORS, allow_pickle=False) as data:
        saved = np.asarray(data["vectors"])
    assert fresh.shape == saved.shape
    assert compare.dense_top_pairs(fresh, ids) == compare.dense_top_pairs(saved, ids)
    assert np.allclose(fresh, saved, atol=1e-4)


def test_log_holds_no_path_or_user() -> None:
    text = LOG.read_text(encoding="utf-8")
    for forbidden in ("/home", "/Users", "C:\\", getpass.getuser(), socket.gethostname()):
        if forbidden:
            assert forbidden not in text, forbidden


def test_script_imports_stay_light_until_a_model_is_needed() -> None:
    code = (
        "import importlib.util, sys\n"
        f"spec = importlib.util.spec_from_file_location('ec', {str(SCRIPT)!r})\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(module)\n"
        "heavy = [n for n in ('torch', 'sentence_transformers', 'transformers') "
        "if n in sys.modules]\n"
        "print('HEAVY:' + ','.join(heavy))\n"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "HEAVY:"


def test_engine_overlap_compares_pair_id_lists(compare: ModuleType) -> None:
    result = compare.engine_overlap(REFERENCE_RUN, REFERENCE_RUN)
    assert result["unusual_pairs"] == 1.0
    assert result["wording_and_meaning"] == 1.0


def test_update_log_adds_a_vectors_file_without_a_model(
    compare: ModuleType, records: list[dict[str, Any]], tmp_path: Path
) -> None:
    ids = [item["id"] for item in records]
    base, vectors = make_log(compare, records, tmp_path)
    path = tmp_path / "nemotron.npz"
    fake_vectors_file(path, ids, width=16)
    merged = compare.update_log(base, vectors, ids, {"nemotron": path})
    assert merged["columns"]["nemotron"]["status"] == "from_file"
    assert merged["columns"]["nemotron"]["dimension"] == 16
    assert merged["columns"]["minilm"] == base["columns"]["minilm"]
    assert "nemotron" in merged["overlap"]["minilm"]
    assert base["columns"]["nemotron"]["status"] == "not_run"
    with pytest.raises(ValueError):
        compare.update_log(base, vectors, ids, {"minilm": path})
