"""Tests for the encoder factory and the spec-aware SentenceTransformerEncoder.

A fake `sentence_transformers` module stands in for the real library, so most tests need no
model files. One test uses the real MiniLM model and is skipped when it is not on disk.
"""

from __future__ import annotations

import dataclasses
import hashlib
import re
import sys
import types
from collections.abc import Callable, Iterator, Sequence
from typing import Any

import numpy as np
import pytest
from hashing_stub import HashingEncoder

TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]")


class FakeTokenizer:
    """One token for each word or punctuation mark. Decode joins tokens by one space."""

    def __init__(self) -> None:
        self._ids: dict[str, int] = {}
        self._words: list[str] = []

    def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
        out: list[int] = []
        for word in TOKEN_PATTERN.findall(text):
            if word not in self._ids:
                self._ids[word] = len(self._words)
                self._words.append(word)
            out.append(self._ids[word])
        return out

    def decode(self, ids: Sequence[int], skip_special_tokens: bool = True) -> str:
        return " ".join(self._words[i] for i in ids)


class FakeState:
    """What the fake library recorded."""

    def __init__(self, width: int) -> None:
        self.width = width
        self.init_calls: list[dict[str, Any]] = []
        self.init_args: list[tuple[Any, ...]] = []
        self.encode_calls: list[tuple[list[str], dict[str, Any]]] = []
        self.models: list[Any] = []
        self.max_seq_length = 12


def _make_fake_class(state: FakeState) -> type:
    class FakeSentenceTransformer:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            state.init_args.append(args)
            state.init_calls.append(dict(kwargs))
            self.tokenizer = FakeTokenizer()
            self.max_seq_length = state.max_seq_length
            state.models.append(self)

        def get_sentence_embedding_dimension(self) -> int:
            return state.width

        def encode(self, items: Sequence[str], **kwargs: Any) -> np.ndarray:
            batch = list(items)
            state.encode_calls.append((batch, dict(kwargs)))
            rows = []
            for text in batch:
                seed = hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest()
                rng = np.random.default_rng(int.from_bytes(seed, "big"))
                rows.append(rng.standard_normal(state.width).astype(np.float32))
            matrix = np.stack(rows) if rows else np.zeros((0, state.width), dtype=np.float32)
            if kwargs.get("normalize_embeddings"):
                norms = np.linalg.norm(matrix, axis=1, keepdims=True)
                matrix = matrix / np.where(norms == 0, 1.0, norms)
            return matrix

    return FakeSentenceTransformer


@pytest.fixture
def fake_st(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeState]:
    """Install the fake library. After the test, assert no call set trust_remote_code."""
    state = FakeState(width=384)
    module = types.ModuleType("sentence_transformers")
    module.SentenceTransformer = _make_fake_class(state)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)
    yield state
    for call in state.init_calls:
        assert "trust_remote_code" not in call


@pytest.fixture
def fake_torch(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    module = types.ModuleType("torch")
    module.bfloat16 = object()  # type: ignore[attr-defined]
    module.float16 = object()  # type: ignore[attr-defined]
    module.float32 = object()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "torch", module)
    return module


def _legacy_encode(
    model: Any, texts: Sequence[str], cancel_check: Callable[[], bool] | None = None
) -> np.ndarray:
    """A copy of the encode algorithm as it was before the spec was added."""
    tokenizer = model.tokenizer
    limit = max(8, int(model.max_seq_length) - 2)
    chunks: list[str] = []
    owners: list[int] = []
    for owner, text in enumerate(texts):
        token_ids = tokenizer.encode(text, add_special_tokens=False)
        segments = [token_ids[i:i + limit] for i in range(0, len(token_ids), limit)] or [[]]
        for segment in segments:
            chunks.append(tokenizer.decode(segment, skip_special_tokens=True))
            owners.append(owner)
    vector_batches = []
    for start in range(0, len(chunks), 16):
        vector_batches.append(model.encode(
            chunks[start:start + 16], convert_to_numpy=True, normalize_embeddings=True,
            show_progress_bar=False, batch_size=16,
        ))
    vectors = np.concatenate(vector_batches, axis=0)
    grouped: list[list[np.ndarray]] = [[] for _ in texts]
    for owner, vector in zip(owners, vectors, strict=True):
        grouped[owner].append(vector)
    return np.stack([np.mean(group, axis=0) for group in grouped]).astype(np.float64)


TEXTS = [
    "a short text",
    "another text with a few more words in it",
    "",
    " ".join(f"word{i}" for i in range(75)),
    "x",
    "one two three four five six seven eight nine ten eleven twelve",
    " ".join(f"tok{i}" for i in range(31)),
]


def test_legacy_construction_is_unchanged(fake_st: FakeState) -> None:
    from mindrian_eureka.opportunity_pairs.encoders import SentenceTransformerEncoder

    SentenceTransformerEncoder("m")
    assert fake_st.init_args[-1] == ("m",)
    assert fake_st.init_calls[-1] == {"local_files_only": True, "revision": None}
    SentenceTransformerEncoder("m", allow_download=True, revision="r")
    assert fake_st.init_calls[-1] == {"local_files_only": False, "revision": "r"}


def test_legacy_encode_equals_the_oracle(fake_st: FakeState) -> None:
    from mindrian_eureka.opportunity_pairs.encoders import SentenceTransformerEncoder

    encoder = SentenceTransformerEncoder("m")
    result = encoder.encode(TEXTS)
    calls = list(fake_st.encode_calls)
    fake_st.encode_calls.clear()
    oracle = _legacy_encode(fake_st.models[0], TEXTS)
    assert result.dtype == np.float64
    assert np.array_equal(result, oracle)
    assert calls and all(len(batch) <= 16 for batch, _ in calls)
    assert sum(len(batch) for batch, _ in calls) > 16
    for _, kwargs in calls:
        assert kwargs == {
            "convert_to_numpy": True, "normalize_embeddings": True,
            "show_progress_bar": False, "batch_size": 16,
        }


def test_spec_construction_passes_device_dtype_attention(
    fake_st: FakeState, fake_torch: types.ModuleType
) -> None:
    from mindrian_eureka.encoder_spec import profile_spec
    from mindrian_eureka.opportunity_pairs.encoders import SentenceTransformerEncoder

    SentenceTransformerEncoder("m", spec=profile_spec("cpu-default"))
    call = fake_st.init_calls[-1]
    assert call["device"] == "cpu"
    assert "model_kwargs" not in call
    fake_st.width = 2048
    SentenceTransformerEncoder("m", spec=profile_spec("gpu-nemotron"))
    call = fake_st.init_calls[-1]
    assert call["device"] == "cuda"
    assert call["model_kwargs"] == {
        "dtype": fake_torch.bfloat16,  # type: ignore[attr-defined]
        "attn_implementation": "sdpa",
    }


def test_spec_applies_prefix_limit_and_batch(fake_st: FakeState) -> None:
    from mindrian_eureka.encoder_spec import profile_spec
    from mindrian_eureka.opportunity_pairs.encoders import SentenceTransformerEncoder

    spec = dataclasses.replace(
        profile_spec("cpu-default"),
        document_prefix="passage: ", max_seq_length=20, batch_size=4, normalize=False,
    )
    encoder = SentenceTransformerEncoder("m", spec=spec)
    assert fake_st.models[0].max_seq_length == 20
    text = " ".join(f"w{i}" for i in range(40))
    encoder.encode([text, "short one"])
    batches = [batch for batch, _ in fake_st.encode_calls]
    assert batches
    strings = [item for batch in batches for item in batch]
    assert all(item.startswith("passage: ") for item in strings)
    assert all(len(batch) <= 4 for batch in batches)
    assert all(kwargs["normalize_embeddings"] is False for _, kwargs in fake_st.encode_calls)
    # limit is max(8, 20 - 2 - 2) = 16 tokens; "passage: " is 2 tokens in the fake.
    tokenizer = fake_st.models[0].tokenizer
    longest = max(len(tokenizer.encode(item[len("passage: "):])) for item in strings)
    assert longest == 16
    assert len(strings) == 4  # 40 tokens -> 16 + 16 + 8, plus the short text


def test_dimension_mismatch_is_loud(fake_st: FakeState) -> None:
    from mindrian_eureka.encoder_spec import custom_spec, profile_spec
    from mindrian_eureka.opportunity_pairs.encoders import SentenceTransformerEncoder

    fake_st.width = 5
    spec = dataclasses.replace(profile_spec("cpu-default"), dimension=8)
    with pytest.raises(RuntimeError) as caught:
        SentenceTransformerEncoder("m", spec=spec)
    message = str(caught.value)
    assert "5" in message
    assert "8" in message
    assert "cpu-default" in message
    SentenceTransformerEncoder("m", spec=custom_spec("m"))


def test_encode_raw_matches_the_wording_engine_call(fake_st: FakeState) -> None:
    from mindrian_eureka.encoder_spec import profile_spec
    from mindrian_eureka.opportunity_pairs.encoders import SentenceTransformerEncoder

    encoder = SentenceTransformerEncoder("m")
    result = encoder.encode_raw(["a", "b"])
    assert len(fake_st.encode_calls) == 1
    batch, kwargs = fake_st.encode_calls[0]
    assert batch == ["a", "b"]
    assert kwargs == {"show_progress_bar": False}
    assert result.dtype == np.float32
    assert result.shape == (2, 384)
    fake_st.encode_calls.clear()
    spec = dataclasses.replace(profile_spec("cpu-default"), document_prefix="p: ")
    SentenceTransformerEncoder("m", spec=spec).encode_raw(["a", "b"])
    assert fake_st.encode_calls[0][0] == ["p: a", "p: b"]


def test_missing_package_text_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    from mindrian_eureka.encoder_spec import profile_spec
    from mindrian_eureka.opportunity_pairs.encoders import SentenceTransformerEncoder

    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    with pytest.raises(RuntimeError) as caught:
        SentenceTransformerEncoder("m")
    assert "Install the optional extra: pip install 'mindrian-eureka[modern-encoder]'" in str(
        caught.value
    )
    with pytest.raises(RuntimeError) as caught_gpu:
        SentenceTransformerEncoder("m", spec=profile_spec("gpu-nemotron"))
    assert "mindrian-eureka[gpu-encoder]" in str(caught_gpu.value)


class Recorder:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs


def test_make_encoder_legacy_call_and_spec_call() -> None:
    from mindrian_eureka.encoder_spec import custom_spec, profile_spec
    from mindrian_eureka.opportunity_pairs.encoders import make_encoder

    legacy = make_encoder(custom_spec("m"), model_path="m", backend=Recorder)
    assert isinstance(legacy, Recorder)
    assert legacy.args == ("m",)
    assert legacy.kwargs == {"allow_download": False, "revision": None}
    spec = profile_spec("cpu-default")
    named = make_encoder(spec, model_path="/x", backend=Recorder)
    assert isinstance(named, Recorder)
    assert named.args == ("/x",)
    assert named.kwargs == {"allow_download": False, "revision": None, "spec": spec}
    modified = dataclasses.replace(custom_spec("m"), device="cuda")
    other = make_encoder(modified, model_path="m", backend=Recorder, allow_download=True)
    assert isinstance(other, Recorder)
    assert other.kwargs == {"allow_download": True, "revision": None, "spec": modified}
    plain = make_encoder(custom_spec("m"), model_path="m", backend=HashingEncoder)
    assert isinstance(plain, HashingEncoder)
    assert plain.spec is None
    with_spec = make_encoder(spec, model_path="m", backend=HashingEncoder)
    assert isinstance(with_spec, HashingEncoder)
    assert with_spec.spec == spec


def test_encoder_protocol(fake_st: FakeState) -> None:
    from mindrian_eureka.encoder_spec import profile_spec
    from mindrian_eureka.opportunity_pairs.encoders import Encoder, make_encoder

    spec = profile_spec("cpu-default")
    encoder = make_encoder(spec, model_path="m")
    for attribute in ("name", "version", "spec", "encode", "encode_raw"):
        assert hasattr(encoder, attribute)
    assert encoder.spec == spec
    assert isinstance(encoder, Encoder)


def test_real_minilm_spec_path_equals_legacy_path() -> None:
    from mindrian_eureka.encoder_spec import profile_spec
    from mindrian_eureka.models import discover_model
    from mindrian_eureka.opportunity_pairs.encoders import (
        SentenceTransformerEncoder,
        make_encoder,
    )

    found = discover_model()
    if not found.ok or found.path is None:
        pytest.skip("the local MiniLM model is not on disk")
    path = str(found.path)
    texts = [
        "A cheap sensor that tracks soil moisture.",
        "Hospital scheduling with fewer missed appointments.",
        "Wine bottle labels printed on demand.",
        "Rural clinics share one radiology reader.",
        "An open index of university patents " * 40,
        "",
    ]
    legacy = SentenceTransformerEncoder(path).encode(texts)
    via_spec = make_encoder(profile_spec("cpu-default"), model_path=path).encode(texts)
    assert legacy.dtype == via_spec.dtype == np.float64
    assert np.array_equal(legacy, via_spec)
