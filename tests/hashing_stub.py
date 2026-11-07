"""Deterministic stand-in for the sentence encoder. It needs no model files.

The vectors come from hashed word buckets. They are stable across processes
because the hash is blake2b, not the built-in `hash`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence

import numpy as np
from numpy.typing import NDArray

EMBED_DIM = 64


def hashing_encode(items: Sequence[str]) -> NDArray[np.float64]:
    """Encode each text as a signed word-bucket vector with unit length.

    Args:
        items: The texts to encode.

    Returns:
        A float64 array of shape (len(items), EMBED_DIM). Each row has L2 norm 1.
    """
    out = np.zeros((len(items), EMBED_DIM), dtype=np.float64)
    for row, text in enumerate(items):
        for token in text.lower().split():
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % EMBED_DIM
            sign = 1.0 if digest[4] % 2 == 1 else -1.0
            out[row, bucket] += sign
        norm = float(np.linalg.norm(out[row]))
        if norm == 0.0:
            out[row, 0] = 1.0
        else:
            out[row] /= norm
    return out


class HashingEncoder:
    """Same interface as SentenceTransformerEncoder. Never touches network or disk."""

    def __init__(
        self,
        model_path: str,
        *,
        allow_download: bool = False,
        revision: str | None = None,
        spec: object | None = None,
    ) -> None:
        self.model_path = model_path
        self.spec = spec
        self.name = "sentence-transformers"
        self.version = model_path

    def encode(
        self, texts: Sequence[str], cancel_check: Callable[[], bool] | None = None
    ) -> NDArray[np.float64]:
        """Return one hashed vector per text."""
        return hashing_encode(texts)
