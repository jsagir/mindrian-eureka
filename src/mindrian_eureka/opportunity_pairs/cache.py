"""Local content-addressed cache for derived semantic vectors only."""

from __future__ import annotations

import hashlib
import io
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Callable, Sequence

import numpy as np


class EmbeddingCache:
    """SQLite cache keyed by text digest + encoder/model identity.

    Raw text is never stored. The cache is local user data because embeddings
    remain derived representations of potentially confidential material.
    """

    SCHEMA_VERSION = 1
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
    def key(text: str, *, encoder: str, model: str, revision: str | None, method_version: str) -> str:
        material = json.dumps({
            "schema": EmbeddingCache.SCHEMA_VERSION,
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "encoder": encoder,
            "model": model,
            "revision": revision,
            "method_version": method_version,
        }, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(material).hexdigest()

    def get(self, key: str) -> np.ndarray | None:
        with self._connect() as db:
            row = db.execute("SELECT payload FROM embeddings WHERE cache_key=?", (key,)).fetchone()
            if row is None:
                return None
            db.execute("UPDATE embeddings SET last_used=? WHERE cache_key=?", (time.time(), key))
        try:
            with np.load(io.BytesIO(row[0]), allow_pickle=False) as stored:
                return np.asarray(stored["vectors"], dtype=np.float64)
        except Exception:
            self.delete(key)
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
                try:
                    with np.load(io.BytesIO(row[0]), allow_pickle=False) as stored:
                        values.append(np.asarray(stored["vectors"], dtype=np.float64))
                except Exception:
                    db.execute("DELETE FROM embeddings WHERE cache_key=?", (key,))
                    values.append(None)
        return values

    def put(self, key: str, vectors: np.ndarray) -> None:
        array = np.asarray(vectors, dtype=np.float64)
        buffer = io.BytesIO()
        np.savez_compressed(buffer, vectors=array)
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
        with self._connect() as db:
            count = db.execute("SELECT count(*) FROM embeddings").fetchone()[0]
            db.execute("DELETE FROM embeddings")
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            db.execute("VACUUM")
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


def default_cache_path() -> Path:
    override = os.environ.get("MINDRIAN_EUREKA_CACHE_DIR")
    root = Path(override).expanduser() if override else Path.home() / ".cache" / "mindrian-eureka"
    return root / "embeddings.sqlite3"


def cached_encode(texts: Sequence[str], *, cache: EmbeddingCache, encoder_name: str,
                  model_path: str, model_revision: str | None, method_version: str,
                  encode_missing, cancel_check: Callable[[], bool] | None = None) -> tuple[list[np.ndarray], dict]:
    keys = [cache.key(text, encoder=encoder_name, model=model_path,
                      revision=model_revision, method_version=method_version) for text in texts]
    values = cache.get_many(keys)
    missing = [i for i, value in enumerate(values) if value is None]
    if missing:
        if cancel_check and cancel_check():
            raise RuntimeError("Run cancelled before semantic embedding")
        generated = encode_missing([texts[i] for i in missing], cancel_check)
        if len(generated) != len(missing):
            raise RuntimeError("Encoder returned a different number of vectors than requested")
        for index, vectors in zip(missing, generated):
            array = np.asarray(vectors, dtype=np.float64)
            if array.ndim == 1:
                array = array.reshape(1, -1)
            cache.put(keys[index], array)
            values[index] = array
    return [np.asarray(value, dtype=np.float64) for value in values if value is not None], {
        "hits": len(texts) - len(missing), "misses": len(missing),
        "cache_entries": cache.stats()["entries"],
    }
