"""The spec layer of the encoder seam.

This module holds plain data only: no model, no numpy, no path. An `EncoderSpec` names every
setting that changes a vector. Its fingerprint is the identity of the vector space, so two
different setups never share a cache entry or look equal in a manifest.

Only the standard library is imported, so the module is cheap to load from the doctor, the
manifest writer and the cache key code.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from typing import Any

RESULT_LABEL = "candidate, not verified"

DEFAULT_PROFILE = "cpu-default"
GPU_PROFILE = "gpu-nemotron"
CUSTOM_PROFILE = "custom"

CHUNKING_TOKEN_WINDOW = "token-window-mean"
CHUNKING_CALLER = "caller"

DETERMINISM_CPU_EXACT = "cpu-exact"
DETERMINISM_GPU_APPROX = "gpu-approx"

ENCODER_BLOCK_SCHEMA = "eureka.encoder-block.v1"

MODERN_EXTRA = "modern-encoder"
GPU_EXTRA = "gpu-encoder"

IDENTITY_KEYS: tuple[str, ...] = (
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

_DTYPES = (None, "float32", "float16", "bfloat16")
_ATTENTIONS = (None, "sdpa", "eager", "flash_attention_2")
_CHUNKINGS = (CHUNKING_TOKEN_WINDOW, CHUNKING_CALLER)
_DEVICE_PATTERN = re.compile(r"^(cpu|mps|cuda|cuda:[0-9]+)$")
_MIN_SEQ_LENGTH = 8


@dataclass(frozen=True)
class EncoderSpec:
    """Every setting that changes a vector.

    Attributes:
        profile: The profile name, or `custom` for a bare model folder.
        model_id: The model name or folder name. It is never an absolute path in a profile.
        revision: The pinned model revision, or None when it is not pinned.
        model_digest: A digest of the model files, or None when it is not recorded.
        dimension: The declared vector width, or None when it is not declared.
        dtype: The model weight type (`float32`, `float16`, `bfloat16`), or None for the default.
        attention: The attention kernel (`sdpa`, `eager`, `flash_attention_2`), or None.
        device: `cpu`, `mps`, `cuda` or `cuda:<n>`.
        query_prefix: The text put before a query.
        document_prefix: The text put before a document chunk.
        normalize: True when the encoder normalizes each chunk vector.
        chunking: `token-window-mean` or `caller`.
        batch_size: The number of chunks for each model call, or None when the caller chunks.
        max_seq_length: The token window cap, or None to keep the model default.
    """

    profile: str
    model_id: str
    revision: str | None = None
    model_digest: str | None = None
    dimension: int | None = None
    dtype: str | None = None
    attention: str | None = None
    device: str = "cpu"
    query_prefix: str = ""
    document_prefix: str = ""
    normalize: bool = True
    chunking: str = CHUNKING_TOKEN_WINDOW
    batch_size: int | None = 16
    max_seq_length: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.profile, str) or not self.profile:
            raise ValueError("profile must be a non-empty string")
        if not isinstance(self.model_id, str) or not self.model_id:
            raise ValueError("model_id must be a non-empty string")
        for name in ("revision", "model_digest"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{name} must be a string or None")
        if self.dimension is not None and (
            isinstance(self.dimension, bool) or not isinstance(self.dimension, int)
            or self.dimension < 1
        ):
            raise ValueError("dimension must be a whole number of 1 or more, or None")
        if self.dtype not in _DTYPES:
            raise ValueError("dtype must be one of float32, float16, bfloat16, or None")
        if self.attention not in _ATTENTIONS:
            raise ValueError("attention must be one of sdpa, eager, flash_attention_2, or None")
        if not isinstance(self.device, str) or not _DEVICE_PATTERN.match(self.device):
            raise ValueError("device must be cpu, mps, cuda or cuda:<number>")
        for name in ("query_prefix", "document_prefix"):
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"{name} must be a string")
        if not isinstance(self.normalize, bool):
            raise ValueError("normalize must be true or false")
        if self.chunking not in _CHUNKINGS:
            raise ValueError("chunking must be token-window-mean or caller")
        if self.batch_size is not None and (
            isinstance(self.batch_size, bool) or not isinstance(self.batch_size, int)
            or self.batch_size < 1
        ):
            raise ValueError("batch_size must be a whole number of 1 or more, or None")
        if self.max_seq_length is not None and (
            isinstance(self.max_seq_length, bool) or not isinstance(self.max_seq_length, int)
            or self.max_seq_length < _MIN_SEQ_LENGTH
        ):
            raise ValueError(
                f"max_seq_length must be a whole number of {_MIN_SEQ_LENGTH} or more, or None"
            )

    def identity(self) -> dict[str, Any]:
        """Return the 14 identity fields in a fixed order. The dict holds no path."""
        return {key: getattr(self, key) for key in IDENTITY_KEYS}

    def fingerprint(self) -> str:
        """Return `sha256:` plus the hash of the canonical JSON of the identity."""
        text = json.dumps(
            self.identity(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

    def determinism_class(self) -> str:
        """Return `cpu-exact` for a plain CPU setup, and `gpu-approx` for every other setup."""
        if self.device == "cpu" and self.dtype in (None, "float32") and self.attention is None:
            return DETERMINISM_CPU_EXACT
        return DETERMINISM_GPU_APPROX

    def for_caller_chunks(self) -> EncoderSpec:
        """Return a copy for an engine that cuts the text itself (no batch size)."""
        return replace(self, chunking=CHUNKING_CALLER, batch_size=None)

    def prefix_for(self, role: str) -> str:
        """Return the prefix for the role `document` or `query`."""
        if role == "document":
            return self.document_prefix
        if role == "query":
            return self.query_prefix
        raise ValueError("role must be document or query")

    def is_legacy_equivalent(self, model_path: str, revision: str | None) -> bool:
        """True when this spec equals the spec that the old bare call implied."""
        return self == custom_spec(model_path, revision)


# The cpu-default row is today's behavior: MiniLM, no prefix, window cut by the model limit.
# The gpu-nemotron row comes from the model card as read in 05-RESEARCH.md Q3. The prefix
# whitespace, the `sdpa` setting and the pin of the revision are confirmed or changed by the
# spike record (plan 05-08). No revision hash is invented here. The 4096 limit is the NVIDIA
# evaluation length from the same source; it bounds memory on a 12 GB card.
PROFILES: dict[str, EncoderSpec] = {
    DEFAULT_PROFILE: EncoderSpec(
        profile=DEFAULT_PROFILE,
        model_id="sentence-transformers/all-MiniLM-L6-v2",
        dimension=384,
        device="cpu",
        normalize=True,
        chunking=CHUNKING_TOKEN_WINDOW,
        batch_size=16,
    ),
    GPU_PROFILE: EncoderSpec(
        profile=GPU_PROFILE,
        model_id="nvidia/Nemotron-3-Embed-1B-BF16",
        dimension=2048,
        dtype="bfloat16",
        attention="sdpa",
        device="cuda",
        query_prefix="query: ",
        document_prefix="passage: ",
        normalize=True,
        chunking=CHUNKING_TOKEN_WINDOW,
        batch_size=16,
        max_seq_length=4096,
    ),
}

PROFILE_STATUS: dict[str, str] = {DEFAULT_PROFILE: "default", GPU_PROFILE: "spike"}
PROFILE_EXTRA: dict[str, str] = {DEFAULT_PROFILE: MODERN_EXTRA, GPU_PROFILE: GPU_EXTRA}


def custom_spec(model_path: str, revision: str | None = None) -> EncoderSpec:
    """Return the spec of a bare model folder, with the same runtime values as `cpu-default`."""
    base = PROFILES[DEFAULT_PROFILE]
    return replace(
        base, profile=CUSTOM_PROFILE, model_id=model_path, dimension=None, revision=revision
    )


def profile_spec(
    name: str, *, revision: str | None = None, model_digest: str | None = None
) -> EncoderSpec:
    """Return a named profile, with the revision and the model digest set when given."""
    if name not in PROFILES:
        known = ", ".join(sorted(PROFILES))
        raise ValueError(f"unknown encoder profile {name!r}; known profiles: {known}")
    base = PROFILES[name]
    return replace(
        base,
        revision=revision if revision is not None else base.revision,
        model_digest=model_digest if model_digest is not None else base.model_digest,
    )


def encoder_block(unusual: EncoderSpec, wording: EncoderSpec) -> dict[str, Any]:
    """Return the manifest block that names the encoder setup of both pair engines."""
    classes = {unusual.determinism_class(), wording.determinism_class()}
    determinism = (
        DETERMINISM_GPU_APPROX if DETERMINISM_GPU_APPROX in classes else DETERMINISM_CPU_EXACT
    )
    return {
        "schema": ENCODER_BLOCK_SCHEMA,
        "profile": unusual.profile,
        "determinism_class": determinism,
        "unusual_pairs": {"fingerprint": unusual.fingerprint(), "identity": unusual.identity()},
        "wording_and_meaning": {
            "fingerprint": wording.fingerprint(),
            "identity": wording.identity(),
        },
    }
