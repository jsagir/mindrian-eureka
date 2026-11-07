"""Tests of the schema 2 cache key, the width check, the profile files and the clear command."""

from __future__ import annotations

import hashlib
import io
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np
import pytest

IDENTITY_FIELDS = (
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
)

BASE_IDENTITY = {
    "profile": "cpu-default",
    "model_id": "all-MiniLM-L6-v2",
    "revision": "abc123",
    "model_digest": "d" * 64,
    "dimension": 384,
    "dtype": "float32",
    "attention": "eager",
    "device": "cpu",
    "query_prefix": "",
    "document_prefix": "",
    "normalize": True,
    "chunking": "window-256",
    "batch_size": 32,
    "max_seq_length": 256,
}

CHANGED_VALUES = {
    "profile": "gpu-nemotron",
    "model_id": "other-model",
    "revision": "def456",
    "model_digest": "e" * 64,
    "dimension": 2048,
    "dtype": "bfloat16",
    "attention": "sdpa",
    "device": "cuda",
    "query_prefix": "query: ",
    "document_prefix": "passage: ",
    "normalize": False,
    "chunking": "window-512",
    "batch_size": 8,
    "max_seq_length": 512,
}

KEY_ARGS = {
    "encoder": "sentence-transformers",
    "model": "m",
    "revision": "r",
    "method_version": "v1",
}


def _key(text: str = "alpha", **kwargs):
    from mindrian_eureka.opportunity_pairs.cache import EmbeddingCache

    return EmbeddingCache.key(text, **{**KEY_ARGS, **kwargs})


def _cached(cache, texts, encode_missing, **kwargs):
    from mindrian_eureka.opportunity_pairs.cache import cached_encode

    return cached_encode(
        texts,
        cache=cache,
        encoder_name=KEY_ARGS["encoder"],
        model_path=KEY_ARGS["model"],
        model_revision=KEY_ARGS["revision"],
        method_version=KEY_ARGS["method_version"],
        encode_missing=encode_missing,
        **kwargs,
    )


def _payload(vectors: np.ndarray, width: int | None) -> bytes:
    buffer = io.BytesIO()
    if width is None:
        np.savez_compressed(buffer, vectors=vectors)
    else:
        np.savez_compressed(buffer, vectors=vectors, width=np.int64(width))
    return buffer.getvalue()


def _insert_row(path: Path, key: str, payload: bytes) -> None:
    now = time.time()
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO embeddings(cache_key,payload,created_at,last_used) VALUES(?,?,?,?)",
            (key, payload, now, now),
        )


def _has_row(path: Path, key: str) -> bool:
    with sqlite3.connect(path) as db:
        sql = "SELECT count(*) FROM embeddings WHERE cache_key=?"
        return db.execute(sql, (key,)).fetchone()[0] == 1


def test_schema_version_is_2():
    from mindrian_eureka.opportunity_pairs.cache import EmbeddingCache

    assert EmbeddingCache.SCHEMA_VERSION == 2


def test_key_differs_from_the_schema_1_formula():
    old = hashlib.sha256(
        json.dumps(
            {
                "schema": 1,
                "text_sha256": hashlib.sha256(b"alpha").hexdigest(),
                "encoder": KEY_ARGS["encoder"],
                "model": KEY_ARGS["model"],
                "revision": KEY_ARGS["revision"],
                "method_version": KEY_ARGS["method_version"],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    assert _key() != old
    assert _key(identity=dict(BASE_IDENTITY)) != old


@pytest.mark.parametrize("field", IDENTITY_FIELDS)
def test_key_changes_with_every_identity_field(field):
    changed = dict(BASE_IDENTITY)
    changed[field] = CHANGED_VALUES[field]
    assert changed[field] != BASE_IDENTITY[field]
    assert _key(identity=changed) != _key(identity=dict(BASE_IDENTITY))


def test_key_ignores_identity_insertion_order():
    forward = dict(BASE_IDENTITY)
    backward = dict(reversed(list(BASE_IDENTITY.items())))
    assert list(forward) != list(backward)
    assert _key(identity=forward) == _key(identity=backward)
    assert _key(identity=None) != _key(identity={})
    assert _key() == _key(identity=None)


def test_old_schema_entries_are_ignored(tmp_path):
    from mindrian_eureka.opportunity_pairs.cache import EmbeddingCache

    cache = EmbeddingCache(tmp_path / "c" / "embeddings.sqlite3")
    old_key = hashlib.sha256(
        json.dumps(
            {
                "schema": 1,
                "text_sha256": hashlib.sha256(b"alpha").hexdigest(),
                "encoder": KEY_ARGS["encoder"],
                "model": KEY_ARGS["model"],
                "revision": KEY_ARGS["revision"],
                "method_version": KEY_ARGS["method_version"],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    _insert_row(cache.path, old_key, _payload(np.ones((1, 3)), None))
    calls = []

    def encode_missing(texts, cancel):
        calls.append(list(texts))
        return [np.full((1, 3), 2.0) for _ in texts]

    vectors, meta = _cached(cache, ["alpha"], encode_missing, identity=dict(BASE_IDENTITY))
    assert calls == [["alpha"]]
    assert meta["misses"] == 1
    assert meta["hits"] == 0
    assert float(vectors[0][0][0]) == 2.0
    assert _has_row(cache.path, old_key)
    assert cache.stats()["entries"] == 2


def test_hit_with_the_wrong_width_is_rejected(tmp_path):
    from mindrian_eureka.opportunity_pairs.cache import EmbeddingCache

    cache = EmbeddingCache(tmp_path / "embeddings.sqlite3")
    identity = dict(BASE_IDENTITY)
    key = _key(identity=identity)
    cache.put(key, np.ones((1, 3)))
    calls = []

    def encode_missing(texts, cancel):
        calls.append(list(texts))
        return [np.full((1, 5), 7.0) for _ in texts]

    vectors, meta = _cached(
        cache, ["alpha"], encode_missing, identity=identity, expected_dimension=5
    )
    assert calls == [["alpha"]]
    assert meta["dimension_rejected"] == 1
    assert meta["misses"] == 1
    assert vectors[0].shape[-1] == 5
    stored = cache.get(key)
    assert stored is not None
    assert stored.shape[-1] == 5
    vectors2, meta2 = _cached(
        cache, ["alpha"], encode_missing, identity=identity, expected_dimension=5
    )
    assert calls == [["alpha"]]
    assert meta2["dimension_rejected"] == 0
    assert meta2["hits"] == 1
    assert vectors2[0].shape[-1] == 5


def test_generated_width_mismatch_raises_and_stores_nothing(tmp_path):
    from mindrian_eureka.opportunity_pairs.cache import EmbeddingCache

    cache = EmbeddingCache(tmp_path / "embeddings.sqlite3")
    before = cache.stats()["entries"]

    def encode_missing(texts, cancel):
        return [np.ones((1, 4)) for _ in texts]

    with pytest.raises(RuntimeError) as caught:
        _cached(
            cache,
            ["alpha", "beta"],
            encode_missing,
            identity=dict(BASE_IDENTITY),
            expected_dimension=5,
        )
    assert "4" in str(caught.value)
    assert "5" in str(caught.value)
    assert cache.stats()["entries"] == before


def test_mixed_widths_raise(tmp_path):
    from mindrian_eureka.opportunity_pairs.cache import EmbeddingCache

    cache = EmbeddingCache(tmp_path / "embeddings.sqlite3")
    cache.put(_key("alpha"), np.ones((1, 3)))

    def encode_missing(texts, cancel):
        return [np.ones((1, 4)) for _ in texts]

    with pytest.raises(RuntimeError) as caught:
        _cached(cache, ["alpha", "beta"], encode_missing)
    assert "different widths" in str(caught.value)


def test_legacy_call_shape_is_unchanged(tmp_path):
    from mindrian_eureka.opportunity_pairs.cache import EmbeddingCache

    cache = EmbeddingCache(tmp_path / "embeddings.sqlite3")
    cache.put(_key("alpha"), np.full((1, 3), 1.0))
    seen = []

    def encode_missing(texts, cancel):
        seen.append((list(texts), cancel))
        return [np.full((1, 3), 2.0) for _ in texts]

    cancel = lambda: False  # noqa: E731
    vectors, meta = _cached(cache, ["alpha", "beta"], encode_missing, cancel_check=cancel)
    assert [float(v[0][0]) for v in vectors] == [1.0, 2.0]
    assert set(meta) >= {"hits", "misses", "cache_entries", "dimension_rejected"}
    assert meta["dimension_rejected"] == 0
    assert meta["hits"] == 1
    assert meta["misses"] == 1
    assert seen == [(["beta"], cancel)]


def test_payload_width_header(tmp_path):
    from mindrian_eureka.opportunity_pairs.cache import EmbeddingCache

    cache = EmbeddingCache(tmp_path / "embeddings.sqlite3")
    cache.put("good", np.ones((2, 6)))
    with sqlite3.connect(cache.path) as db:
        blob = db.execute("SELECT payload FROM embeddings WHERE cache_key='good'").fetchone()[0]
    with np.load(io.BytesIO(blob), allow_pickle=False) as stored:
        assert int(stored["width"]) == 6

    _insert_row(cache.path, "bad-one", _payload(np.ones((2, 6)), 5))
    assert cache.get("bad-one") is None
    assert not _has_row(cache.path, "bad-one")

    _insert_row(cache.path, "bad-many", _payload(np.ones((2, 6)), 5))
    values = cache.get_many(["good", "bad-many"])
    assert values[0] is not None
    assert values[1] is None
    assert not _has_row(cache.path, "bad-many")

    _insert_row(cache.path, "legacy", _payload(np.ones((1, 4)), None))
    legacy = cache.get("legacy")
    assert legacy is not None
    assert legacy.shape == (1, 4)


def test_profile_cache_paths(monkeypatch, tmp_path):
    from mindrian_eureka.opportunity_pairs.cache import default_cache_path, profile_cache_path

    base = Path("c/embeddings.sqlite3")
    assert profile_cache_path(base, "cpu-default") == base
    assert profile_cache_path(base, "gpu-nemotron") == Path("c/embeddings-gpu-nemotron.sqlite3")

    monkeypatch.setenv("MINDRIAN_EUREKA_CACHE_DIR", str(tmp_path / "cachedir"))
    assert default_cache_path() == tmp_path / "cachedir" / "embeddings.sqlite3"
    expected = tmp_path / "cachedir" / "embeddings-gpu-nemotron.sqlite3"
    assert default_cache_path("gpu-nemotron") == expected
    assert default_cache_path("cpu-default") == default_cache_path()

    for bad in ("../x", "a/b", "A", "-a", "", "has space", "a" * 41):
        with pytest.raises(ValueError):
            profile_cache_path(base, bad)
        with pytest.raises(ValueError):
            default_cache_path(bad)
    assert profile_cache_path(base, "a" * 40).name == "embeddings-" + "a" * 40 + ".sqlite3"


def test_profiles_do_not_share_a_file(tmp_path):
    from mindrian_eureka.opportunity_pairs.cache import EmbeddingCache, profile_cache_path

    base = tmp_path / "c" / "embeddings.sqlite3"
    gpu = EmbeddingCache(profile_cache_path(base, "gpu-nemotron"))
    cpu = EmbeddingCache(profile_cache_path(base, "cpu-default"))
    key = _key()
    gpu.put(key, np.ones((1, 8)))
    assert gpu.get(key) is not None
    assert cpu.get(key) is None
    assert cpu.stats()["entries"] == 0
    assert gpu.path != cpu.path


@pytest.mark.skipif(os.name != "posix", reason="posix permissions")
def test_new_profile_file_is_private(tmp_path):
    from mindrian_eureka.opportunity_pairs.cache import EmbeddingCache, profile_cache_path

    path = profile_cache_path(tmp_path / "fresh" / "embeddings.sqlite3", "gpu-nemotron")
    EmbeddingCache(path)
    assert (path.parent.stat().st_mode & 0o777) == 0o700
    assert (path.stat().st_mode & 0o777) == 0o600


def test_clear_cache_all_profiles(tmp_path, monkeypatch, capsys):
    from mindrian_eureka.opportunity_pairs.cache import EmbeddingCache
    from mindrian_eureka.opportunity_pairs.cli import clear_cache_main

    folder = tmp_path / "caches"
    files = [
        folder / "embeddings.sqlite3",
        folder / "embeddings-gpu-nemotron.sqlite3",
        folder / "embeddings-other.sqlite3",
    ]
    for path in files:
        EmbeddingCache(path).put("k", np.ones((1, 2)))
    notes = folder / "notes.txt"
    notes.write_text("keep me", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["x", "--cache-path", str(files[0]), "--all-profiles"])
    clear_cache_main()
    out = json.loads(capsys.readouterr().out)
    assert out["deleted_embeddings"] == 3
    assert sorted(out["cache_paths"]) == sorted(str(p) for p in files)
    for path in files:
        assert EmbeddingCache(path).stats()["entries"] == 0
    assert notes.read_text(encoding="utf-8") == "keep me"

    for path in files:
        EmbeddingCache(path).put("k", np.ones((1, 2)))
    monkeypatch.setattr(sys, "argv", ["x", "--cache-path", str(files[0])])
    clear_cache_main()
    out = json.loads(capsys.readouterr().out)
    assert set(out) == {"deleted_embeddings", "cache_path"}
    assert out["deleted_embeddings"] == 1
    assert EmbeddingCache(files[0]).stats()["entries"] == 0
    assert EmbeddingCache(files[1]).stats()["entries"] == 1
    assert EmbeddingCache(files[2]).stats()["entries"] == 1
