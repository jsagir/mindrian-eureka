"""Tests for the manifest and run-info builders (plan 02-04, task 3)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from mindrian_eureka import __version__
from mindrian_eureka.run import manifest
from mindrian_eureka.run.contracts import (
    LABEL,
    MANIFEST_SCHEMA,
    RUN_INFO_SCHEMA,
    SCORE_MEANING,
    UNUSUAL_PAIRS_CAPABILITY,
    WORDING_AND_MEANING_CAPABILITY,
)
from mindrian_eureka.run.output import canonical_json

SRC_DIR = str(Path(__file__).resolve().parents[1] / "src")
SNAPSHOT = "0123456789abcdef0123456789abcdef01234567"
TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:")

STRING = {"type": "string"}
MANIFEST_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": [
        "schema_version",
        "label",
        "score_meaning",
        "tool",
        "inputs",
        "corpus",
        "settings",
        "seeds",
        "model",
        "environment",
        "outputs",
        "engine_notes",
    ],
    "properties": {
        "schema_version": {"const": MANIFEST_SCHEMA},
        "label": {"const": LABEL},
        "score_meaning": {
            "type": "object",
            "required": ["unusual_pairs", "wording_and_meaning"],
        },
        "tool": {
            "type": "object",
            "required": ["name", "version", "engines"],
            "properties": {
                "engines": {
                    "type": "object",
                    "required": ["unusual_pairs", "wording_and_meaning"],
                    "properties": {
                        "unusual_pairs": {
                            "type": "object",
                            "required": [
                                "capability_id",
                                "capability_version",
                                "scoring",
                                "tie_break",
                                "method_version",
                            ],
                        },
                        "wording_and_meaning": {
                            "type": "object",
                            "required": ["capability_id", "reference_sha256", "params_hash"],
                        },
                    },
                }
            },
        },
        "outputs": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["path", "sha256", "bytes"],
                "properties": {
                    "path": STRING,
                    "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    "bytes": {"type": "integer"},
                },
            },
        },
        "engine_notes": {"type": "array", "items": STRING},
    },
}


def _engine_sections() -> dict[str, Any]:
    """Hand-built sections shaped like the output of engines.manifest_engine_sections."""
    return {
        "engines": {
            "unusual_pairs": {
                "capability_id": UNUSUAL_PAIRS_CAPABILITY,
                "capability_version": "0.1.0",
                "scoring": "hybrid_2026",
                "method_version": "rs-hybrid-2026",
                "tie_break": "stable descending top-7 term sort",
            },
            "wording_and_meaning": {
                "capability_id": WORDING_AND_MEANING_CAPABILITY,
                "reference": "hsi_reference.py",
                "reference_sha256": "a" * 64,
                "params_hash": "7affae3c94c6bed9",
            },
        },
        "settings": {"unusual_pairs": {"top_k": 20}, "wording_and_meaning": {"tier": 1}},
        "seeds": {"unusual_pairs_svd_random_state": 256, "wording_and_meaning_lsa_seed": 42},
        "engine_notes": ["Note b.", "Note a."],
    }


def _build(tmp_path: Path, model_dir: Path) -> dict[str, Any]:
    source = tmp_path / "records.csv"
    source.write_text("id,text\n1,hello\n", encoding="utf-8")
    sections = _engine_sections()
    return manifest.build_manifest(
        engines=sections["engines"],
        inputs={
            "files": [
                {
                    "path": "records.csv",
                    "bytes": source.stat().st_size,
                    "sha256": manifest.sha256_file(source),
                }
            ],
            "folder_digest": "d" * 64,
        },
        corpus={"records_read": 1, "records_used": 1, "dropped": [], "caps_hit": []},
        settings=sections["settings"],
        seeds=sections["seeds"],
        model=manifest.model_fingerprint(model_dir),
        environment=manifest.collect_environment(None),
        outputs=[
            {"path": "unusual-pairs.json", "sha256": "b" * 64, "bytes": 10},
            {"path": "corpus/records.jsonl", "sha256": "c" * 64, "bytes": 5},
        ],
        engine_notes=sections["engine_notes"],
    )


# --- sha256_file ------------------------------------------------------------


def test_sha256_file_streams_large_file(tmp_path: Path) -> None:
    data = os.urandom(3 * 1024 * 1024 + 17)
    path = tmp_path / "big.bin"
    path.write_bytes(data)
    assert manifest.sha256_file(path) == hashlib.sha256(data).hexdigest()


def test_sha256_file_empty(tmp_path: Path) -> None:
    path = tmp_path / "empty"
    path.write_bytes(b"")
    assert manifest.sha256_file(path) == hashlib.sha256(b"").hexdigest()


# --- model_fingerprint ------------------------------------------------------


def test_fingerprint_plain_folder(fake_model_dir: Path) -> None:
    result = manifest.model_fingerprint(fake_model_dir)
    assert result["name"] == "all-MiniLM-L6-v2"
    assert result["snapshot"] is None
    assert set(result["files"]) == {
        "config.json",
        "modules.json",
        "model.safetensors",
        "tokenizer.json",
    }
    assert result["files"]["model.safetensors"] == hashlib.sha256(b"stub-weights").hexdigest()
    assert str(fake_model_dir) not in json.dumps(result)


def test_fingerprint_hugging_face_layout_with_symlinks(tmp_path: Path) -> None:
    cache = tmp_path / "models--sentence-transformers--all-MiniLM-L6-v2"
    blobs = cache / "blobs"
    snapshot = cache / "snapshots" / SNAPSHOT
    (snapshot / "1_Pooling").mkdir(parents=True)
    blobs.mkdir()
    (blobs / "blob1").write_bytes(b"weights")
    (blobs / "blob2").write_text("{}", encoding="utf-8")
    try:
        (snapshot / "model.safetensors").symlink_to(blobs / "blob1")
        (snapshot / "1_Pooling" / "config.json").symlink_to(blobs / "blob2")
    except OSError:
        pytest.skip("symbolic links are not available")
    (snapshot / "config.json").write_text("{}", encoding="utf-8")
    result = manifest.model_fingerprint(snapshot)
    assert result["name"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert result["snapshot"] == SNAPSHOT
    assert result["files"]["model.safetensors"] == hashlib.sha256(b"weights").hexdigest()
    assert "1_Pooling/config.json" in result["files"]
    assert str(tmp_path) not in json.dumps(result)


def test_fingerprint_ignores_unlisted_and_missing_files(tmp_path: Path) -> None:
    folder = tmp_path / "m"
    folder.mkdir()
    (folder / "README.md").write_text("x", encoding="utf-8")
    assert manifest.model_fingerprint(folder)["files"] == {}


# --- collect_environment ----------------------------------------------------


def test_collect_environment_keys() -> None:
    env = manifest.collect_environment(4)
    assert set(env) == {
        "python",
        "implementation",
        "platform",
        "libraries",
        "blas",
        "threads_requested",
    }
    assert env["threads_requested"] == 4
    assert env["platform"].startswith(sys.platform + "-")
    assert env["platform"] == env["platform"].lower()
    assert set(env["libraries"]) == {
        "numpy",
        "scikit-learn",
        "scipy",
        "sentence-transformers",
        "torch",
        "transformers",
        "tokenizers",
        "huggingface-hub",
        "jsonschema",
        "threadpoolctl",
    }
    assert all(isinstance(v, str) or v is None for v in env["libraries"].values())
    for entry in env["blas"]:
        assert set(entry) == {"api", "version", "num_threads"}


def test_collect_environment_missing_library_is_none(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.metadata as metadata

    def _raise(name: str) -> str:
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(metadata, "version", _raise)
    env = manifest.collect_environment(None)
    assert all(value is None for value in env["libraries"].values())
    assert env["threads_requested"] is None


def test_collect_environment_without_threadpoolctl(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "threadpoolctl", None)
    assert manifest.collect_environment(None)["blas"] == []


def test_blas_entries_omit_file_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    import threadpoolctl

    fake = [
        {
            "user_api": "blas",
            "internal_api": "openblas",
            "version": "0.3.29",
            "num_threads": 12,
            "filepath": "/secret/path/libopenblas.so",
        },
        {
            "user_api": "blas",
            "internal_api": "mkl",
            "version": "2024",
            "num_threads": 2,
            "filepath": "/secret/path/libmkl.so",
        },
    ]
    monkeypatch.setattr(threadpoolctl, "threadpool_info", lambda: fake)
    blas = manifest.collect_environment(None)["blas"]
    assert [entry["api"] for entry in blas] == ["mkl", "openblas"]
    assert "/secret" not in json.dumps(blas)


# --- tool_version -----------------------------------------------------------


def test_tool_version_matches_package() -> None:
    assert manifest.tool_version() == __version__


def test_tool_version_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib.metadata as metadata

    def _raise(name: str) -> str:
        raise metadata.PackageNotFoundError(name)

    monkeypatch.setattr(metadata, "version", _raise)
    assert manifest.tool_version() == __version__


# --- build_manifest ---------------------------------------------------------


def test_manifest_matches_schema(tmp_path: Path, fake_model_dir: Path) -> None:
    built = _build(tmp_path, fake_model_dir)
    errors = list(Draft202012Validator(MANIFEST_JSON_SCHEMA).iter_errors(built))
    assert errors == []
    assert built["tool"]["name"] == "mindrian-eureka"
    assert built["score_meaning"] == {
        "unusual_pairs": SCORE_MEANING["unusual_pairs"],
        "wording_and_meaning": SCORE_MEANING["wording_and_meaning"],
    }
    assert [item["path"] for item in built["outputs"]] == [
        "corpus/records.jsonl",
        "unusual-pairs.json",
    ]
    assert built["engine_notes"] == ["Note b.", "Note a."]


def test_schema_rejects_missing_engine_field(tmp_path: Path, fake_model_dir: Path) -> None:
    built = _build(tmp_path, fake_model_dir)
    del built["tool"]["engines"]["unusual_pairs"]["tie_break"]
    assert list(Draft202012Validator(MANIFEST_JSON_SCHEMA).iter_errors(built))


def test_manifest_has_no_path_or_timestamp(tmp_path: Path, fake_model_dir: Path) -> None:
    built = _build(tmp_path, fake_model_dir)
    text = json.dumps(built)
    assert str(tmp_path) not in text
    assert str(Path.home()) not in text
    assert not TIMESTAMP.search(text)


def test_manifest_is_reproducible(tmp_path: Path, fake_model_dir: Path) -> None:
    first = _build(tmp_path, fake_model_dir)
    second = _build(tmp_path, fake_model_dir)
    assert first == second
    assert canonical_json(first) == canonical_json(second)


def test_manifest_copies_inputs(tmp_path: Path, fake_model_dir: Path) -> None:
    sections = _engine_sections()
    outputs = [{"path": "a", "sha256": "0" * 64, "bytes": 1}]
    built = manifest.build_manifest(
        engines=sections["engines"],
        inputs={"files": ()},
        corpus={},
        settings=sections["settings"],
        seeds=sections["seeds"],
        model={},
        environment={},
        outputs=outputs,
        engine_notes=(),
    )
    outputs[0]["path"] = "changed"
    assert built["outputs"][0]["path"] == "a"
    assert built["inputs"]["files"] == []
    json.dumps(built)


# --- build_run_info ---------------------------------------------------------


def test_run_info() -> None:
    info = manifest.build_run_info(
        started_at="2026-10-24T10:00:00Z",
        finished_at="2026-10-24T10:01:00Z",
        duration_ms=60000,
        argv=["eureka", "run", "in", "--out", "out"],
        manifest_sha256="e" * 64,
    )
    assert info == {
        "schema_version": RUN_INFO_SCHEMA,
        "label": LABEL,
        "started_at": "2026-10-24T10:00:00Z",
        "finished_at": "2026-10-24T10:01:00Z",
        "duration_ms": 60000,
        "argv": ["eureka", "run", "in", "--out", "out"],
        "manifest_sha256": "e" * 64,
        "note": manifest.RUN_INFO_NOTE,
    }
    assert "kept in this file" in info["note"]


# --- Imports ----------------------------------------------------------------


def test_import_loads_no_numpy() -> None:
    code = (
        "import sys\n"
        f"sys.path.insert(0, {SRC_DIR!r})\n"
        "import mindrian_eureka.run.manifest\n"
        "assert 'numpy' not in sys.modules, 'numpy was loaded'\n"
        "assert 'torch' not in sys.modules, 'torch was loaded'\n"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


def test_source_has_no_em_dash_or_short_engine_codes() -> None:
    text = Path(manifest.__file__).read_text(encoding="utf-8")
    assert chr(0x2014) not in text
    assert not re.search(r"\b(R[S]|H[S]I)\b", text)
