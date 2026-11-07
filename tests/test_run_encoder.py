"""Tests for the encoder profile run of `eureka run` (pipeline, engines, manifest, flag)."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import types
from collections.abc import Callable, Iterator
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from conftest import InputSet
from mindrian_eureka.run import engines, pipeline
from mindrian_eureka.run.contracts import RunError, UsageError
from test_run_engines import OFFLINE_NAMES, _restorable_env, make_records
from test_run_pipeline import HASHED_FILES, read, run

RECORDED_PARAMS_HASH = "bea4c100c2013300"
GPU_MODEL_ID = "nvidia/Nemotron-3-Embed-1B-BF16"
SNAPSHOT = "0123456789abcdef0123456789abcdef01234567"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


@pytest.fixture
def env(isolated_env: Path, stub_encoders: None) -> Path:
    return isolated_env


def _strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _manifest(out: Path) -> dict[str, Any]:
    return json.loads(read(out, "manifest.json"))  # type: ignore[no-any-return]


def _listed_hashes(out: Path) -> dict[str, str]:
    manifest = _manifest(out)
    return {item["path"]: item["sha256"] for item in manifest["outputs"]}


def _use_stub_width_for_gpu(monkeypatch: pytest.MonkeyPatch) -> None:
    from hashing_stub import EMBED_DIM
    from mindrian_eureka.encoder_spec import PROFILES

    gpu = replace(PROFILES["gpu-nemotron"], dimension=EMBED_DIM)
    monkeypatch.setitem(PROFILES, "gpu-nemotron", gpu)


# --- The manifest block of the default run ----------------------------------


def test_default_manifest_has_the_encoder_block(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    out = tmp_path / "out"
    run(tmp_inputs("markdown"), out, fake_model_dir)
    block = _manifest(out)["encoder"]
    assert set(block) == {
        "schema",
        "profile",
        "determinism_class",
        "unusual_pairs",
        "wording_and_meaning",
    }
    assert block["schema"] == "eureka.encoder-block.v1"
    assert block["profile"] == "cpu-default"
    assert block["determinism_class"] == "cpu-exact"
    for key in ("unusual_pairs", "wording_and_meaning"):
        assert set(block[key]) == {"fingerprint", "identity"}
    unusual = block["unusual_pairs"]["identity"]
    wording = block["wording_and_meaning"]["identity"]
    assert unusual["model_id"] == "sentence-transformers/all-MiniLM-L6-v2"
    assert unusual["chunking"] == "token-window-mean"
    assert unusual["batch_size"] == 16
    assert unusual["device"] == "cpu"
    assert wording["chunking"] == "caller"
    assert wording["batch_size"] is None
    assert unusual["revision"] is None
    assert HEX64.match(unusual["model_digest"])
    assert HEX64.match(wording["model_digest"])
    assert block["unusual_pairs"]["fingerprint"] != block["wording_and_meaning"]["fingerprint"]
    for text in _strings(block):
        assert not text.startswith("/"), text
    assert "gpu" not in block


def test_default_pair_files_have_no_new_key(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    out = tmp_path / "out"
    run(tmp_inputs("markdown"), out, fake_model_dir)
    for name in ("unusual-pairs.json", "wording-and-meaning-pairs.json"):
        assert set(json.loads(read(out, name))) == {
            "counts",
            "engine",
            "label",
            "notes",
            "pairs",
            "schema_version",
            "score_meaning",
            "settings",
        }


def test_explicit_default_profile_equals_the_implicit_one(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    inputs = tmp_inputs("markdown")
    implicit, explicit = tmp_path / "implicit", tmp_path / "explicit"
    run(inputs, implicit, fake_model_dir)
    run(inputs, explicit, fake_model_dir, encoder_profile="cpu-default")
    first, second = _listed_hashes(implicit), _listed_hashes(explicit)
    assert set(first) == set(HASHED_FILES)
    assert first == second
    one, two = _manifest(implicit), _manifest(explicit)
    for key in ("settings", "seeds", "tool", "encoder"):
        assert one[key] == two[key], key


def test_settings_of_the_default_profile_are_unchanged(
    env: Path, fake_model_dir: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    out = tmp_path / "out"
    run(tmp_inputs("markdown"), out, fake_model_dir)
    manifest = _manifest(out)
    assert manifest["settings"]["wording_and_meaning"]["model_name"] == "all-MiniLM-L6-v2"
    wording = manifest["tool"]["engines"]["wording_and_meaning"]
    assert wording["params_hash"] == RECORDED_PARAMS_HASH


# --- Profile validation -----------------------------------------------------


def test_unknown_profile_is_a_usage_error(
    env: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    out = tmp_path / "out"
    with pytest.raises(UsageError) as caught:
        run(
            tmp_inputs("markdown"),
            out,
            tmp_path / "no-such-model-folder",
            encoder_profile="nope",
        )
    text = f"{caught.value.message} {caught.value.fix}"
    assert "cpu-default" in text
    assert "gpu-nemotron" in text
    assert not out.exists()


def test_named_profile_needs_an_explicit_model_path(
    env: Path, tmp_inputs: Callable[..., InputSet], tmp_path: Path
) -> None:
    inputs = tmp_inputs("markdown")
    out = tmp_path / "out"
    with pytest.raises(UsageError) as caught:
        run(inputs, out, None, encoder_profile="gpu-nemotron")  # type: ignore[arg-type]
    assert "--model-path" in str(caught.value.fix)
    assert GPU_MODEL_ID in f"{caught.value.message} {caught.value.fix}"
    assert not out.exists()
    summary = run(
        inputs,
        tmp_path / "dry",
        None,  # type: ignore[arg-type]
        encoder_profile="gpu-nemotron",
        dry_run=True,
    )
    assert summary.dry_run is True
    assert summary.records_used > 0


# --- A named profile run with stubs -----------------------------------------


def test_named_profile_run_with_stubs(
    env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_stub_width_for_gpu(monkeypatch)
    inputs = tmp_inputs("markdown")
    out = tmp_path / "out"
    summary = run(inputs, out, fake_model_dir, encoder_profile="gpu-nemotron")
    manifest = _manifest(out)
    block = manifest["encoder"]
    assert block["profile"] == "gpu-nemotron"
    assert block["determinism_class"] == "gpu-approx"
    assert block["unusual_pairs"]["identity"]["device"] == "cuda"
    assert block["unusual_pairs"]["identity"]["dtype"] == "bfloat16"
    for key, name in (
        ("unusual_pairs", "unusual-pairs.json"),
        ("wording_and_meaning", "wording-and-meaning-pairs.json"),
    ):
        document = json.loads(read(out, name))
        assert document["encoder_fingerprint"] == block[key]["fingerprint"]
    assert manifest["settings"]["wording_and_meaning"]["model_name"] == GPU_MODEL_ID
    wording = manifest["tool"]["engines"]["wording_and_meaning"]
    assert wording["params_hash"] != RECORDED_PARAMS_HASH
    cache_files = {item.name for item in (env / "cache").iterdir()}
    assert "embeddings-gpu-nemotron.sqlite3" in cache_files
    assert "embeddings.sqlite3" not in cache_files
    flagged = [
        text for text in summary.warnings if "gpu-approx" in text and "overlap" in text
    ]
    assert len(flagged) == 1
    default_out = tmp_path / "default"
    default_summary = run(inputs, default_out, fake_model_dir)
    assert not [text for text in default_summary.warnings if "gpu-approx" in text]
    assert "embeddings.sqlite3" in {item.name for item in (env / "cache").iterdir()}


def test_named_profile_runs_twice_with_equal_outputs(
    env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_stub_width_for_gpu(monkeypatch)
    inputs = tmp_inputs("markdown")
    first, second = tmp_path / "first", tmp_path / "second"
    run(inputs, first, fake_model_dir, encoder_profile="gpu-nemotron")
    run(inputs, second, fake_model_dir, encoder_profile="gpu-nemotron")
    assert _listed_hashes(first) == _listed_hashes(second)
    assert set(_listed_hashes(first)) == set(HASHED_FILES)


# --- Identity from the model folder -----------------------------------------


def _hub_layout(tmp_path: Path, source: Path) -> Path:
    snapshot = (
        tmp_path / "models--sentence-transformers--all-MiniLM-L6-v2" / "snapshots" / SNAPSHOT
    )
    snapshot.mkdir(parents=True)
    for item in source.iterdir():
        (snapshot / item.name).write_bytes(item.read_bytes())
    return snapshot


def test_snapshot_and_digest_come_from_the_model_folder(
    env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _hub_layout(tmp_path, fake_model_dir)
    misses: list[int] = []
    real_unusual = engines.run_unusual_pairs

    def watch(records: Any, **kwargs: Any) -> Any:
        outcome = real_unusual(records, **kwargs)
        cache = outcome.result["method_details"]["semantic_signal"]["cache"]
        misses.append(int(cache["misses"]))
        return outcome

    monkeypatch.setattr(engines, "run_unusual_pairs", watch)
    inputs = tmp_inputs("markdown")
    first = tmp_path / "first"
    summary = run(inputs, first, model)
    identity = _manifest(first)["encoder"]["unusual_pairs"]["identity"]
    assert identity["revision"] == SNAPSHOT
    assert HEX64.match(identity["model_digest"])
    assert misses == [summary.records_used]
    run(inputs, tmp_path / "again", model)
    assert misses[-1] == 0
    weights = model / "model.safetensors"
    weights.write_bytes(weights.read_bytes() + b"x")
    changed = tmp_path / "changed"
    run(inputs, changed, model)
    other = _manifest(changed)["encoder"]["unusual_pairs"]["identity"]
    assert other["model_digest"] != identity["model_digest"]
    assert misses[-1] == summary.records_used


def test_digest_is_missing_and_said_so_when_no_model_file_can_be_hashed(
    env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pipeline,
        "describe_model",
        lambda folder: {"name": "stub", "snapshot": None, "files": {}},
    )
    out = tmp_path / "out"
    run(tmp_inputs("markdown"), out, fake_model_dir)
    block = _manifest(out)["encoder"]
    assert block["unusual_pairs"]["identity"]["model_digest"] is None
    assert "not pinned" in block["weights_note"]


def test_gpu_details_only_for_cuda_profiles(
    env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _use_stub_width_for_gpu(monkeypatch)
    calls: list[int] = []

    def details() -> dict[str, str]:
        calls.append(1)
        return {"name": "Test GPU", "cuda": "12.0"}

    monkeypatch.setattr(pipeline, "_gpu_details", details)
    inputs = tmp_inputs("markdown")
    default_out = tmp_path / "default"
    run(inputs, default_out, fake_model_dir)
    assert "gpu" not in _manifest(default_out)["encoder"]
    assert calls == []
    gpu_out = tmp_path / "gpu"
    run(inputs, gpu_out, fake_model_dir, encoder_profile="gpu-nemotron")
    assert _manifest(gpu_out)["encoder"]["gpu"] == {"name": "Test GPU", "cuda": "12.0"}
    assert calls == [1]


# --- Engine seam ------------------------------------------------------------


def test_wording_params_take_a_model_name(env: Path) -> None:
    assert engines.wording_params(200)["model"] == "all-MiniLM-L6-v2"
    assert engines.wording_params_hash(200) == RECORDED_PARAMS_HASH
    other = engines.wording_params(200, model_name="other/model")
    assert other["model"] == "other/model"
    assert engines.wording_params_hash(200, model_name="other/model") != RECORDED_PARAMS_HASH


def _fake_sentence_transformers(
    monkeypatch: pytest.MonkeyPatch, width: int
) -> dict[str, list[Any]]:
    import numpy as np

    seen: dict[str, list[Any]] = {"init": [], "encode": []}

    class FakeModel:
        max_seq_length = 128

        def __init__(self, path: str, **kwargs: Any) -> None:
            seen["init"].append((path, kwargs))

        def get_embedding_dimension(self) -> int:
            return width

        def encode(self, items: list[str], **kwargs: Any) -> Any:
            seen["encode"].append((list(items), kwargs))
            return np.arange(len(items) * width, dtype=np.float32).reshape(len(items), width)

    module = types.ModuleType("sentence_transformers")
    module.SentenceTransformer = FakeModel  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)
    return seen


def test_load_local_encode_with_a_fake_model(
    fake_model_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import numpy as np
    from mindrian_eureka.encoder_spec import profile_spec

    _restorable_env(monkeypatch, OFFLINE_NAMES)
    seen = _fake_sentence_transformers(monkeypatch, 8)
    encode = engines.load_local_encode(fake_model_dir)
    items = ["alpha", "beta"]
    result = encode(items)
    expected = np.arange(16, dtype=np.float32).reshape(2, 8)
    assert result.dtype == np.float32
    assert np.array_equal(result, expected)
    assert seen["encode"] == [(["alpha", "beta"], {"show_progress_bar": False})]
    assert "trust_remote_code" not in seen["init"][0][1]

    spec = replace(
        profile_spec("cpu-default").for_caller_chunks(), dimension=8, document_prefix="p: "
    )
    prefixed = engines.load_local_encode(fake_model_dir, spec)
    prefixed(items)
    assert seen["encode"][-1] == (["p: alpha", "p: beta"], {"show_progress_bar": False})
    assert all("trust_remote_code" not in kwargs for _path, kwargs in seen["init"])

    wrong = replace(spec, dimension=9)
    with pytest.raises(RunError) as caught:
        engines.load_local_encode(fake_model_dir, wrong)
    assert caught.value.fix == engines.MODEL_FIX


def test_run_unusual_pairs_passes_the_spec_only_when_given(
    monkeypatch: pytest.MonkeyPatch, fake_model_dir: Path, tmp_path: Path
) -> None:
    from mindrian_eureka.encoder_spec import profile_spec
    from mindrian_eureka.opportunity_pairs import runner

    _restorable_env(monkeypatch, OFFLINE_NAMES)
    seen: list[dict[str, Any]] = []

    def fake_run(document: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        seen.append(kwargs)
        return {"status": "completed", "outputs": []}

    monkeypatch.setattr(runner, "validate_document", lambda document, **kwargs: None)
    monkeypatch.setattr(runner, "run_document", fake_run)
    records = make_records(5)
    common: dict[str, Any] = {
        "model_dir": fake_model_dir,
        "top_k": 10,
        "max_artifacts": 4000,
        "cache_path": tmp_path / "cache.sqlite",
    }
    engines.run_unusual_pairs(records, **common)
    spec = profile_spec("cpu-default")
    engines.run_unusual_pairs(records, encoder_spec=spec, **common)
    assert "encoder_spec" not in seen[0]
    assert seen[1]["encoder_spec"] == spec
    assert seen[0]["model_path"] == str(fake_model_dir)
    assert seen[1]["model_path"] == str(fake_model_dir)


# --- The flag and the request field -----------------------------------------


def test_run_flag_and_request_field(
    env: Path,
    fake_model_dir: Path,
    tmp_inputs: Callable[..., InputSet],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from mindrian_eureka.cli import main
    from mindrian_eureka.run.command import build_run_request, register_commands

    assert pipeline.RunRequest(input_dir=tmp_path, out_dir=tmp_path).encoder_profile == (
        "cpu-default"
    )
    inputs = tmp_inputs("markdown")
    out = tmp_path / "out"
    code = main(
        [
            "run",
            str(inputs.folder),
            "--out",
            str(out),
            "--model-path",
            str(fake_model_dir),
            "--encoder-profile",
            "nope",
        ]
    )
    assert code == 2
    assert not out.exists()
    capsys.readouterr()
    with pytest.raises(SystemExit):
        main(["run", "--help"])
    assert "--encoder-profile" in capsys.readouterr().out

    parser = argparse.ArgumentParser(prog="eureka")
    register_commands(parser.add_subparsers(dest="command", required=True))
    args = parser.parse_args(
        ["run", str(inputs.folder), "--encoder-profile", "gpu-nemotron"]
    )
    assert build_run_request(args).encoder_profile == "gpu-nemotron"
    default_args = parser.parse_args(["run", str(inputs.folder)])
    assert build_run_request(default_args).encoder_profile == "cpu-default"


def test_cache_digest_helper_is_stable() -> None:
    files = {"b": "2", "a": "1"}
    expected = hashlib.sha256(
        json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert pipeline._model_digest(files) == expected
    assert pipeline._model_digest({}) is None
