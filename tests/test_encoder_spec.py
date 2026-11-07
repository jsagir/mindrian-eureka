"""Tests for the pure-data spec layer of the encoder seam (encoder_spec.py)."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

SRC_DIR = str(Path(__file__).resolve().parents[1] / "src")

IDENTITY_KEY_ORDER = [
    "profile",
    "model_id",
    "revision",
    "model_digest",
    "dimension",
    "dtype",
    "attention",
    "device",
    "query_prefix",
    "document_prefix",
    "normalize",
    "chunking",
    "batch_size",
    "max_seq_length",
]


def test_module_import_is_light() -> None:
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]);"
        "import mindrian_eureka.encoder_spec;"
        "bad = {'numpy', 'sklearn', 'scipy', 'torch', 'sentence_transformers', 'transformers'}"
        " & set(sys.modules);"
        "sys.exit(1 if bad else 0)"
    )
    done = subprocess.run([sys.executable, "-I", "-c", code, SRC_DIR], capture_output=True)
    assert done.returncode == 0, done.stderr.decode()


def test_profile_table() -> None:
    from mindrian_eureka import encoder_spec as es

    assert sorted(es.PROFILES) == ["cpu-default", "gpu-nemotron"]
    assert es.DEFAULT_PROFILE == "cpu-default"
    cpu = es.PROFILES["cpu-default"]
    assert cpu.model_id == "sentence-transformers/all-MiniLM-L6-v2"
    assert cpu.dimension == 384
    assert cpu.device == "cpu"
    assert cpu.dtype is None
    assert cpu.attention is None
    assert cpu.query_prefix == ""
    assert cpu.document_prefix == ""
    assert cpu.normalize is True
    assert cpu.chunking == "token-window-mean"
    assert cpu.batch_size == 16
    assert cpu.max_seq_length is None
    assert cpu.revision is None
    gpu = es.PROFILES["gpu-nemotron"]
    assert gpu.model_id == "nvidia/Nemotron-3-Embed-1B-BF16"
    assert gpu.dimension == 2048
    assert gpu.device == "cuda"
    assert gpu.dtype == "bfloat16"
    assert gpu.attention == "sdpa"
    assert gpu.query_prefix == "query: "
    assert gpu.document_prefix == "passage: "
    assert gpu.normalize is True
    assert gpu.batch_size == 16
    assert gpu.max_seq_length == 4096
    assert gpu.revision is None
    assert es.PROFILE_STATUS == {"cpu-default": "default", "gpu-nemotron": "spike"}
    assert es.PROFILE_EXTRA == {"cpu-default": "modern-encoder", "gpu-nemotron": "gpu-encoder"}


def test_identity_has_14_keys_and_no_path() -> None:
    from mindrian_eureka import encoder_spec as es

    for spec in es.PROFILES.values():
        identity = spec.identity()
        assert list(identity) == IDENTITY_KEY_ORDER
        assert list(es.IDENTITY_KEYS) == IDENTITY_KEY_ORDER
        for value in identity.values():
            assert value is None or isinstance(value, (str, int, bool))
            if isinstance(value, str):
                assert not value.startswith("/")
                assert "\\" not in value


def test_fingerprint_is_stable_and_starts_with_sha256() -> None:
    from mindrian_eureka import encoder_spec as es

    a = es.profile_spec("cpu-default")
    b = es.profile_spec("cpu-default")
    assert a.fingerprint() == b.fingerprint()
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", a.fingerprint())
    text = json.dumps(a.identity(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    expected = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert a.fingerprint() == expected
    assert es.profile_spec("gpu-nemotron").fingerprint() != a.fingerprint()


CHANGES: dict[str, Any] = {
    "profile": "custom",
    "model_id": "other/model",
    "revision": "a" * 40,
    "model_digest": "b" * 64,
    "dimension": 385,
    "dtype": "float16",
    "attention": "eager",
    "device": "cuda:1",
    "query_prefix": "q: ",
    "document_prefix": "d: ",
    "normalize": False,
    "chunking": "caller",
    "batch_size": 8,
    "max_seq_length": 256,
}


@pytest.mark.parametrize("key", IDENTITY_KEY_ORDER)
def test_every_field_changes_the_fingerprint(key: str) -> None:
    from mindrian_eureka import encoder_spec as es

    base = es.profile_spec("cpu-default")
    changed = dataclasses.replace(base, **{key: CHANGES[key]})
    assert changed.fingerprint() != base.fingerprint()


def test_determinism_class() -> None:
    from mindrian_eureka import encoder_spec as es

    assert es.DETERMINISM_CPU_EXACT == "cpu-exact"
    assert es.DETERMINISM_GPU_APPROX == "gpu-approx"
    cpu = es.profile_spec("cpu-default")
    assert cpu.determinism_class() == "cpu-exact"
    assert es.profile_spec("gpu-nemotron").determinism_class() == "gpu-approx"
    assert dataclasses.replace(cpu, dtype="float32").determinism_class() == "cpu-exact"
    assert dataclasses.replace(cpu, dtype="bfloat16").determinism_class() == "gpu-approx"
    assert dataclasses.replace(cpu, attention="sdpa").determinism_class() == "gpu-approx"
    assert (
        dataclasses.replace(cpu, device="cuda", dtype="float32").determinism_class()
        == "gpu-approx"
    )


@pytest.mark.parametrize(
    ("change", "field"),
    [
        ({"device": "tpu"}, "device"),
        ({"device": "cuda:x"}, "device"),
        ({"dtype": "int8"}, "dtype"),
        ({"attention": "fast"}, "attention"),
        ({"chunking": "words"}, "chunking"),
        ({"batch_size": 0}, "batch_size"),
        ({"dimension": 0}, "dimension"),
        ({"max_seq_length": 4}, "max_seq_length"),
        ({"query_prefix": 3}, "query_prefix"),
        ({"document_prefix": 3}, "document_prefix"),
        ({"normalize": "yes"}, "normalize"),
    ],
)
def test_validation(change: dict[str, Any], field: str) -> None:
    from mindrian_eureka import encoder_spec as es

    base = es.profile_spec("cpu-default")
    with pytest.raises(ValueError, match=field):
        dataclasses.replace(base, **change)


@pytest.mark.parametrize("device", ["cpu", "cuda", "cuda:0", "mps"])
def test_valid_devices(device: str) -> None:
    from mindrian_eureka import encoder_spec as es

    base = es.profile_spec("cpu-default")
    assert dataclasses.replace(base, device=device).device == device


def test_profile_spec_and_custom_spec() -> None:
    from mindrian_eureka import encoder_spec as es

    pinned = es.profile_spec("cpu-default", revision="a" * 40, model_digest="b" * 64)
    base = es.PROFILES["cpu-default"]
    assert pinned == dataclasses.replace(base, revision="a" * 40, model_digest="b" * 64)
    with pytest.raises(ValueError) as caught:
        es.profile_spec("nope")
    assert "cpu-default" in str(caught.value)
    assert "gpu-nemotron" in str(caught.value)
    custom = es.custom_spec("/models/x", "c" * 40)
    assert custom.profile == "custom"
    assert custom.model_id == "/models/x"
    assert custom.dimension is None
    assert custom.revision == "c" * 40
    for field in ("dtype", "attention", "device", "query_prefix", "document_prefix",
                  "normalize", "chunking", "batch_size", "max_seq_length"):
        assert getattr(custom, field) == getattr(base, field)
    plain = es.custom_spec("/models/x")
    assert plain.is_legacy_equivalent("/models/x", None)
    assert not dataclasses.replace(plain, device="cuda").is_legacy_equivalent("/models/x", None)


def test_for_caller_chunks() -> None:
    from mindrian_eureka import encoder_spec as es

    gpu = es.profile_spec("gpu-nemotron")
    caller = gpu.for_caller_chunks()
    assert caller.chunking == "caller"
    assert caller.batch_size is None
    assert gpu.chunking == "token-window-mean"
    assert gpu.batch_size == 16
    assert gpu.prefix_for("document") == "passage: "
    assert gpu.prefix_for("query") == "query: "
    with pytest.raises(ValueError):
        gpu.prefix_for("other")


def test_encoder_block_shape() -> None:
    from mindrian_eureka import encoder_spec as es

    cpu = es.profile_spec("cpu-default")
    gpu = es.profile_spec("gpu-nemotron")
    block = es.encoder_block(cpu, cpu.for_caller_chunks())
    assert set(block) == {"schema", "profile", "determinism_class", "unusual_pairs",
                          "wording_and_meaning"}
    assert block["schema"] == "eureka.encoder-block.v1"
    assert block["profile"] == "cpu-default"
    assert block["determinism_class"] == "cpu-exact"
    for key in ("unusual_pairs", "wording_and_meaning"):
        assert set(block[key]) == {"fingerprint", "identity"}
    assert block["unusual_pairs"]["fingerprint"] == cpu.fingerprint()
    mixed = es.encoder_block(cpu, gpu)
    assert mixed["determinism_class"] == "gpu-approx"
    assert mixed["profile"] == "cpu-default"
    text = json.dumps(mixed)
    assert json.loads(text) == mixed

    def has_float(value: Any) -> bool:
        if isinstance(value, float):
            return True
        if isinstance(value, dict):
            return any(has_float(v) for v in value.values())
        if isinstance(value, list):
            return any(has_float(v) for v in value)
        return False

    assert not has_float(mixed)


def test_result_label_matches_the_run_contract() -> None:
    from mindrian_eureka import encoder_spec as es
    from mindrian_eureka.run.contracts import LABEL

    assert es.RESULT_LABEL == LABEL == "candidate, not verified"


def test_extra_names() -> None:
    from mindrian_eureka import encoder_spec as es

    assert es.GPU_EXTRA == "gpu-encoder"
    assert es.MODERN_EXTRA == "modern-encoder"
