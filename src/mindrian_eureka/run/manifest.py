"""Build the run manifest and the run-info file for `eureka run`.

The manifest proves what was run: input hashes, record counts, settings, seeds, library
and model versions, and output hashes. It holds no timestamp, no absolute path, no host
name and no user name, so two runs on the same input give the same manifest bytes.
Real times and the manifest hash go to the run-info file.

Importing this module loads no numpy. The thread library loads inside a function.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import platform
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .contracts import LABEL, MANIFEST_SCHEMA, RUN_INFO_SCHEMA, SCORE_MEANING

_BLOCK_SIZE = 1024 * 1024
_SNAPSHOT_NAME = re.compile(r"^[0-9a-f]{40}$")
_CACHE_FOLDER_PREFIX = "models--"

MODEL_FILES: tuple[str, ...] = (
    "config.json",
    "config_sentence_transformers.json",
    "modules.json",
    "sentence_bert_config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.txt",
    "model.safetensors",
    "pytorch_model.bin",
    "1_Pooling/config.json",
)

LIBRARIES: tuple[str, ...] = (
    "numpy",
    "scikit-learn",
    "scipy",
    "sentence-transformers",
    "torch",
    "transformers",
    "tokenizers",
    "huggingface-hub",
    "jsonschema",
    "threadpoolctl",
)

RUN_INFO_NOTE = (
    "Times and the manifest hash are kept in this file, "
    "so the other output files stay identical between runs."
)


def sha256_file(path: Path) -> str:
    """Return the sha256 of a file as lowercase hex, read in blocks of 1 MiB.

    Args:
        path: The file to hash. Symbolic links are followed.

    Returns:
        The hex digest.
    """
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            block = handle.read(_BLOCK_SIZE)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def model_fingerprint(model_dir: Path) -> dict[str, Any]:
    """Describe a local model folder by name, snapshot and file hashes.

    Args:
        model_dir: The model folder.

    Returns:
        A dictionary with "name", "snapshot" and "files". It holds no absolute path.
    """
    folder = model_dir.resolve()
    name = folder.name
    snapshot: str | None = None
    cache_folder = folder.parent.parent.name
    if (
        _SNAPSHOT_NAME.match(folder.name)
        and folder.parent.name == "snapshots"
        and cache_folder.startswith(_CACHE_FOLDER_PREFIX)
    ):
        snapshot = folder.name
        organization, separator, short = cache_folder[len(_CACHE_FOLDER_PREFIX) :].partition("--")
        name = f"{organization}/{short}" if separator else organization
    files: dict[str, str] = {}
    for relative in MODEL_FILES:
        candidate = folder.joinpath(*relative.split("/"))
        if candidate.is_file():
            files[relative] = sha256_file(candidate)
    return {"name": name, "snapshot": snapshot, "files": files}


def _library_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _blas_libraries() -> list[dict[str, Any]]:
    try:
        import threadpoolctl
    except ImportError:
        return []
    found: list[dict[str, Any]] = []
    for item in threadpoolctl.threadpool_info():
        found.append(
            {
                "api": item.get("internal_api"),
                "version": item.get("version"),
                "num_threads": item.get("num_threads"),
            }
        )
    return sorted(found, key=lambda entry: (str(entry["api"]), str(entry["version"])))


def collect_environment(threads_requested: int | None) -> dict[str, Any]:
    """Collect the versions that can change the numbers of a run.

    Args:
        threads_requested: The value of --threads, or None when it was not set.

    Returns:
        A dictionary with Python, platform, library versions and thread library data.
        The file path of each library is not included.
    """
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": f"{sys.platform}-{platform.machine().lower()}",
        "libraries": {name: _library_version(name) for name in LIBRARIES},
        "blas": _blas_libraries(),
        "threads_requested": threads_requested,
    }


def tool_version() -> str:
    """Return the version of the installed `mindrian-eureka` package."""
    try:
        return importlib.metadata.version("mindrian-eureka")
    except importlib.metadata.PackageNotFoundError:
        from mindrian_eureka import __version__

        return str(__version__)


def _plain(value: object) -> Any:
    """Copy mappings and sequences into plain dictionaries and lists."""
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        return [_plain(item) for item in value]
    return value


def build_manifest(
    *,
    engines: Mapping[str, Any],
    inputs: Mapping[str, Any],
    corpus: Mapping[str, Any],
    settings: Mapping[str, Any],
    seeds: Mapping[str, Any],
    model: Mapping[str, Any],
    environment: Mapping[str, Any],
    outputs: Sequence[Mapping[str, Any]],
    engine_notes: Sequence[str],
) -> dict[str, Any]:
    """Build the manifest of a run. The result holds no clock value.

    Args:
        engines: The engine sections (capability ids, versions, tie-break rule, hashes).
        inputs: The input file hashes and the folder digest.
        corpus: The record counts, drops and caps hit.
        settings: The settings of each engine.
        seeds: The seeds of each engine.
        model: The model fingerprint.
        environment: The result of `collect_environment`.
        outputs: One item for each hashed output file, with path, sha256 and bytes.
        engine_notes: Notes from the engines, already sorted by the caller.

    Returns:
        A JSON-ready dictionary.
    """
    ordered = sorted((_plain(item) for item in outputs), key=lambda item: str(item["path"]))
    return {
        "schema_version": MANIFEST_SCHEMA,
        "label": LABEL,
        "score_meaning": {
            "unusual_pairs": SCORE_MEANING["unusual_pairs"],
            "wording_and_meaning": SCORE_MEANING["wording_and_meaning"],
        },
        "tool": {
            "name": "mindrian-eureka",
            "version": tool_version(),
            "engines": _plain(engines),
        },
        "inputs": _plain(inputs),
        "corpus": _plain(corpus),
        "settings": _plain(settings),
        "seeds": _plain(seeds),
        "model": _plain(model),
        "environment": _plain(environment),
        "outputs": ordered,
        "engine_notes": [str(note) for note in engine_notes],
    }


def build_run_info(
    *,
    started_at: str,
    finished_at: str,
    duration_ms: int,
    argv: Sequence[str],
    manifest_sha256: str,
) -> dict[str, Any]:
    """Build the run-info file, which holds the values that change between runs.

    Args:
        started_at: The start time, as text.
        finished_at: The end time, as text.
        duration_ms: The run time in milliseconds.
        argv: The command line arguments, without input contents.
        manifest_sha256: The sha256 of the manifest file.

    Returns:
        A JSON-ready dictionary.
    """
    return {
        "schema_version": RUN_INFO_SCHEMA,
        "label": LABEL,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_ms": duration_ms,
        "argv": list(argv),
        "manifest_sha256": manifest_sha256,
        "note": RUN_INFO_NOTE,
    }
