"""Typed facade over the two ranking engines used by `eureka run`.

The two engines are "Find Unusual Pairs Across a Research Collection" (the
library runner in `opportunity_pairs`) and "Rank Unusual Pairs by Wording and
Meaning" (the reference script `hsi_reference`). This module is the only place
where `eureka run` calls them. Calls into hsi_reference live only in this file.

The facade adds no scoring code. It sets the same options on every call, keeps
the call order of the recorded rebuild, and keeps every run offline.

Importing this module loads only the standard library, `.contracts` and
`..limits`. numpy, scikit-learn and torch load later, inside the functions, so
the caller can set thread limits before they load.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib
import io
import logging
import os
import re
import sys
import warnings
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..limits import MAX_TOP_K
from .contracts import (
    UNUSUAL_PAIRS_CAPABILITY,
    WORDING_AND_MEANING_CAPABILITY,
    Record,
    RunError,
    UsageError,
)

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

Encode = Callable[[list[str]], "NDArray[np.float64]"]
Progress = Callable[[str], None]

RECORDED_PARAMS_HASH = "7affae3c94c6bed9"
TIE_BREAK = "stable descending top-7 term sort (lower term index first on equal values)"
REFERENCE_FILE_NAME = "hsi_reference.py"
WORDING_NOTE_PREFIX = "Wording-and-meaning engine: "

# A fixed stamp keeps the engine output free of the wall clock.
FIXED_COMPUTED_AT = "1970-01-01T00:00:00+00:00"

MODEL_FIX = "Check the model folder with: eureka doctor --load-model"
EXTRA_FIX = "uv sync --extra modern-encoder"

_ENGINE_CODE_PREFIX = re.compile(r"^[A-Z]{2,4}:\s*")


@dataclass(frozen=True)
class UnusualPairsSettings:
    """Settings of the unusual-pairs engine for one run.

    Attributes:
        top_k: The number of pairs the engine returns at most.
        scoring: The scoring mode.
        lex_weight: The weight of the wording signal in the hybrid score.
        min_percentile: The percentile gate for pairs.
        mode: The corpus mode.
        encoder: The encoder name.
        method_version: The version of the meaning method.
        svd_topics_requested: The topic count requested for the wording signal.
        tfidf_max_features: The vocabulary size limit of the wording signal.
        svd_random_state: The seed of the wording signal.
    """

    top_k: int
    scoring: str = "hybrid_2026"
    lex_weight: float = 0.5
    min_percentile: float = 0.90
    mode: str = "local"
    encoder: str = "sentence-transformers"
    method_version: str = "sentence-transformer-chunk-mean-v1"
    svd_topics_requested: int = 80
    tfidf_max_features: int = 2000
    svd_random_state: int = 256


@dataclass(frozen=True)
class WordingSettings:
    """Settings of the wording-and-meaning engine for one run.

    Attributes:
        top_k: The number of pairs the engine returns at most.
        tier: The embedding tier. Tier 1 is the local model.
        ranking: The ranking mode.
        lexical: The wording signal. "hybrid" is the mean of two measures.
        min_percentile: The percentile gate for pairs.
        confirm_percentile: The percentile at which the second signal confirms.
        chunk_words: The words in one chunk of the meaning signal.
        max_chunks: The most chunks for one record.
        seed: The seed of the wording measure.
        model_name: The name of the meaning model.
    """

    top_k: int
    tier: int = 1
    ranking: str = "percentile"
    lexical: str = "hybrid"
    min_percentile: float = 0.0
    confirm_percentile: float = 0.75
    chunk_words: int = 200
    max_chunks: int = 12
    seed: int = 42
    model_name: str = "all-MiniLM-L6-v2"


@dataclass(frozen=True)
class UnusualPairsOutcome:
    """The result of the unusual-pairs engine.

    Attributes:
        result: The full result document of the runner.
        settings: The settings used.
        capability_version: The version of the engine.
    """

    result: dict[str, Any]
    settings: UnusualPairsSettings
    capability_version: str


@dataclass(frozen=True)
class WordingOutcome:
    """The result of the wording-and-meaning engine.

    Attributes:
        pairs: The ranked pairs, exactly as the engine returns them.
        settings: The settings used.
        params_hash: The hash of the settings, in the form the engine records.
        reference_sha256: The sha256 of the reference script file.
        engine_notes: Plain notes that the engine printed. No record text.
    """

    pairs: tuple[dict[str, Any], ...]
    settings: WordingSettings
    params_hash: str
    reference_sha256: str
    engine_notes: tuple[str, ...] = field(default_factory=tuple)


# --- Environment ------------------------------------------------------------


def prepare_offline_environment() -> None:
    """Make model and package loads local only. Call it before any engine import."""
    os.environ["HSI_NO_AUTO_INSTALL"] = "1"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def apply_thread_limits(threads: int | None) -> None:
    """Set the thread count of the numeric libraries.

    Args:
        threads: The thread count, or None to leave the defaults.

    Raises:
        UsageError: If `threads` is below 1.
    """
    if threads is None:
        return
    if threads < 1:
        raise UsageError(
            f"The thread count must be 1 or more. You gave {threads}.",
            fix="Use --threads 1 or a larger number.",
        )
    value = str(threads)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ[name] = value
    torch_module = sys.modules.get("torch")
    if torch_module is not None:
        torch_module.set_num_threads(threads)


def _quiet_model_loggers() -> None:
    """Lower the log level of the model libraries and filter one known warning."""
    for name in ("transformers", "sentence_transformers"):
        logging.getLogger(name).setLevel(logging.ERROR)
    warnings.filterwarnings("ignore", message="Token indices sequence length is longer than")
    try:
        transformers_logging: Any = importlib.import_module("transformers.utils.logging")
    except ImportError:
        return
    transformers_logging.set_verbosity_error()


def load_local_encode(model_dir: Path) -> Encode:
    """Load the meaning model from a local folder and return its encode function.

    Args:
        model_dir: The folder that holds the model files.

    Returns:
        A function that maps a list of texts to a float64 matrix, one row per text.

    Raises:
        RunError: If the package is missing or the folder cannot be loaded.
    """
    prepare_offline_environment()
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RunError(
            "The sentence-transformers package is not installed.", fix=EXTRA_FIX
        ) from exc
    import numpy as numpy_runtime

    _quiet_model_loggers()
    try:
        model = SentenceTransformer(str(model_dir), local_files_only=True)
    except (OSError, ValueError, KeyError) as exc:
        raise RunError(f"The model could not be loaded: {exc}", fix=MODEL_FIX) from exc

    def encode(items: list[str]) -> NDArray[np.float64]:
        return numpy_runtime.asarray(model.encode(list(items), show_progress_bar=False))

    return encode


# --- Unusual-pairs engine ---------------------------------------------------


def run_unusual_pairs(
    records: Sequence[Record],
    *,
    model_dir: Path,
    top_k: int,
    max_artifacts: int,
    cache_path: Path,
    objective: str = "",
    progress: Progress | None = None,
) -> UnusualPairsOutcome:
    """Run the unusual-pairs engine on the records.

    Args:
        records: The clean records, in the order both engines must see.
        model_dir: The local folder of the meaning model.
        top_k: The most pairs to return.
        max_artifacts: The record limit for this run.
        cache_path: The file of the vector cache.
        objective: Free text that the engine records. It is not a scoring signal.
        progress: A function that receives the stage names.

    Returns:
        The outcome with the full result document.

    Raises:
        RunError: If the engine rejects the input or cannot load the model.
    """
    prepare_offline_environment()
    from mindrian_eureka.opportunity_pairs import CAPABILITY_VERSION, runner

    settings = UnusualPairsSettings(top_k=top_k)
    document: dict[str, Any] = {
        "objective": objective,
        "mode": settings.mode,
        "scoring": settings.scoring,
        "artifacts": [
            {
                "id": record.id,
                "title": record.title,
                "text": record.text,
                "source_ref": record.source_ref,
                "corpus": "room",
            }
            for record in records
        ],
    }
    try:
        runner.validate_document(document, max_artifacts=max_artifacts)
        result = runner.run_document(
            document,
            encoder_name=settings.encoder,
            model_path=str(model_dir),
            allow_model_download=False,
            top_k=top_k,
            scoring=settings.scoring,
            lex_weight=settings.lex_weight,
            min_percentile=settings.min_percentile,
            cache_path=cache_path,
            stage_callback=progress,
        )
    except ValueError as exc:
        raise RunError(str(exc)) from exc
    except (OSError, RuntimeError) as exc:
        raise RunError(f"The unusual-pairs engine stopped: {exc}", fix=MODEL_FIX) from exc
    return UnusualPairsOutcome(
        result=result, settings=settings, capability_version=CAPABILITY_VERSION
    )


# --- Wording-and-meaning engine ---------------------------------------------

_reference_module: Any = None
_reference_notes: tuple[str, ...] = ()
_reference_sha256: str = ""


def _plain_lines(text: str) -> list[str]:
    """Split captured engine output into plain lines with the engine code replaced."""
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        lines.append(WORDING_NOTE_PREFIX + _ENGINE_CODE_PREFIX.sub("", line))
    return lines


def _reference() -> Any:
    """Import the reference script once, offline, and keep its import-time notes."""
    global _reference_module, _reference_notes, _reference_sha256
    if _reference_module is None:
        prepare_offline_environment()
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            module: Any = importlib.import_module("mindrian_eureka.hsi_reference")
        _reference_notes = tuple(_plain_lines(buffer.getvalue()))
        _reference_sha256 = hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
        _reference_module = module
    return _reference_module


def wording_params(top_k: int) -> dict[str, Any]:
    """Return the settings dictionary that the reference script records for a run.

    The keys and values equal the dictionary in `hsi_reference.main` for
    `--tier 1 --top-k <top_k>` with every other option at its default.

    Args:
        top_k: The most pairs to return.

    Returns:
        The settings dictionary.
    """
    reference = _reference()
    settings = WordingSettings(top_k=top_k)
    return {
        "tier": settings.tier,
        "threshold": None,
        "ranking": settings.ranking,
        "lexical": settings.lexical,
        "top_k": settings.top_k,
        "min_percentile": settings.min_percentile,
        "confirm_percentile": settings.confirm_percentile,
        "claim_level": False,
        "dense_vectors": None,
        "model": settings.model_name,
        "seed": settings.seed,
        "chunking": True,
        "allow_lexical_only": False,
        "schema_version": reference.SCHEMA_VERSION,
        "pinecone": False,
    }


def wording_params_hash(top_k: int) -> str:
    """Return the hash that the reference script records for the settings."""
    reference = _reference()
    return str(reference.params_fingerprint(wording_params(top_k)))


def _call_captured(
    progress: Progress | None, func: Callable[..., Any], *args: Any, **kwargs: Any
) -> Any:
    """Call `func` with stderr captured. Send each captured line to `progress`."""
    buffer = io.StringIO()
    with contextlib.redirect_stderr(buffer):
        value = func(*args, **kwargs)
    if progress is not None:
        for line in _plain_lines(buffer.getvalue()):
            progress(line)
    return value


def run_wording_and_meaning(
    records: Sequence[Record],
    *,
    encode: Encode,
    top_k: int,
    progress: Progress | None = None,
) -> WordingOutcome:
    """Run the wording-and-meaning engine as the recorded rebuild.

    The calls follow the order of `hsi_reference.main`: wording by LSA, wording by
    BM25, the mean of both, the meaning signal in 200-word chunks, then the ranking.

    Args:
        records: The clean records, in the order both engines must see.
        encode: The function that turns texts into vectors.
        top_k: The most pairs to return.
        progress: A function that receives plain progress lines.

    Returns:
        The outcome with the pairs in engine order.

    Raises:
        UsageError: If `top_k` is outside 0 to the shared limit.
        RunError: If there are fewer than 2 records or the meaning signal is empty.
    """
    if top_k < 0 or top_k > MAX_TOP_K:
        raise UsageError(
            f"The pair count must be between 0 and {MAX_TOP_K}. You gave {top_k}.",
            fix=f"Use --top-k with a number from 0 to {MAX_TOP_K}.",
        )
    if len(records) < 2:
        raise RunError(
            "The wording-and-meaning engine needs at least 2 records.",
            fix="Add more input files or records.",
        )
    reference = _reference()
    settings = WordingSettings(top_k=top_k)
    texts = [record.model_text for record in records]
    artifacts = [
        {
            "id": record.id,
            "text": record.model_text,
            "title": record.title,
            "section": "",
            "path": record.source_ref,
            "content_hash": record.text_sha256,
        }
        for record in records
    ]
    lsa = _call_captured(progress, reference.compute_lsa_similarity, texts, seed=settings.seed)
    bm25 = _call_captured(progress, reference.compute_bm25_similarity, texts)
    lexical = 0.5 * (lsa + bm25)
    semantic = _call_captured(
        progress,
        reference.compute_semantic_similarity_tier1,
        texts,
        encoder=encode,
        chunk_words=settings.chunk_words,
    )
    if semantic is None:
        raise RunError("The meaning signal could not be computed.", fix=MODEL_FIX)
    pairs, _profiles = _call_captured(
        progress,
        reference.compute_hsi_matrix,
        artifacts,
        lsa,
        semantic,
        threshold=None,
        lexical_matrix=lexical,
        bm25_matrix=bm25,
        ranking=settings.ranking,
        top_k=settings.top_k,
        min_percentile=settings.min_percentile,
        confirm_percentile=settings.confirm_percentile,
        computed_at=FIXED_COMPUTED_AT,
    )
    return WordingOutcome(
        pairs=tuple(pairs),
        settings=settings,
        params_hash=str(reference.params_fingerprint(wording_params(top_k))),
        reference_sha256=_reference_sha256,
        engine_notes=_reference_notes,
    )


# --- Manifest ---------------------------------------------------------------


def manifest_engine_sections(
    unusual: UnusualPairsOutcome, wording: WordingOutcome
) -> dict[str, Any]:
    """Return the manifest sections that describe the engines, settings and seeds.

    Args:
        unusual: The outcome of the unusual-pairs engine.
        wording: The outcome of the wording-and-meaning engine.

    Returns:
        A dictionary with the keys "engines", "settings", "seeds" and "engine_notes".
    """
    return {
        "engines": {
            "unusual_pairs": {
                "capability_id": UNUSUAL_PAIRS_CAPABILITY,
                "capability_version": unusual.capability_version,
                "scoring": unusual.settings.scoring,
                "method_version": unusual.settings.method_version,
                "tie_break": TIE_BREAK,
            },
            "wording_and_meaning": {
                "capability_id": WORDING_AND_MEANING_CAPABILITY,
                "reference": REFERENCE_FILE_NAME,
                "reference_sha256": wording.reference_sha256,
                "params_hash": wording.params_hash,
            },
        },
        "settings": {
            "unusual_pairs": asdict(unusual.settings),
            "wording_and_meaning": asdict(wording.settings),
        },
        "seeds": {
            "unusual_pairs_svd_random_state": unusual.settings.svd_random_state,
            "wording_and_meaning_lsa_seed": wording.settings.seed,
        },
        "engine_notes": sorted(set(wording.engine_notes)),
    }
