"""Local semantic encoders; model loading is opt-in and network-free by default."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol, runtime_checkable

import numpy as np

from ..encoder_spec import MODERN_EXTRA, PROFILE_EXTRA, EncoderSpec

_LEGACY_BATCH = 16


@runtime_checkable
class Encoder(Protocol):
    """What the pair engines need from a text encoder."""

    name: str
    version: str
    spec: EncoderSpec | None

    def encode(
        self, texts: Sequence[str], cancel_check: Callable[[], bool] | None = None
    ) -> np.ndarray: ...

    def encode_raw(self, texts: Sequence[str]) -> np.ndarray: ...


class SentenceTransformerEncoder:
    """Sentence-transformers encoder. Without a spec it behaves as it always did."""

    def __init__(
        self,
        model_path: str,
        *,
        allow_download: bool = False,
        revision: str | None = None,
        spec: EncoderSpec | None = None,
    ):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            extra = PROFILE_EXTRA.get(spec.profile, MODERN_EXTRA) if spec else MODERN_EXTRA
            raise RuntimeError(
                f"Install the optional extra: pip install 'mindrian-eureka[{extra}]'"
            ) from exc
        self.model_path = model_path
        self.name = "sentence-transformers"
        self.spec = spec
        self.device = spec.device if spec is not None else None
        if spec is None:
            self.version = f"{model_path}@{revision}" if revision else model_path
            self._model = SentenceTransformer(
                model_path, local_files_only=not allow_download, revision=revision
            )
            return
        revision = revision if revision is not None else spec.revision
        self.version = f"{model_path}@{revision}" if revision else model_path
        load_args: dict[str, Any] = {
            "local_files_only": not allow_download,
            "revision": revision,
            "device": spec.device,
        }
        model_kwargs: dict[str, Any] = {}
        if spec.dtype is not None:
            import torch

            model_kwargs["dtype"] = getattr(torch, spec.dtype)
        if spec.attention is not None:
            model_kwargs["attn_implementation"] = spec.attention
        if model_kwargs:
            load_args["model_kwargs"] = model_kwargs
        # trust_remote_code is never passed. A model that needs remote code fails to load, and
        # that failure is a recorded finding of the spike, not something to switch on.
        self._model = SentenceTransformer(model_path, **load_args)
        if spec.max_seq_length is not None:
            self._model.max_seq_length = spec.max_seq_length
        # The new method name avoids a FutureWarning on current sentence-transformers.
        read_width = getattr(self._model, "get_embedding_dimension", None) or (
            self._model.get_sentence_embedding_dimension
        )
        width = read_width()
        if spec.dimension is not None and width != spec.dimension:
            raise RuntimeError(
                f"The model gives vectors of width {width}, but the profile {spec.profile} "
                f"declares width {spec.dimension}."
            )

    def encode(
        self, texts: Sequence[str], cancel_check: Callable[[], bool] | None = None
    ) -> np.ndarray:
        spec = self.spec
        batch = _LEGACY_BATCH if spec is None else (spec.batch_size or _LEGACY_BATCH)
        normalize = True if spec is None else spec.normalize
        prefix = "" if spec is None else spec.document_prefix
        tokenizer = self._model.tokenizer
        prefix_tokens = len(tokenizer.encode(prefix, add_special_tokens=False)) if prefix else 0
        limit = max(8, int(self._model.max_seq_length) - 2 - prefix_tokens)
        chunks: list[str] = []
        owners: list[int] = []
        for owner, text in enumerate(texts):
            if cancel_check and cancel_check():
                raise RuntimeError("Run cancelled during semantic chunking")
            token_ids = tokenizer.encode(text, add_special_tokens=False)
            segments = [token_ids[i:i + limit] for i in range(0, len(token_ids), limit)] or [[]]
            for segment in segments:
                chunks.append(prefix + tokenizer.decode(segment, skip_special_tokens=True))
                owners.append(owner)
        vector_batches = []
        for start in range(0, len(chunks), batch):
            if cancel_check and cancel_check():
                raise RuntimeError("Run cancelled during semantic embedding")
            vector_batches.append(self._model.encode(
                chunks[start:start + batch], convert_to_numpy=True, normalize_embeddings=normalize,
                show_progress_bar=False, batch_size=batch,
            ))
        vectors = np.concatenate(vector_batches, axis=0)
        grouped: list[list[np.ndarray]] = [[] for _ in texts]
        for owner, vector in zip(owners, vectors, strict=True):
            grouped[owner].append(vector)
        return np.stack([np.mean(group, axis=0) for group in grouped]).astype(np.float64)

    def encode_raw(self, texts: Sequence[str]) -> np.ndarray:
        """Encode whole texts in one model call, with no chunking, cast or normalization."""
        prefix = "" if self.spec is None else self.spec.document_prefix
        items = list(texts) if not prefix else [prefix + text for text in texts]
        return np.asarray(self._model.encode(items, show_progress_bar=False))


def make_encoder(
    spec: EncoderSpec,
    *,
    model_path: str | None = None,
    allow_download: bool = False,
    backend: Callable[..., Any] | None = None,
) -> Encoder:
    """Build an encoder for the spec. This is the one place that picks the backend.

    A spec equal to the bare-folder spec calls the backend with the legacy arguments only.
    Any other spec also passes `spec=`.
    """
    path = spec.model_id if model_path is None else model_path
    build = SentenceTransformerEncoder if backend is None else backend
    if spec.is_legacy_equivalent(path, spec.revision):
        encoder = build(path, allow_download=allow_download, revision=spec.revision)
    else:
        encoder = build(path, allow_download=allow_download, revision=spec.revision, spec=spec)
    return encoder  # type: ignore[no-any-return]


class ReferenceBertEncoder:
    """BERT CLS-per-512-token-segment encoder described in the source analysis."""

    def __init__(
        self, model_path: str, *, allow_download: bool = False, revision: str | None = None
    ):
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "Install the optional extra: pip install 'mindrian-eureka[reference-encoder]'"
            ) from exc
        self.name = "bert_cls_segment_mean"
        self.version = f"{model_path}@{revision}" if revision else model_path
        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(
            model_path, local_files_only=not allow_download, revision=revision
        )
        self._model = AutoModel.from_pretrained(
            model_path, local_files_only=not allow_download, revision=revision
        )
        self._model.eval()

    def encode_segments(
        self, texts: Sequence[str], cancel_check: Callable[[], bool] | None = None
    ) -> list[np.ndarray]:
        output: list[np.ndarray] = []
        torch = self._torch
        for text in texts:
            if cancel_check and cancel_check():
                raise RuntimeError("Run cancelled during reference BERT encoding")
            encoded = self._tokenizer(
                text, add_special_tokens=False, return_attention_mask=False
            )["input_ids"]
            chunks = [encoded[i:i + 510] for i in range(0, len(encoded), 510)] or [[]]
            rows: list[np.ndarray] = []
            with torch.inference_mode():
                for chunk in chunks:
                    if cancel_check and cancel_check():
                        raise RuntimeError("Run cancelled during reference BERT encoding")
                    ids = [self._tokenizer.cls_token_id, *chunk, self._tokenizer.sep_token_id]
                    tensor = torch.tensor([ids], dtype=torch.long)
                    result = self._model(input_ids=tensor)
                    rows.append(result.last_hidden_state[0, 0, :].cpu().numpy())
            output.append(np.stack(rows).astype(np.float64))
        return output

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Mean segment vectors for a fast document-level variant."""
        return np.stack([parts.mean(axis=0) for parts in self.encode_segments(texts)])
