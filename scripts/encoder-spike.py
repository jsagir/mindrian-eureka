#!/usr/bin/env python3
"""GPU spike of nvidia/Nemotron-3-Embed-1B-BF16 on one computer with a CUDA card.

What it measures, for the 36 records of the public example:

- whether the model loads and embeds (bfloat16 with `sdpa` attention first, then bfloat16
  without an attention setting; float32 as the second run);
- the vector width, the maximum sequence length, the load seconds, the peak GPU memory and
  the texts for each second;
- the prefix strings that the model folder defines, and whether they equal the profile
  strings;
- the revision (the commit hash of the downloaded snapshot), the file list of the snapshot,
  and the highest token count among the 36 texts;
- the dense top-200 overlap between the bfloat16 and the float32 vectors;
- optional: the dense top-200 overlap between MiniLM float32 on the GPU and the MiniLM
  vectors that were made on the CPU (`--minilm-dir` and `--cpu-vectors`).

Where to run it: in a scratch virtual environment OUTSIDE the repository, on the GPU
computer. The script refuses an output folder inside the repository. It is self-contained: it
imports only the standard library at module level, and it imports nothing from the Eureka
package. The packages numpy, torch, transformers, sentence-transformers and
huggingface-hub are imported inside functions, so `--help`, `--dry-run` and `--render-doc`
need the standard library alone.

It never enables remote code. A model that needs remote code is recorded as
`needs_remote_code` and the run stops.

It writes only into `--out-dir`: the log `gpu-spike-log.json` and the vectors files. Every
number on the results page is rendered from that log by `--render-doc`. A value that the run
did not produce is shown as `NOT RUN`. The label of every result is "candidate, not verified".
"""

from __future__ import annotations

import argparse
import fnmatch
import gc
import hashlib
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

SCHEMA = "eureka.encoder-spike-log.v1"
LOG_NAME = "gpu-spike-log.json"

# These values equal the `gpu-nemotron` row of the encoder profiles. A test compares them.
MODEL_ID = "nvidia/Nemotron-3-Embed-1B-BF16"
QUERY_PREFIX = "query: "
DOCUMENT_PREFIX = "passage: "
MAX_SEQ_LENGTH = 4096
BATCH_SIZE = 16

TOP_K = 200
REPEATS = 3
MINILM_LABEL = "minilm"
NOT_RUN = "NOT RUN"
START_MARKER = "<!-- spike-table:start -->"
END_MARKER = "<!-- spike-table:end -->"
NO_CUDA_MESSAGE = "No CUDA device was found. This script measures the GPU."

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_RECORDS = (
    SCRIPT_DIR.parent / "examples" / "public-example" / "reference-run" / "corpus" / "records.jsonl"
)

# (dotted path in the log, label of the row, format). The page table has one row for each item.
LOG_FIELDS: list[tuple[str, str, str]] = [
    ("environment.python", "Python version", "str"),
    ("environment.platform", "Operating system", "str"),
    ("environment.torch", "torch version", "str"),
    ("environment.transformers", "transformers version", "str"),
    ("environment.sentence_transformers", "sentence-transformers version", "str"),
    ("environment.numpy", "numpy version", "str"),
    ("environment.cuda_available", "CUDA device found", "bool"),
    ("environment.cuda_runtime", "CUDA runtime version", "str"),
    ("environment.driver", "GPU driver version", "str"),
    ("environment.gpu_name", "GPU name", "str"),
    ("environment.gpu_memory_bytes", "GPU memory (GiB)", "gib"),
    ("model.id", "Model name", "str"),
    ("model.revision", "Resolved revision (snapshot commit hash)", "str"),
    ("model.file_count", "Files in the snapshot", "int"),
    ("model.total_bytes", "Size of the snapshot (GiB)", "gib"),
    ("model.sharded_weights", "Weights in several files", "bool"),
    ("model.error", "Snapshot error", "str"),
    ("load.bf16.ok", "bfloat16 run loads and embeds", "bool"),
    ("load.bf16.seconds", "bfloat16 load time (seconds)", "float2"),
    ("load.bf16.attention_used", "bfloat16 attention setting that worked", "str"),
    ("load.bf16.error", "bfloat16 error", "str"),
    ("load.needs_remote_code", "Model needs remote code", "bool"),
    ("load.fp32.ok", "float32 run loads and embeds", "bool"),
    ("load.fp32.seconds", "float32 load time (seconds)", "float2"),
    ("load.fp32.error", "float32 error", "str"),
    ("embedding.dimension", "Vector width", "int"),
    ("embedding.max_seq_length", "Maximum sequence length of the model (tokens)", "int"),
    ("embedding.prompts", "Prefix strings defined by the model folder", "str"),
    ("embedding.query_prefix_confirmed", "Query prefix equals the profile string", "bool"),
    ("embedding.document_prefix_confirmed", "Document prefix equals the profile string", "bool"),
    ("texts.count", "Texts embedded", "int"),
    ("texts.max_tokens", "Highest token count among the texts", "int"),
    ("speed.bf16.texts_per_second", "bfloat16 texts for each second", "float2"),
    ("speed.fp32.texts_per_second", "float32 texts for each second", "float2"),
    ("memory.bf16.peak_allocated_bytes", "bfloat16 peak GPU memory (GiB)", "gib"),
    ("memory.fp32.peak_allocated_bytes", "float32 peak GPU memory (GiB)", "gib"),
    ("drift.bf16_vs_fp32.top200_overlap", "Top-200 overlap, bfloat16 against float32", "overlap4"),
    (
        "drift.minilm_gpu_vs_cpu.top200_overlap",
        "Top-200 overlap, MiniLM on the GPU against the CPU vectors",
        "overlap4",
    ),
]

_ENVIRONMENT_KEYS = (
    "python",
    "platform",
    "torch",
    "transformers",
    "sentence_transformers",
    "numpy",
    "cuda_available",
    "cuda_runtime",
    "driver",
    "gpu_name",
    "gpu_memory_bytes",
)


# --- the log ---------------------------------------------------------------------------------


def set_path(log: dict[str, Any], dotted: str, value: Any) -> None:
    """Set a value at a dotted path and create the folders of the path as needed."""
    node = log
    parts = dotted.split(".")
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = {}
            node[part] = child
        node = child
    node[parts[-1]] = value


def lookup(log: dict[str, Any], dotted: str) -> Any:
    """Return the value at a dotted path, or None when any part of the path is missing."""
    node: Any = log
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def skeleton_log() -> dict[str, Any]:
    """Return the log of a run that did not happen: every value is None."""
    log: dict[str, Any] = {"schema_version": SCHEMA, "status": "not_run"}
    for dotted, _label, _kind in LOG_FIELDS:
        set_path(log, dotted, None)
    set_path(log, "model.files", None)
    set_path(log, "load.attempts", [])
    set_path(log, "drift.minilm_gpu_vs_cpu.error", None)
    return log


def write_log(log: dict[str, Any], out_dir: Path) -> Path:
    path = out_dir / LOG_NAME
    text = json.dumps(log, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    return path


def clean_error(exc: BaseException, secrets: tuple[str, ...] = ()) -> str:
    """Return a short error text that holds no folder path and no user name."""
    text = f"{type(exc).__name__}: {exc}"
    for secret in sorted((item for item in secrets if item), key=len, reverse=True):
        text = text.replace(secret, "<path>")
    text = re.sub(r"/(?:home|Users)/[^/\s'\"]+", "/<user>", text)
    text = re.sub(r"[A-Za-z]:\\Users\\[^\\\s'\"]+", r"C:\\Users\\<user>", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:400]


# --- records and pairs -----------------------------------------------------------------------


def read_records(path: Path) -> list[dict[str, Any]]:
    """Read the corpus file: one header line, then the records. Refuse a wrong count."""
    header: dict[str, Any] | None = None
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if item.get("record_type") == "header":
            header = item
            continue
        if not isinstance(item.get("id"), str) or not isinstance(item.get("text"), str):
            raise ValueError("A record has no id or no text.")
        records.append(item)
    if header is None:
        raise ValueError("The records file has no header line.")
    if header.get("record_count") != len(records):
        raise ValueError(
            f"The header declares {header.get('record_count')} records, "
            f"but the file holds {len(records)}."
        )
    return records


def model_text(record: dict[str, Any]) -> str:
    """The text the model reads: the title, a blank line, the text, stripped."""
    title = record.get("title") or ""
    return f"{title}\n\n{record['text']}".strip()


def pair_key(first: str, second: str) -> str:
    joined = "\0".join(sorted([first, second]))
    return "pair-" + hashlib.sha256(joined.encode("utf-8")).hexdigest()[:20]


def dense_top_pairs(vectors: Any, ids: list[str], k: int = TOP_K) -> list[str]:
    """Return the keys of the k pairs with the highest cosine, in rank order.

    Pairs have i < j. The order is the falling cosine, then (i, j).
    """
    import numpy as np

    matrix = np.asarray(vectors, dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    matrix = matrix / norms
    similarity = matrix @ matrix.T
    left, right = np.triu_indices(len(ids), k=1)
    values = similarity[left, right]
    order = np.lexsort((right, left, -values))
    return [pair_key(ids[int(left[i])], ids[int(right[i])]) for i in order[:k]]


def overlap(first: list[str], second: list[str]) -> float | None:
    """The share of the keys of `first` that `second` also holds."""
    if not first:
        return None
    return len(set(first) & set(second)) / len(first)


# --- the page ---------------------------------------------------------------------------------


def format_value(value: Any, kind: str) -> str:
    if value is None:
        return NOT_RUN
    if kind == "bool":
        if isinstance(value, bool):
            return "yes" if value else "no"
        return str(value)
    if kind == "int":
        return str(int(value))
    if kind == "float2":
        return f"{float(value):.2f}"
    if kind == "overlap4":
        return f"{float(value):.4f}"
    if kind == "gib":
        return f"{float(value) / 2**30:.2f}"
    return re.sub(r"\s+", " ", str(value)).replace("|", "\\|")


def display_value(log: dict[str, Any], dotted: str, kind: str) -> str:
    value = lookup(log, dotted)
    if value is None and dotted.endswith(".error"):
        parent = dotted[: -len(".error")]
        if parent == "model":
            finished = lookup(log, "model.revision") is not None
        else:
            finished = lookup(log, parent + ".ok") is True
        if finished:
            return "none"
    return format_value(value, kind)


def render_table(log: dict[str, Any]) -> str:
    lines = ["| Measure | Value | Log field |", "| --- | --- | --- |"]
    for dotted, label, kind in LOG_FIELDS:
        lines.append(f"| {label} | {display_value(log, dotted, kind)} | `{dotted}` |")
    return "\n".join(lines)


def render_page_text(text: str, log: dict[str, Any]) -> str:
    """Return the page text with the table block and the front matter status from the log."""
    lines = text.split("\n")
    starts = [i for i, line in enumerate(lines) if line.strip() == START_MARKER]
    ends = [i for i, line in enumerate(lines) if line.strip() == END_MARKER]
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise ValueError("The page needs exactly one pair of spike-table markers.")
    table = render_table(log).split("\n")
    lines = lines[: starts[0] + 1] + table + lines[ends[0] :]
    status = "not_run" if log.get("status") == "not_run" else "recorded"
    if lines and lines[0] == "---":
        try:
            closing = lines.index("---", 1)
        except ValueError:
            closing = 0
        for i in range(1, closing):
            if lines[i].startswith("status:"):
                lines[i] = f"status: {status}"
    return "\n".join(lines)


def render_doc(page: Path, log_path: Path) -> None:
    log = json.loads(log_path.read_text(encoding="utf-8"))
    if log.get("schema_version") != SCHEMA:
        raise ValueError(f"The log does not have the schema {SCHEMA}.")
    text = page.read_text(encoding="utf-8")
    page.write_text(render_page_text(text, log), encoding="utf-8")


# --- the real backend -------------------------------------------------------------------------


class RealBackend:
    """The backend that uses the GPU. All heavy imports happen inside the methods."""

    def environment(self) -> dict[str, Any]:
        import numpy
        import sentence_transformers
        import torch
        import transformers

        info: dict[str, Any] = {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "torch": getattr(torch, "__version__", None),
            "transformers": getattr(transformers, "__version__", None),
            "sentence_transformers": getattr(sentence_transformers, "__version__", None),
            "numpy": getattr(numpy, "__version__", None),
            "cuda_available": bool(torch.cuda.is_available()),
            "cuda_runtime": getattr(torch.version, "cuda", None),
            "driver": None,
            "gpu_name": None,
            "gpu_memory_bytes": None,
        }
        if info["cuda_available"]:
            info["gpu_name"] = torch.cuda.get_device_name(0)
            info["gpu_memory_bytes"] = int(torch.cuda.get_device_properties(0).total_memory)
            try:
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                lines = result.stdout.strip().splitlines()
                if result.returncode == 0 and lines:
                    info["driver"] = lines[0].strip()
            except (OSError, subprocess.SubprocessError):
                info["driver"] = None
        return info

    def snapshot(self, model_id: str, allow_download: bool) -> dict[str, Any]:
        from huggingface_hub import snapshot_download

        path = snapshot_download(model_id, local_files_only=not allow_download)
        folder = Path(path)
        files = []
        for item in sorted(folder.rglob("*")):
            if item.is_file():
                files.append((item.relative_to(folder).as_posix(), item.stat().st_size))
        names = [name for name, _size in files]
        sharded = any(fnmatch.fnmatch(name, "model-*-of-*.safetensors") for name in names) or (
            "model.safetensors.index.json" in names
        )
        return {
            "path": str(folder),
            "revision": folder.name,
            "files": files,
            "sharded_weights": sharded,
        }

    def load(self, model_id: str, path: str, dtype: str, attention: str | None) -> SimpleNamespace:
        import torch
        from sentence_transformers import SentenceTransformer

        model_kwargs: dict[str, Any] = {"dtype": getattr(torch, dtype)}
        if attention is not None:
            model_kwargs["attn_implementation"] = attention
        torch.cuda.synchronize()
        started = time.perf_counter()
        model = SentenceTransformer(
            path, device="cuda", trust_remote_code=False, model_kwargs=model_kwargs
        )
        torch.cuda.synchronize()
        seconds = time.perf_counter() - started
        native = getattr(model, "max_seq_length", None)
        if model_id == MODEL_ID:
            model.max_seq_length = MAX_SEQ_LENGTH
        return SimpleNamespace(
            model=model,
            load_seconds=seconds,
            native_max_seq_length=int(native) if native is not None else None,
        )

    def prompts(self, handle: Any) -> dict[str, str]:
        value = getattr(handle.model, "prompts", None)
        return dict(value) if value else {}

    def embed(
        self, handle: Any, texts: list[str], batch_size: int, repeats: int
    ) -> dict[str, Any]:
        import numpy as np
        import torch

        model = handle.model

        def encode_once() -> Any:
            result = model.encode(
                texts,
                batch_size=batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            torch.cuda.synchronize()
            return result

        encode_once()  # warm-up run, not timed
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()
        seconds = []
        vectors = None
        for _ in range(repeats):
            started = time.perf_counter()
            vectors = encode_once()
            seconds.append(time.perf_counter() - started)
        return {
            "vectors": np.asarray(vectors, dtype=np.float32),
            "seconds": sorted(seconds),
            "peak_allocated_bytes": int(torch.cuda.max_memory_allocated()),
        }

    def max_tokens(self, handle: Any, texts: list[str]) -> int:
        tokenizer = handle.model.tokenizer
        return max(len(tokenizer.encode(text, add_special_tokens=True)) for text in texts)

    def unload(self, handle: Any) -> None:
        import torch

        del handle.model
        gc.collect()
        torch.cuda.empty_cache()


# --- the run ----------------------------------------------------------------------------------


def say(text: str, *, error: bool = False) -> None:
    print(text, file=sys.stderr if error else sys.stdout, flush=True)


def find_repository_root() -> Path | None:
    """Return the repository folder that holds this script, or None for a copied script."""
    for folder in SCRIPT_DIR.parents:
        if (folder / ".git").exists() or (folder / "examples" / "public-example").is_dir():
            return folder
    return None


def check_out_dir(raw: str) -> Path | None:
    """Return the resolved output folder, or None when it lies inside the repository."""
    target = Path(os.path.expanduser(raw)).resolve()
    root = find_repository_root()
    if root is not None and (target == root or root in target.parents):
        say(
            "The output folder must be outside the repository. "
            "Choose another folder with --out-dir.",
            error=True,
        )
        return None
    return target


def needs_remote_code(exc: BaseException) -> bool:
    return "trust_remote_code" in str(exc).lower()


def confirm_prefixes(prompts: dict[str, str] | None) -> tuple[bool | None, bool | None]:
    if not prompts:
        return None, None
    query = prompts.get("query")
    document = prompts.get("document", prompts.get("passage"))
    return (
        None if query is None else query == QUERY_PREFIX,
        None if document is None else document == DOCUMENT_PREFIX,
    )


def record_facts(
    backend: Any, handle: Any, vectors: Any, texts: list[str], log: dict[str, Any]
) -> None:
    """Record the facts that the first working run gives: width, window, prefixes, tokens."""
    if lookup(log, "embedding.dimension") is None:
        set_path(log, "embedding.dimension", int(vectors.shape[1]))
    if lookup(log, "embedding.max_seq_length") is None:
        native = getattr(handle, "native_max_seq_length", None)
        set_path(log, "embedding.max_seq_length", native)
    if lookup(log, "embedding.prompts") is None:
        prompts = backend.prompts(handle)
        query_ok, document_ok = confirm_prefixes(prompts)
        set_path(log, "embedding.prompts", repr(prompts) if prompts is not None else None)
        set_path(log, "embedding.query_prefix_confirmed", query_ok)
        set_path(log, "embedding.document_prefix_confirmed", document_ok)
    if lookup(log, "texts.max_tokens") is None:
        set_path(log, "texts.max_tokens", int(backend.max_tokens(handle, texts)))


def measure(
    backend: Any,
    handle: Any,
    kind: str,
    texts: list[str],
    ids: list[str],
    out_dir: Path,
    log: dict[str, Any],
) -> Any:
    """Embed the texts, record speed and memory, save the vectors, and return them."""
    import numpy as np

    result = backend.embed(handle, texts, BATCH_SIZE, REPEATS)
    vectors = np.asarray(result["vectors"], dtype=np.float32)
    seconds = [float(item) for item in result["seconds"]]
    set_path(log, f"speed.{kind}.texts_per_second", len(texts) / statistics.median(seconds))
    set_path(log, f"memory.{kind}.peak_allocated_bytes", int(result["peak_allocated_bytes"]))
    np.savez(out_dir / f"nemotron-{kind}-vectors.npz", ids=np.array(ids), vectors=vectors)
    record_facts(backend, handle, vectors, texts, log)
    return vectors


def load_bfloat16(
    backend: Any, path: str, log: dict[str, Any], secrets: tuple[str, ...]
) -> tuple[Any, str | None, bool]:
    """Try bfloat16 with `sdpa`, then without an attention setting.

    Return (handle or None, attention label that worked or None, remote code needed).
    """
    attempts = log["load"]["attempts"]
    last_error: str | None = None
    for attention in ("sdpa", None):
        label = attention or "default"
        say(f"Loading {MODEL_ID} in bfloat16 with attention: {label}.")
        try:
            handle = backend.load(MODEL_ID, path, "bfloat16", attention)
        except Exception as exc:  # noqa: BLE001 - every load error is data for the log
            message = clean_error(exc, secrets)
            attempts.append(
                {"dtype": "bfloat16", "attention": label, "ok": False, "error": message}
            )
            last_error = message
            if needs_remote_code(exc):
                set_path(log, "load.bf16.error", message)
                return None, None, True
            continue
        attempts.append({"dtype": "bfloat16", "attention": label, "ok": True, "error": None})
        set_path(log, "load.bf16.seconds", float(handle.load_seconds))
        set_path(log, "load.bf16.attention_used", label)
        return handle, label, False
    set_path(log, "load.bf16.error", last_error)
    return None, None, False


def run_minilm_drift(
    backend: Any,
    args: argparse.Namespace,
    records: list[dict[str, Any]],
    ids: list[str],
    log: dict[str, Any],
    secrets: tuple[str, ...],
) -> bool:
    """Compare MiniLM float32 on the GPU with the CPU vectors. Return True when it worked."""
    import numpy as np

    handle = None
    try:
        with np.load(args.cpu_vectors, allow_pickle=False) as data:
            cpu_ids = [str(item) for item in data["ids"]]
            cpu_vectors = np.asarray(data["vectors"])
        if cpu_ids != ids:
            raise ValueError("The ids in the CPU vectors file differ from the records.")
        say("Loading MiniLM in float32 for the same-model drift run.")
        handle = backend.load(MINILM_LABEL, args.minilm_dir, "float32", None)
        result = backend.embed(handle, [model_text(r) for r in records], BATCH_SIZE, 1)
        gpu_pairs = dense_top_pairs(result["vectors"], ids)
        cpu_pairs = dense_top_pairs(cpu_vectors, ids)
        set_path(log, "drift.minilm_gpu_vs_cpu.top200_overlap", overlap(gpu_pairs, cpu_pairs))
        return True
    except Exception as exc:  # noqa: BLE001
        set_path(log, "drift.minilm_gpu_vs_cpu.error", clean_error(exc, secrets))
        return False
    finally:
        if handle is not None:
            backend.unload(handle)


def finish(log: dict[str, Any], out_dir: Path, status: str, code: int) -> int:
    log["status"] = status
    write_log(log, out_dir)
    say(f"Log written: {out_dir / LOG_NAME}")
    return code


def run_spike(args: argparse.Namespace, backend: Any) -> int:
    out_dir = check_out_dir(args.out_dir)
    if out_dir is None:
        return 2
    if bool(args.minilm_dir) != bool(args.cpu_vectors):
        say("Give --minilm-dir and --cpu-vectors together, or neither.", error=True)
        return 2
    try:
        records = read_records(Path(args.records))
    except (OSError, ValueError) as exc:
        say(f"Cannot use the records file: {exc}", error=True)
        return 2
    ids = [record["id"] for record in records]
    texts = [DOCUMENT_PREFIX + model_text(record) for record in records]
    out_dir.mkdir(parents=True, exist_ok=True)
    log = skeleton_log()
    secrets: tuple[str, ...] = (str(Path.home()), str(out_dir))

    try:
        environment = backend.environment()
    except Exception as exc:  # noqa: BLE001
        say(f"Cannot read the environment: {clean_error(exc, secrets)}", error=True)
        say("Install the packages listed in docs/encoder-spike-results.md first.", error=True)
        return finish(log, out_dir, "not_run", 3)
    for key in _ENVIRONMENT_KEYS:
        if key in environment:
            set_path(log, f"environment.{key}", environment[key])
    if not environment.get("cuda_available"):
        say(NO_CUDA_MESSAGE, error=True)
        return finish(log, out_dir, "not_run", 3)

    set_path(log, "model.id", MODEL_ID)
    try:
        snapshot = backend.snapshot(MODEL_ID, bool(args.allow_download))
    except Exception as exc:  # noqa: BLE001
        message = clean_error(exc, secrets)
        set_path(log, "model.error", message)
        say(f"Cannot get the model files: {message}", error=True)
        if not args.allow_download:
            say("Add --allow-download to fetch the model.", error=True)
        return finish(log, out_dir, "not_run", 3)
    files = list(snapshot["files"])
    set_path(log, "model.revision", snapshot["revision"])
    set_path(log, "model.file_count", len(files))
    set_path(log, "model.total_bytes", sum(int(size) for _name, size in files))
    set_path(log, "model.sharded_weights", bool(snapshot["sharded_weights"]))
    set_path(log, "model.files", [{"name": name, "bytes": int(size)} for name, size in files])
    set_path(log, "texts.count", len(texts))
    path = str(snapshot["path"])
    secrets = (path, *secrets)

    bf16_vectors = None
    fp32_vectors = None

    handle, attention_used, remote = load_bfloat16(backend, path, log, secrets)
    if remote:
        set_path(log, "load.needs_remote_code", True)
        set_path(log, "load.bf16.ok", False)
        say("The model needs remote code. The script never enables it. Run stopped.", error=True)
        return finish(log, out_dir, "partial", 3)
    set_path(log, "load.needs_remote_code", False)
    if handle is None:
        set_path(log, "load.bf16.ok", False)
    else:
        try:
            bf16_vectors = measure(backend, handle, "bf16", texts, ids, out_dir, log)
            set_path(log, "load.bf16.ok", True)
        except Exception as exc:  # noqa: BLE001
            set_path(log, "load.bf16.ok", False)
            set_path(log, "load.bf16.error", clean_error(exc, secrets))
        finally:
            backend.unload(handle)

    fp32_attention = None if attention_used in (None, "default") else attention_used
    fp32_label = fp32_attention or "default"
    say("Loading the model in float32.")
    try:
        handle = backend.load(MODEL_ID, path, "float32", fp32_attention)
    except Exception as exc:  # noqa: BLE001
        message = clean_error(exc, secrets)
        log["load"]["attempts"].append(
            {"dtype": "float32", "attention": fp32_label, "ok": False, "error": message}
        )
        set_path(log, "load.fp32.ok", False)
        set_path(log, "load.fp32.error", message)
    else:
        log["load"]["attempts"].append(
            {"dtype": "float32", "attention": fp32_label, "ok": True, "error": None}
        )
        set_path(log, "load.fp32.seconds", float(handle.load_seconds))
        try:
            fp32_vectors = measure(backend, handle, "fp32", texts, ids, out_dir, log)
            set_path(log, "load.fp32.ok", True)
        except Exception as exc:  # noqa: BLE001
            set_path(log, "load.fp32.ok", False)
            set_path(log, "load.fp32.error", clean_error(exc, secrets))
        finally:
            backend.unload(handle)

    if bf16_vectors is not None and fp32_vectors is not None:
        set_path(
            log,
            "drift.bf16_vs_fp32.top200_overlap",
            overlap(dense_top_pairs(bf16_vectors, ids), dense_top_pairs(fp32_vectors, ids)),
        )

    minilm_ok = True
    if args.minilm_dir:
        minilm_ok = run_minilm_drift(backend, args, records, ids, log, secrets)

    worked = bf16_vectors is not None and fp32_vectors is not None and minilm_ok
    any_run = bf16_vectors is not None or fp32_vectors is not None
    return finish(log, out_dir, "recorded" if worked else "partial", 0 if any_run else 3)


def dry_run(args: argparse.Namespace) -> int:
    out_dir = check_out_dir(args.out_dir)
    if out_dir is None:
        return 2
    say("Dry run. Planned steps:")
    say(f"1. Read the records from {Path(args.records).name}.")
    say("2. Check that a CUDA device exists. Stop if there is none.")
    say(f"3. Find the snapshot of {MODEL_ID} (download only with --allow-download).")
    say("4. Load in bfloat16 with sdpa attention, then without. Embed the texts.")
    say("5. Load in float32. Embed the texts.")
    say("6. Compare the dense top-200 pairs of the two runs.")
    say("7. With --minilm-dir and --cpu-vectors: run the same-model drift check.")
    say("8. Write the log and the vectors files into the output folder.")
    say("No model is loaded and no number is produced.")
    out_dir.mkdir(parents=True, exist_ok=True)
    write_log(skeleton_log(), out_dir)
    say(f"Log written: {out_dir / LOG_NAME}")
    return 0


def render_command(args: argparse.Namespace) -> int:
    log_path = Path(args.log) if args.log else Path(os.path.expanduser(args.out_dir)) / LOG_NAME
    page = Path(args.render_doc)
    try:
        render_doc(page, log_path)
    except (OSError, ValueError) as exc:
        say(f"Cannot render the page: {exc}", error=True)
        return 2
    say(f"Page updated from the log: {page.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="encoder-spike.py",
        description=(
            "Measure nvidia/Nemotron-3-Embed-1B-BF16 on one CUDA computer. Run it in a scratch "
            "virtual environment outside the repository. It never enables remote code."
        ),
    )
    parser.add_argument(
        "--records",
        default=str(DEFAULT_RECORDS),
        help="The corpus file of the 36 records (default: the public example).",
    )
    parser.add_argument(
        "--out-dir",
        default="./encoder-spike-out",
        help="Output folder for the log and the vectors. It must be outside the repository.",
    )
    parser.add_argument(
        "--allow-download",
        action="store_true",
        help="Allow the download of the model files (about 2.3 GB on the first run).",
    )
    parser.add_argument("--minilm-dir", help="Folder of the MiniLM model for the drift run.")
    parser.add_argument("--cpu-vectors", help="The .npz file of MiniLM vectors made on the CPU.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned steps and write a log with no numbers. Loads nothing.",
    )
    parser.add_argument(
        "--render-doc",
        metavar="PAGE",
        help="Fill the results table of PAGE from the log. Uses the standard library only.",
    )
    parser.add_argument(
        "--log", help="The log file to render (default: gpu-spike-log.json in --out-dir)."
    )
    return parser


def main(argv: list[str] | None = None, backend: Any = None) -> int:
    args = build_parser().parse_args(argv)
    if args.render_doc:
        return render_command(args)
    if args.dry_run:
        return dry_run(args)
    return run_spike(args, backend if backend is not None else RealBackend())


if __name__ == "__main__":
    sys.exit(main())
