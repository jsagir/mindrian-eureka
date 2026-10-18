"""Local semantic encoders; model loading is opt-in and network-free by default."""

from __future__ import annotations

from typing import Sequence

import numpy as np


class SentenceTransformerEncoder:
    def __init__(self, model_path: str, *, allow_download: bool = False, revision: str | None = None):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError("Install the optional extra: pip install 'mindrian-eureka[modern-encoder]'") from exc
        self.model_path = model_path
        self.name = "sentence-transformers"
        self.version = f"{model_path}@{revision}" if revision else model_path
        self._model = SentenceTransformer(
            model_path, local_files_only=not allow_download, revision=revision
        )

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        tokenizer = self._model.tokenizer
        limit = max(8, int(self._model.max_seq_length) - 2)
        chunks: list[str] = []
        owners: list[int] = []
        for owner, text in enumerate(texts):
            token_ids = tokenizer.encode(text, add_special_tokens=False)
            segments = [token_ids[i:i + limit] for i in range(0, len(token_ids), limit)] or [[]]
            for segment in segments:
                chunks.append(tokenizer.decode(segment, skip_special_tokens=True))
                owners.append(owner)
        vectors = self._model.encode(
            chunks, convert_to_numpy=True, normalize_embeddings=True,
            show_progress_bar=False, batch_size=16,
        )
        grouped = [[] for _ in texts]
        for owner, vector in zip(owners, vectors):
            grouped[owner].append(vector)
        return np.stack([np.mean(group, axis=0) for group in grouped]).astype(np.float64)


class ReferenceBertEncoder:
    """BERT CLS-per-512-token-segment encoder described in the source analysis."""

    def __init__(self, model_path: str, *, allow_download: bool = False, revision: str | None = None):
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError("Install the optional extra: pip install 'mindrian-eureka[reference-encoder]'") from exc
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

    def encode_segments(self, texts: Sequence[str]) -> list[np.ndarray]:
        output: list[np.ndarray] = []
        torch = self._torch
        for text in texts:
            encoded = self._tokenizer(text, add_special_tokens=False, return_attention_mask=False)["input_ids"]
            chunks = [encoded[i:i + 510] for i in range(0, len(encoded), 510)] or [[]]
            rows: list[np.ndarray] = []
            with torch.inference_mode():
                for chunk in chunks:
                    ids = [self._tokenizer.cls_token_id, *chunk, self._tokenizer.sep_token_id]
                    tensor = torch.tensor([ids], dtype=torch.long)
                    result = self._model(input_ids=tensor)
                    rows.append(result.last_hidden_state[0, 0, :].cpu().numpy())
            output.append(np.stack(rows).astype(np.float64))
        return output

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        """Mean segment vectors for a fast document-level variant."""
        return np.stack([parts.mean(axis=0) for parts in self.encode_segments(texts)])
