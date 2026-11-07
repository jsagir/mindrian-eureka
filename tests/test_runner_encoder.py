"""The unusual-pairs runner builds its encoder through the seam and keys the cache by setup."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from hashing_stub import hashing_encode
from mindrian_eureka.opportunity_pairs import runner
from mindrian_eureka.opportunity_pairs.algorithm import Artifact
from mindrian_eureka.opportunity_pairs.cache import EmbeddingCache

ENCODER = "sentence-transformers"
RS_METHOD = "sentence-transformer-chunk-mean-v1"
BERT_METHOD = "bert-cls-510-plus-specials-v1"
LABEL = "candidate, not verified"
TEXTS = {
    "a1": "battery storage grid energy resilience",
    "a2": "clinical imaging diagnostic medical sensors",
    "a3": "agricultural irrigation water crop yield",
    "a4": "electrochemical battery storage power system",
    "a5": "medical imaging sensors diagnostic equipment",
    "a6": "battery storage hospital sensors power outage",
}


def _document() -> dict[str, Any]:
    return {
        "mode": "local",
        "scoring": "legacy",
        "objective": "runner seam test",
        "artifacts": [
            {"id": key, "title": key, "text": text, "source_ref": f"ref://{key}"}
            for key, text in TEXTS.items()
        ],
    }


def _model_texts() -> list[str]:
    return [
        Artifact(id=key, title=key, text=text, source_ref=f"ref://{key}").model_text
        for key, text in TEXTS.items()
    ]


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> type:
    """Replace the runner encoder with a recording stub. The stub width is a class attribute."""

    class Recorder:
        calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        width = 64

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            type(self).calls.append((args, kwargs))
            self.spec = kwargs.get("spec")

        def encode(self, texts: Any, cancel_check: Any = None) -> np.ndarray:
            base = hashing_encode(list(texts))
            width = type(self).width
            if width < base.shape[1]:
                # A narrow slice of a hashed vector can be all zero, so lift every row.
                return base[:, :width] + np.arange(1, width + 1)
            if width == base.shape[1]:
                return base
            pad = np.zeros((base.shape[0], width - base.shape[1]))
            return np.concatenate([base, pad], axis=1)

    monkeypatch.setattr(runner, "SentenceTransformerEncoder", Recorder)
    return Recorder


def _spec(**changes: Any) -> Any:
    from mindrian_eureka.encoder_spec import profile_spec

    return replace(profile_spec("cpu-default"), dimension=64, **changes)


def _run(tmp_path: Path, name: str = "cache.sqlite3", **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("model_path", "stub-model")
    return runner.run_document(
        _document(), encoder_name=ENCODER, top_k=20, cache_path=tmp_path / name, **kwargs
    )


def _cache_meta(result: dict[str, Any]) -> dict[str, Any]:
    meta: dict[str, Any] = result["method_details"]["semantic_signal"]["cache"]
    return meta


def test_legacy_call_uses_the_legacy_constructor_call(
    tmp_path: Path, recorder: type
) -> None:
    _run(tmp_path, model_path="stub-model")
    assert len(recorder.calls) == 1  # type: ignore[attr-defined]
    args, kwargs = recorder.calls[0]  # type: ignore[attr-defined]
    assert args == ("stub-model",)
    assert kwargs == {"allow_download": False, "revision": None}
    assert "spec" not in kwargs


def test_spec_call_passes_the_spec(tmp_path: Path, recorder: type) -> None:
    from mindrian_eureka.encoder_spec import profile_spec

    spec = profile_spec("cpu-default")
    recorder.width = 384  # type: ignore[attr-defined]
    _run(tmp_path, model_path="/stub/folder", encoder_spec=spec)
    args, kwargs = recorder.calls[0]  # type: ignore[attr-defined]
    assert args == ("/stub/folder",)
    assert kwargs["spec"] == spec


def test_ranking_is_identical_with_and_without_a_spec(
    tmp_path: Path, recorder: type
) -> None:
    plain = _run(tmp_path, "plain.sqlite3")
    with_spec = _run(tmp_path, "spec.sqlite3", encoder_spec=_spec())
    assert plain["outputs"], "the fixture must give ranked pairs"
    assert [o["payload"] for o in plain["outputs"]] == [o["payload"] for o in with_spec["outputs"]]
    assert [o["id"] for o in plain["outputs"]] == [o["id"] for o in with_spec["outputs"]]


def test_outputs_carry_label_and_fingerprint(tmp_path: Path, recorder: type) -> None:
    from mindrian_eureka.encoder_spec import custom_spec

    legacy = _run(tmp_path, "legacy.sqlite3")
    spec = _spec()
    modern = _run(tmp_path, "modern.sqlite3", encoder_spec=spec)
    legacy_spec = custom_spec("stub-model")
    for result, expected in ((legacy, legacy_spec), (modern, spec)):
        assert result["outputs"]
        for output in result["outputs"]:
            assert output["label"] == LABEL
            assert output["encoder_fingerprint"] == expected.fingerprint()
        block = result["method_details"]["encoder"]
        assert block["name"] == ENCODER
        assert block["model"] == "stub-model"
        assert block["revision"] is None
        assert block["profile"] == expected.profile
        assert block["fingerprint"] == expected.fingerprint()
        assert block["determinism_class"] == "cpu-exact"
        assert block["identity"] == expected.identity()
    assert legacy_spec.fingerprint() != spec.fingerprint()


def test_cache_separates_encoder_setups(tmp_path: Path, recorder: type) -> None:
    count = len(TEXTS)
    spec_a = _spec()
    spec_b = replace(spec_a, document_prefix="p: ")
    first = _run(tmp_path, encoder_spec=spec_a)
    assert _cache_meta(first)["misses"] == count
    second = _run(tmp_path, encoder_spec=spec_a)
    assert _cache_meta(second)["hits"] == count
    assert len(recorder.calls) == 1  # type: ignore[attr-defined]
    other = _run(tmp_path, encoder_spec=spec_b)
    assert _cache_meta(other)["misses"] == count
    assert _cache_meta(other)["hits"] == 0
    assert len(recorder.calls) == 2  # type: ignore[attr-defined]
    again = _run(tmp_path, encoder_spec=spec_a)
    assert _cache_meta(again)["hits"] == count


def test_declared_width_is_enforced(tmp_path: Path, recorder: type) -> None:
    spec = replace(_spec(), dimension=5)
    recorder.width = 3  # type: ignore[attr-defined]
    with pytest.raises(RuntimeError) as caught:
        _run(tmp_path, encoder_spec=spec)
    assert "3" in str(caught.value) and "5" in str(caught.value)
    assert EmbeddingCache(tmp_path / "cache.sqlite3").stats()["entries"] == 0

    cache = EmbeddingCache(tmp_path / "cache.sqlite3")
    for text in _model_texts():
        key = EmbeddingCache.key(
            text, encoder=ENCODER, model=spec.model_id, revision=spec.revision,
            method_version=RS_METHOD, identity=spec.identity(),
        )
        cache.put(key, np.ones((1, 3)))
    recorder.width = 5  # type: ignore[attr-defined]
    result = _run(tmp_path, encoder_spec=spec)
    meta = _cache_meta(result)
    assert meta["dimension_rejected"] == len(TEXTS)
    assert meta["hits"] == 0
    assert meta["misses"] == len(TEXTS)


def test_non_exact_setup_adds_one_warning(tmp_path: Path, recorder: type) -> None:
    from mindrian_eureka.encoder_spec import profile_spec

    gpu = _run(tmp_path, "gpu.sqlite3", encoder_spec=_spec(device="cuda"))
    noted = [w for w in gpu["warnings"] if "gpu-approx" in w]
    assert len(noted) == 1
    assert "overlap" in noted[0]
    legacy = _run(tmp_path, "legacy.sqlite3")
    assert not [w for w in legacy["warnings"] if "gpu-approx" in w]
    recorder.width = 384  # type: ignore[attr-defined]
    cpu = _run(tmp_path, "cpu.sqlite3", encoder_spec=profile_spec("cpu-default"))
    assert not [w for w in cpu["warnings"] if "gpu-approx" in w]


def test_encoder_spec_with_reference_bert_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mindrian_eureka.encoder_spec import custom_spec, profile_spec

    class StubBert:
        def __init__(self, model_path: str, **kwargs: Any) -> None:
            self.model_path = model_path

        def encode_segments(self, texts: Any, cancel_check: Any = None) -> list[np.ndarray]:
            out = []
            for text in texts:
                seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
                out.append(np.random.default_rng(seed).normal(size=(2, 4)))
            return out

    monkeypatch.setattr(runner, "ReferenceBertEncoder", StubBert)
    cache_path = tmp_path / "bert.sqlite3"
    with pytest.raises(ValueError):
        runner.run_document(
            _document(), encoder_name="reference-bert", model_path="bert-stub",
            top_k=20, cache_path=cache_path, encoder_spec=profile_spec("cpu-default"),
        )
    results = [
        runner.run_document(
            _document(), encoder_name="reference-bert", model_path="bert-stub",
            top_k=20, cache_path=cache_path, encoder_spec=None,
        )
        for _ in range(2)
    ]
    assert _cache_meta(results[0])["misses"] == len(TEXTS)
    assert _cache_meta(results[1])["hits"] == len(TEXTS)
    identity = custom_spec("bert-stub").identity()
    cache = EmbeddingCache(cache_path)
    for text in _model_texts():
        key = EmbeddingCache.key(
            text, encoder="reference-bert", model="bert-stub", revision=None,
            method_version=BERT_METHOD, identity=identity,
        )
        assert cache.get(key) is not None


def test_download_rule_reads_the_spec_revision(tmp_path: Path, recorder: type) -> None:
    from mindrian_eureka.encoder_spec import profile_spec

    pinned = replace(profile_spec("cpu-default", revision="a" * 40), dimension=64)
    _run(tmp_path, "pinned.sqlite3", allow_model_download=True, encoder_spec=pinned)
    _, kwargs = recorder.calls[0]  # type: ignore[attr-defined]
    assert kwargs["allow_download"] is True
    assert kwargs["revision"] == "a" * 40

    with pytest.raises(ValueError) as caught:
        _run(
            tmp_path, "open.sqlite3", allow_model_download=True,
            encoder_spec=profile_spec("cpu-default"),
        )
    assert (
        "Model downloads require a 40-character immutable commit hash via --model-revision"
        in str(caught.value)
    )

    with pytest.raises(ValueError):
        _run(tmp_path, "conflict.sqlite3", model_revision="b" * 40, encoder_spec=pinned)


def test_cache_and_spec_modules_agree() -> None:
    from mindrian_eureka import encoder_spec
    from mindrian_eureka.opportunity_pairs import cache
    from mindrian_eureka.run import contracts

    assert cache.BASE_PROFILE == encoder_spec.DEFAULT_PROFILE
    assert set(encoder_spec.IDENTITY_KEYS) == {
        "profile", "model_id", "revision", "model_digest", "dimension", "dtype", "attention",
        "device", "query_prefix", "document_prefix", "normalize", "chunking", "batch_size",
        "max_seq_length",
    }
    assert encoder_spec.RESULT_LABEL == contracts.LABEL
