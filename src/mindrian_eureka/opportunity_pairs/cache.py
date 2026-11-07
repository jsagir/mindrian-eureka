"""Local content-addressed cache for derived semantic vectors only."""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sqlite3
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np

BASE_PROFILE = "cpu-default"
_PROFILE_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")


class EmbeddingCache:
    """SQLite cache keyed by text digest + encoder/model identity.

    Raw text is never stored. The cache is local user data because embeddings
    remain derived representations of potentially confidential material.
    """

    SCHEMA_VERSION = 2
    MAX_BYTES = 1024 * 1024 * 1024
    PRUNE_TO_BYTES = 768 * 1024 * 1024

    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            os.chmod(self.path.parent, 0o700)
        except OSError:
            pass
        with self._connect() as db:
            db.execute("PRAGMA auto_vacuum=INCREMENTAL")
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=NORMAL")
            db.execute("""CREATE TABLE IF NOT EXISTS embeddings (
                cache_key TEXT PRIMARY KEY,
                payload BLOB NOT NULL,
                created_at REAL NOT NULL,
                last_used REAL NOT NULL
            )""")
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=30)
        db.execute("PRAGMA busy_timeout=30000")
        return db

    @staticmethod
    def key(text: str, *, encoder: str, model: str, revision: str | None, method_version: str,
            identity: Mapping[str, Any] | None = None) -> str:
        material = json.dumps({
            "schema": EmbeddingCache.SCHEMA_VERSION,
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "encoder": encoder,
            "model": model,
            "revision": revision,
            "method_version": method_version,
            "identity": dict(identity) if identity is not None else None,
        }, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(material).hexdigest()

    def get(self, key: str) -> np.ndarray | None:
        with self._connect() as db:
            row = db.execute("SELECT payload FROM embeddings WHERE cache_key=?", (key,)).fetchone()
            if row is None:
                return None
            db.execute("UPDATE embeddings SET last_used=? WHERE cache_key=?", (time.time(), key))
        array = self._decode(row[0])
        if array is None:
            self.delete(key)
        return array

    @staticmethod
    def _decode(payload: bytes) -> np.ndarray | None:
        """Return the stored vectors, or None when the payload is damaged.

        A payload whose own width header disagrees with its array is damaged.
        A payload without a width header is accepted (older shape).
        """
        try:
            with np.load(io.BytesIO(payload), allow_pickle=False) as stored:
                array = np.asarray(stored["vectors"], dtype=np.float64)
                if "width" in stored.files and int(stored["width"]) != array.shape[-1]:
                    return None
                return array
        except Exception:
            return None

    def get_many(self, keys: Sequence[str]) -> list[np.ndarray | None]:
        values: list[np.ndarray | None] = []
        now = time.time()
        with self._connect() as db:
            for key in keys:
                row = db.execute("SELECT payload FROM embeddings WHERE cache_key=?", (key,)).fetchone()
                if row is None:
                    values.append(None)
                    continue
                db.execute("UPDATE embeddings SET last_used=? WHERE cache_key=?", (now, key))
                array = self._decode(row[0])
                if array is None:
                    db.execute("DELETE FROM embeddings WHERE cache_key=?", (key,))
                values.append(array)
        return values

    def put(self, key: str, vectors: np.ndarray) -> None:
        array = np.asarray(vectors, dtype=np.float64)
        buffer = io.BytesIO()
        np.savez_compressed(buffer, vectors=array, width=np.int64(array.shape[-1]))
        payload = buffer.getvalue()
        now = time.time()
        with self._connect() as db:
            db.execute(
                "INSERT INTO embeddings(cache_key,payload,created_at,last_used) VALUES(?,?,?,?) "
                "ON CONFLICT(cache_key) DO UPDATE SET payload=excluded.payload,last_used=excluded.last_used",
                (key, payload, now, now),
            )
            self._prune(db)

    def delete(self, key: str) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM embeddings WHERE cache_key=?", (key,))

    def clear(self) -> int:
        # The delete must be committed before the checkpoint and the vacuum:
        # neither can run inside an open transaction ("database table is locked").
        db = self._connect()
        try:
            with db:
                count = db.execute("SELECT count(*) FROM embeddings").fetchone()[0]
                db.execute("DELETE FROM embeddings")
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            db.execute("VACUUM")
        finally:
            db.close()
        return int(count)

    def stats(self) -> dict:
        with self._connect() as db:
            count, size = db.execute("SELECT count(*), COALESCE(sum(length(payload)),0) FROM embeddings").fetchone()
        return {"entries": int(count), "payload_bytes": int(size), "maximum_payload_bytes": self.MAX_BYTES}

    def _prune(self, db: sqlite3.Connection) -> None:
        size = int(db.execute("SELECT COALESCE(sum(length(payload)),0) FROM embeddings").fetchone()[0])
        if size <= self.MAX_BYTES:
            return
        rows = db.execute("SELECT cache_key,length(payload) FROM embeddings ORDER BY last_used ASC").fetchall()
        for key, payload_size in rows:
            db.execute("DELETE FROM embeddings WHERE cache_key=?", (key,))
            size -= int(payload_size)
            if size <= self.PRUNE_TO_BYTES:
                break


def _validate_profile(profile: str) -> str:
    if not isinstance(profile, str) or not _PROFILE_NAME.fullmatch(profile):
        raise ValueError(
            "A profile name must be 1 to 40 characters of lower-case letters, digits "
            "and hyphens, and must not start with a hyphen."
        )
    return profile


def profile_cache_path(path: str | Path, profile: str | None) -> Path:
    """Return the cache file of one profile in the folder of the base cache file."""
    base = Path(path)
    if profile is None:
        return base
    _validate_profile(profile)
    if profile == BASE_PROFILE:
        return base
    return base.with_name(f"{base.stem}-{profile}{base.suffix}")


def default_cache_path(profile: str | None = None) -> Path:
    override = os.environ.get("MINDRIAN_EUREKA_CACHE_DIR")
    root = Path(override).expanduser() if override else Path.home() / ".cache" / "mindrian-eureka"
    return profile_cache_path(root / "embeddings.sqlite3", profile)


def cached_encode(texts: Sequence[str], *, cache: EmbeddingCache, encoder_name: str,
                  model_path: str, model_revision: str | None, method_version: str,
                  encode_missing, cancel_check: Callable[[], bool] | None = None,
                  identity: Mapping[str, Any] | None = None,
                  expected_dimension: int | None = None) -> tuple[list[np.ndarray], dict]:
    keys = [cache.key(text, encoder=encoder_name, model=model_path,
                      revision=model_revision, method_version=method_version,
                      identity=identity) for text in texts]
    values = cache.get_many(keys)
    dimension_rejected = 0
    if expected_dimension is not None:
        for index, value in enumerate(values):
            if value is not None and value.shape[-1] != expected_dimension:
                cache.delete(keys[index])
                values[index] = None
                dimension_rejected += 1
    missing = [i for i, value in enumerate(values) if value is None]
    if missing:
        if cancel_check and cancel_check():
            raise RuntimeError("Run cancelled before semantic embedding")
        generated = encode_missing([texts[i] for i in missing], cancel_check)
        if len(generated) != len(missing):
            raise RuntimeError("Encoder returned a different number of vectors than requested")
        arrays = []
        for vectors in generated:
            array = np.asarray(vectors, dtype=np.float64)
            if array.ndim == 1:
                array = array.reshape(1, -1)
            if expected_dimension is not None and array.shape[-1] != expected_dimension:
                raise RuntimeError(
                    f"The encoder made vectors of width {array.shape[-1]} but the declared "
                    f"setup expects width {expected_dimension}; the encoder does not match "
                    "the declared setup."
                )
            arrays.append(array)
        for index, array in zip(missing, arrays):
            cache.put(keys[index], array)
            values[index] = array
    result = [np.asarray(value, dtype=np.float64) for value in values if value is not None]
    widths = {int(vector.shape[-1]) for vector in result}
    if len(widths) > 1:
        raise RuntimeError(
            f"The encoder results have different widths: {sorted(widths)}."
        )
    return result, {
        "hits": len(texts) - len(missing), "misses": len(missing),
        "cache_entries": cache.stats()["entries"],
        "dimension_rejected": dimension_rejected,
    }
