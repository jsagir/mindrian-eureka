#!/usr/bin/env python3
"""Compare text encoders on the 36 records of the public example.

For each encoder the harness reports the vector width, the load seconds, the texts for each
second on this computer and the dense top-200 pair overlap with the other encoders. The dense
top-200 is the 200 pairs with the highest cosine among the 630 pairs of the 36 records. The
overlap is the share of the 200 pairs that two encoders share.

The columns are MiniLM (profile `cpu-default`), `mdbr-leaf-ir` and the Nemotron profile.
MiniLM runs on this computer. The `mdbr-leaf-ir` column runs only when its folder loads
offline as a sentence-transformers folder. The Nemotron column needs a GPU computer: the
harness reads the vectors file that the owner-run spike produces (`--vectors-in nemotron=FILE`).
A column that did not run says `not_run` and gives the reason. No number is typed by hand: the
page table is rendered from the log.

The harness makes no network call. It does not install a package and it does not open an ONNX
file. Standard-library imports are at the top; numpy and the Eureka package load inside the
functions that need them.

Encoding rule (the same rule as `scripts/encoder-spike.py`): one model call for all texts, one
vector for each text, no token-window chunking, the model text is the title, a blank line, the
text, stripped, no prefix for MiniLM, rows normalized to length 1 in float32, record order and
record ids as in the corpus file.
"""

from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import os
import platform
import statistics
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

SCHEMA = "eureka.encoder-compare-log.v1"
LABEL = "candidate, not verified"
NOT_RUN = "NOT RUN"
NOT_TIMED = "not timed"
NOT_RECORDED = "not recorded"
START_MARKER = "<!-- compare-table:start -->"
END_MARKER = "<!-- compare-table:end -->"
TOP_K = 200
REPEATS = 3
WARM_UP_TEXTS = 4

COLUMN_NAMES = ("minilm", "mdbr_leaf_ir", "nemotron")
FILE_COLUMNS = ("mdbr_leaf_ir", "nemotron", "minilm")
HEADINGS = {
    "minilm": "MiniLM (cpu-default)",
    "mdbr_leaf_ir": "mdbr-leaf-ir",
    "nemotron": "Nemotron-3-Embed-1B-BF16",
}

SHORT_NAMES = {"minilm": "MiniLM", "mdbr_leaf_ir": "mdbr-leaf-ir", "nemotron": "Nemotron"}

ENCODING_RULE = (
    "One model call for all texts and one vector for each text, with no token-window chunking. "
    "The model text is the title, a blank line, the text, stripped. No prefix for MiniLM. "
    "Rows are normalized to length 1 in float32. Record order and record ids are those of the "
    "corpus file. The model truncates a text at its own window."
)
METRIC = (
    "The dense top-200 is the 200 pairs with the highest cosine among the 630 pairs of the 36 "
    "records. The overlap of two encoders is the share of those 200 pairs that both lists "
    "hold."
)
TIMING_NOTE = (
    "Timings are indicative: other work may run on the computer. The load average of the "
    "computer is recorded before and after each timing."
)
NOT_RUN_NEMOTRON = (
    "The model needs a computer with a GPU, and this session cannot reach one. The "
    "owner-run spike of plan 05-08 produces the vectors file. Give it with "
    "--vectors-in nemotron=FILE."
)

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_REFERENCE_RUN = REPO_ROOT / "examples" / "public-example" / "reference-run"
DEFAULT_RECORDS = DEFAULT_REFERENCE_RUN / "corpus" / "records.jsonl"
DEFAULT_MDBR_DIR = Path("~/.mindrian/model-cache/MongoDB/mdbr-leaf-ir")
DEFAULT_MINILM_VECTORS = REPO_ROOT / "docs" / "encoder-evidence" / "minilm-cpu-vectors.npz"

# (label of the row, key of the value in the column, kind of format)
COLUMN_ROWS: list[tuple[str, str, str]] = [
    ("Status", "status", "status"),
    ("Vector width", "dimension", "int"),
    ("Load time (seconds)", "load_seconds", "float2"),
    ("Texts for each second (indicative)", "texts_per_second", "float2"),
    ("Longest text (tokens)", "max_tokens", "int"),
    ("Model window (tokens)", "window_tokens", "int"),
]
LOAD_ROWS: list[tuple[str, str]] = [
    ("Load average, 1 minute, before the timing", "loadavg_before"),
    ("Load average, 1 minute, after the timing", "loadavg_after"),
]


# --- records, text and pair rules -------------------------------------------------------------


def load_records(path: Path) -> list[dict[str, Any]]:
    """Read the corpus file: one header line, then the records. Refuse a wrong count."""
    header: dict[str, Any] | None = None
    records: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
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
    ids = [item["id"] for item in records]
    if len(set(ids)) != len(ids):
        raise ValueError("The records file holds a repeated id.")
    return records


def model_text(record: Mapping[str, Any]) -> str:
    """The text the model reads: the title, a blank line, the text, stripped."""
    title = record.get("title") or ""
    return f"{title}\n\n{record['text']}".strip()


def pair_key(first: str, second: str) -> str:
    """The pair id that `eureka run` writes."""
    left, right = sorted((first, second))
    digest = hashlib.sha256(f"{left}\0{right}".encode()).hexdigest()
    return f"pair-{digest[:20]}"


# --- dense top pairs and overlap --------------------------------------------------------------


def dense_top_pairs(vectors: Any, ids: Sequence[str], k: int = TOP_K) -> list[str]:
    """Return the keys of the k pairs with the highest cosine, in rank order.

    Rows are normalized in float64. Pairs have i < j. The order is the falling cosine, then
    (i, j). A k larger than the pair count returns all pairs.
    """
    import numpy as np

    matrix = np.asarray(vectors, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0] < 2:
        raise ValueError("At least 2 vectors are needed to form a pair.")
    if matrix.shape[0] != len(ids):
        raise ValueError("The number of vectors differs from the number of ids.")
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    matrix = matrix / norms
    similarity = matrix @ matrix.T
    left, right = np.triu_indices(len(ids), k=1)
    values = similarity[left, right]
    order = np.lexsort((right, left, -values))
    return [pair_key(ids[int(left[i])], ids[int(right[i])]) for i in order[:k]]


def overlap_matrix(tops: Mapping[str, Sequence[str]]) -> dict[str, dict[str, float]]:
    """Return the overlap of each pair of lists, with `ranking_overlap` of the package."""
    from mindrian_eureka.example.check import ranking_overlap

    return {
        left: {right: ranking_overlap(tops[right], tops[left]) for right in tops} for left in tops
    }


# --- the folder probe -------------------------------------------------------------------------


def probe_sentence_folder(path: Path) -> tuple[bool, str]:
    """Say whether a folder can load as a sentence-transformers folder. Load nothing."""
    from mindrian_eureka import models

    folder = Path(path).expanduser()
    if not folder.is_dir():
        return False, "The folder was not found."
    missing = models.missing_files(folder)
    if not missing:
        return True, ""
    reason = "The folder cannot load as a sentence-transformers folder. It lacks " + ", ".join(
        missing
    )
    reason += "."
    weights = any((folder / name).is_file() for name in ("model.safetensors", "pytorch_model.bin"))
    has_onnx = any(folder.rglob("*.onnx"))
    if has_onnx and not weights:
        reason += " The folder holds ONNX files only."
    return False, reason


# --- encoding and timing ----------------------------------------------------------------------


def encode_whole(encoder: Any, texts: Sequence[str]) -> Any:
    """Encode whole texts in one model call (no chunking) and return float32 unit rows."""
    import numpy as np

    vectors = np.asarray(encoder.encode_raw(list(texts)), dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (vectors / norms).astype(np.float32)


def load_average() -> list[float] | None:
    getter = getattr(os, "getloadavg", None)
    if getter is None:
        return None
    try:
        return [round(float(item), 2) for item in getter()]
    except OSError:
        return None


def token_facts(encoder: Any, texts: Sequence[str]) -> tuple[int | None, int | None]:
    """Return (highest token count among the texts, model window), or None when unknown."""
    model = getattr(encoder, "_model", None)
    tokenizer = getattr(model, "tokenizer", None)
    window = getattr(model, "max_seq_length", None)
    if tokenizer is None:
        return None, None
    longest = max(len(tokenizer.encode(text, add_special_tokens=True)) for text in texts)
    return int(longest), int(window) if window is not None else None


def empty_column(status: str, reason: str | None) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "dimension": None,
        "fingerprint": None,
        "load_seconds": None,
        "encode_seconds": None,
        "median_seconds": None,
        "texts_per_second": None,
        "loadavg_before": None,
        "loadavg_after": None,
        "top_pairs_count": None,
        "max_tokens": None,
        "window_tokens": None,
    }


def measure_column(
    encoder: Any, load_seconds: float, texts: Sequence[str], repeats: int
) -> tuple[dict[str, Any], Any]:
    """Time the encoder on the texts and return (column, float32 vectors of the last run)."""
    encode_whole(encoder, texts[:WARM_UP_TEXTS])  # warm-up run, not timed
    before = load_average()
    seconds: list[float] = []
    vectors = None
    for _ in range(max(1, repeats)):
        started = time.perf_counter()
        vectors = encode_whole(encoder, texts)
        seconds.append(time.perf_counter() - started)
    after = load_average()
    median = statistics.median(seconds)
    column = empty_column("run", None)
    spec = getattr(encoder, "spec", None)
    longest, window = token_facts(encoder, texts)
    column.update(
        dimension=int(vectors.shape[1]),
        fingerprint=spec.fingerprint() if spec is not None else None,
        load_seconds=round(float(load_seconds), 4),
        encode_seconds=[round(item, 6) for item in sorted(seconds)],
        median_seconds=round(median, 6),
        texts_per_second=round(len(texts) / median, 4),
        loadavg_before=before,
        loadavg_after=after,
        max_tokens=longest,
        window_tokens=window,
    )
    return column, vectors


def read_vectors_file(path: Path, ids: Sequence[str]) -> tuple[Any, str | None]:
    """Read an npz file with `ids` and `vectors`. Refuse ids that differ from the records."""
    import numpy as np

    with np.load(Path(path), allow_pickle=False) as data:
        file_ids = [str(item) for item in data["ids"]]
        vectors = np.asarray(data["vectors"])
        fingerprint = str(data["fingerprint"]) if "fingerprint" in data.files else None
    for index in range(max(len(file_ids), len(ids))):
        have = file_ids[index] if index < len(file_ids) else None
        want = ids[index] if index < len(ids) else None
        if have != want:
            raise ValueError(
                f"The ids of the vectors file differ from the records at position {index}: "
                f"the file has {have!r}, the records have {want!r}."
            )
    if vectors.ndim != 2 or vectors.shape[0] != len(ids):
        raise ValueError("The vectors file does not hold one row for each record.")
    return vectors, fingerprint


def file_column(vectors: Any, fingerprint: str | None) -> dict[str, Any]:
    column = empty_column("from_file", None)
    column.update(dimension=int(vectors.shape[1]), fingerprint=fingerprint)
    return column


def not_run_mdbr(reason: str) -> dict[str, Any]:
    return empty_column(
        "not_run",
        reason
        + " The harness does not install onnxruntime and does not open the ONNX file.",
    )


def default_make_mdbr(folder: Path) -> tuple[Any, float]:
    """Build the `mdbr-leaf-ir` encoder from a folder that passed the probe."""
    from mindrian_eureka.encoder_spec import custom_spec
    from mindrian_eureka.opportunity_pairs.encoders import make_encoder

    started = time.perf_counter()
    encoder = make_encoder(custom_spec(str(folder)), model_path=str(folder))
    return encoder, time.perf_counter() - started


def finish_log(
    ids: Sequence[str],
    columns: dict[str, dict[str, Any]],
    vectors: Mapping[str, Any],
    *,
    top_k: int,
    recorded_on: str,
    threads: int | None,
    engine_overlap_value: dict[str, float] | None,
) -> dict[str, Any]:
    tops: dict[str, list[str]] = {}
    for name in COLUMN_NAMES:
        if name in vectors:
            tops[name] = dense_top_pairs(vectors[name], ids, top_k)
            columns[name]["top_pairs_count"] = len(tops[name])
    return {
        "schema_version": SCHEMA,
        "label": LABEL,
        "recorded_on": recorded_on,
        "computer": {
            "machine": platform.machine(),
            "cores": os.cpu_count(),
            "system": platform.system(),
        },
        "threads": threads,
        "records": len(ids),
        "pairs": len(ids) * (len(ids) - 1) // 2,
        "top_k": top_k,
        "metric": METRIC,
        "encoding_rule": ENCODING_RULE,
        "columns": columns,
        "overlap": overlap_matrix(tops) if tops else {},
        "engine_overlap": engine_overlap_value,
        "notes": TIMING_NOTE,
    }


def build_log(
    records: Sequence[Mapping[str, Any]],
    *,
    minilm: tuple[Any, float],
    mdbr_dir: Path,
    vectors_in: Mapping[str, Path] | None = None,
    make_mdbr: Callable[[Path], tuple[Any, float]] | None = None,
    repeats: int = REPEATS,
    top_k: int = TOP_K,
    recorded_on: str | None = None,
    threads: int | None = None,
    engine_overlap_value: dict[str, float] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the columns and return (log, vectors for each column that has vectors)."""
    files = dict(vectors_in or {})
    unknown = sorted(set(files) - set(FILE_COLUMNS))
    if unknown:
        raise ValueError(f"Unknown column name for --vectors-in: {unknown[0]}")
    ids = [str(item["id"]) for item in records]
    texts = [model_text(item) for item in records]
    columns: dict[str, dict[str, Any]] = {}
    vectors: dict[str, Any] = {}

    encoder, load_seconds = minilm
    columns["minilm"], vectors["minilm"] = measure_column(encoder, load_seconds, texts, repeats)

    if "mdbr_leaf_ir" in files:
        data, fingerprint = read_vectors_file(files["mdbr_leaf_ir"], ids)
        columns["mdbr_leaf_ir"], vectors["mdbr_leaf_ir"] = file_column(data, fingerprint), data
    else:
        ok, reason = probe_sentence_folder(mdbr_dir)
        if not ok:
            columns["mdbr_leaf_ir"] = not_run_mdbr(reason)
        else:
            builder = make_mdbr or default_make_mdbr
            mdbr_encoder, mdbr_load = builder(Path(mdbr_dir).expanduser())
            columns["mdbr_leaf_ir"], vectors["mdbr_leaf_ir"] = measure_column(
                mdbr_encoder, mdbr_load, texts, repeats
            )

    if "nemotron" in files:
        data, fingerprint = read_vectors_file(files["nemotron"], ids)
        columns["nemotron"], vectors["nemotron"] = file_column(data, fingerprint), data
    else:
        columns["nemotron"] = empty_column("not_run", NOT_RUN_NEMOTRON)

    log = finish_log(
        ids,
        columns,
        vectors,
        top_k=top_k,
        recorded_on=recorded_on or datetime.date.today().isoformat(),
        threads=threads,
        engine_overlap_value=engine_overlap_value,
    )
    return log, vectors


def update_log(
    base: Mapping[str, Any],
    base_vectors: Mapping[str, Any],
    ids: Sequence[str],
    vectors_in: Mapping[str, Path],
    *,
    recorded_on: str | None = None,
) -> dict[str, Any]:
    """Add vectors files to an existing log without any model run.

    The measured columns of the base log keep their timings. A column from a file replaces
    the column of the same name.
    """
    unknown = sorted(set(vectors_in) - {"mdbr_leaf_ir", "nemotron"})
    if unknown:
        raise ValueError(f"Unknown column name for --vectors-in: {unknown[0]}")
    columns = copy.deepcopy(dict(base["columns"]))
    vectors = dict(base_vectors)
    for name, path in vectors_in.items():
        data, fingerprint = read_vectors_file(path, ids)
        columns[name] = file_column(data, fingerprint)
        vectors[name] = data
    return finish_log(
        ids,
        columns,
        vectors,
        top_k=int(base["top_k"]),
        recorded_on=recorded_on or datetime.date.today().isoformat(),
        threads=base.get("threads"),
        engine_overlap_value=base.get("engine_overlap"),
    )


# --- engine-level overlap ---------------------------------------------------------------------


def engine_overlap(run_dir: Path, reference_dir: Path) -> dict[str, float]:
    """Return the pair-id overlap of a finished run folder against the shipped reference run."""
    from mindrian_eureka.example.check import ranking_overlap

    result: dict[str, float] = {}
    for key, name in (
        ("unusual_pairs", "unusual-pairs.json"),
        ("wording_and_meaning", "wording-and-meaning-pairs.json"),
    ):
        run_ids = _pair_ids(Path(run_dir) / name)
        reference_ids = _pair_ids(Path(reference_dir) / name)
        result[key] = ranking_overlap(run_ids, reference_ids)
    return result


def _pair_ids(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [str(item["pair_id"]) for item in data["pairs"]]


# --- the page table ---------------------------------------------------------------------------


def _format(value: Any, kind: str) -> str:
    if kind == "int":
        return str(int(value))
    return f"{float(value):.2f}"


def _cell(column: Mapping[str, Any], key: str, kind: str) -> str:
    status = column["status"]
    if status == "not_run":
        return NOT_RUN
    if kind == "status":
        return "run" if status == "run" else "from file"
    value = column.get(key)
    if value is None:
        return NOT_TIMED if key in ("load_seconds", "texts_per_second") else NOT_RECORDED
    return _format(value, kind)


def _load_cell(column: Mapping[str, Any], key: str) -> str:
    if column["status"] == "not_run":
        return NOT_RUN
    value = column.get(key)
    if not value:
        return NOT_TIMED
    return f"{float(value[0]):.2f}"


def render_table(log: Mapping[str, Any]) -> str:
    """Render the results table. Every number in it comes from the log."""
    columns = log["columns"]
    names = list(COLUMN_NAMES)
    lines = [
        "| Measure | " + " | ".join(HEADINGS[name] for name in names) + " | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for label, key, kind in COLUMN_ROWS:
        cells = [_cell(columns[name], key, kind) for name in names]
        lines.append(f"| {label} | " + " | ".join(cells) + f" | `columns.*.{key}` |")
    for label, key in LOAD_ROWS:
        cells = [_load_cell(columns[name], key) for name in names]
        lines.append(f"| {label} | " + " | ".join(cells) + f" | `columns.*.{key}` |")
    overlap = log.get("overlap", {})
    for target in names:
        cells = []
        for name in names:
            value = overlap.get(name, {}).get(target)
            cells.append(NOT_RUN if value is None else f"{float(value):.4f}")
        label = f"Dense top-200 overlap with {SHORT_NAMES[target]}"
        lines.append(f"| {label} | " + " | ".join(cells) + f" | `overlap.*.{target}` |")
    return "\n".join(lines)


def render_page_text(text: str, log: Mapping[str, Any]) -> str:
    """Return the page text with the table between the two marker lines replaced."""
    lines = text.split("\n")
    starts = [i for i, line in enumerate(lines) if line.strip() == START_MARKER]
    ends = [i for i, line in enumerate(lines) if line.strip() == END_MARKER]
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise ValueError("The page needs exactly one pair of compare-table markers.")
    table = render_table(log).split("\n")
    return "\n".join(lines[: starts[0] + 1] + table + lines[ends[0] :])


# --- files ------------------------------------------------------------------------------------


def write_log(log: Mapping[str, Any], path: Path) -> None:
    text = json.dumps(log, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    Path(path).write_text(text, encoding="utf-8")


def write_vectors(path: Path, ids: Sequence[str], vectors: Any, fingerprint: str | None) -> None:
    import numpy as np

    np.savez_compressed(
        Path(path),
        ids=np.array(list(ids)),
        vectors=np.asarray(vectors, dtype=np.float32),
        fingerprint=np.array(fingerprint or ""),
        encoding_rule=np.array(ENCODING_RULE),
    )


def say(text: str, *, error: bool = False) -> None:
    print(text, file=sys.stderr if error else sys.stdout, flush=True)


def parse_vectors_in(items: Sequence[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for item in items:
        name, separator, raw = item.partition("=")
        name = name.strip().replace("-", "_")
        if not separator or not name or not raw:
            raise ValueError(f"--vectors-in needs NAME=FILE, got {item!r}")
        result[name] = Path(os.path.expanduser(raw))
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="encoder-compare.py",
        description="Compare encoders on the 36 records of the public example. No network call.",
    )
    parser.add_argument("--records", default=str(DEFAULT_RECORDS))
    parser.add_argument("--minilm-dir", help="MiniLM folder (default: the model search).")
    parser.add_argument("--mdbr-dir", default=str(DEFAULT_MDBR_DIR))
    parser.add_argument(
        "--vectors-in",
        action="append",
        default=[],
        metavar="NAME=FILE",
        help="Fill a column from a vectors file (npz with ids and vectors). Repeatable.",
    )
    parser.add_argument("--engine-run", help="A finished `eureka run` folder to compare.")
    parser.add_argument("--repeats", type=int, default=REPEATS)
    parser.add_argument("--top-k", type=int, default=TOP_K)
    parser.add_argument("--threads", type=int, help="Number of CPU threads for torch.")
    parser.add_argument("--out", help="Path of the log file.")
    parser.add_argument("--vectors-out", help="Path of the npz file for the MiniLM vectors.")
    parser.add_argument(
        "--update-log",
        metavar="LOG",
        help="Start from this log and add --vectors-in files. No model is loaded.",
    )
    parser.add_argument(
        "--minilm-vectors",
        default=str(DEFAULT_MINILM_VECTORS),
        help="The saved MiniLM vectors, used with --update-log.",
    )
    parser.add_argument(
        "--render-page",
        metavar="PAGE",
        help="Replace the table of PAGE with the render of the log.",
    )
    return parser


def build_minilm(args: argparse.Namespace) -> tuple[Any, float]:
    from mindrian_eureka import models
    from mindrian_eureka.encoder_spec import profile_spec
    from mindrian_eureka.opportunity_pairs.encoders import make_encoder

    if args.minilm_dir:
        folder: Path | None = Path(args.minilm_dir).expanduser()
    else:
        resolution = models.discover_model()
        if not resolution.ok:
            for line in (*resolution.searched, *resolution.problems):
                say(line, error=True)
            say(models.model_fix_text(), error=True)
            raise SystemExit(2)
        folder = resolution.path
    started = time.perf_counter()
    encoder = make_encoder(profile_spec("cpu-default"), model_path=str(folder))
    return encoder, time.perf_counter() - started


def render_command(page: Path, log_path: Path) -> int:
    log = json.loads(log_path.read_text(encoding="utf-8"))
    if log.get("schema_version") != SCHEMA:
        say(f"The log does not have the schema {SCHEMA}.", error=True)
        return 2
    try:
        page.write_text(render_page_text(page.read_text(encoding="utf-8"), log), encoding="utf-8")
    except (OSError, ValueError) as exc:
        say(f"Cannot render the page: {exc}", error=True)
        return 2
    say(f"Page updated from the log: {page.name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        files = parse_vectors_in(args.vectors_in)
    except ValueError as exc:
        say(str(exc), error=True)
        return 2
    render_only = (
        args.render_page
        and args.out
        and Path(args.out).is_file()
        and not files
        and not args.update_log
        and not args.engine_run
    )
    if render_only:
        return render_command(Path(args.render_page), Path(args.out))
    records = load_records(Path(args.records))
    ids = [str(item["id"]) for item in records]
    reference = DEFAULT_REFERENCE_RUN
    engine = engine_overlap(Path(args.engine_run), reference) if args.engine_run else None

    if args.update_log:
        import numpy as np

        base = json.loads(Path(args.update_log).read_text(encoding="utf-8"))
        minilm_vectors, _fp = read_vectors_file(Path(args.minilm_vectors), ids)
        base_vectors: dict[str, Any] = {"minilm": np.asarray(minilm_vectors)}
        log = update_log(base, base_vectors, ids, files)
        if engine is not None:
            log["engine_overlap"] = engine
    else:
        if args.threads:
            import torch

            torch.set_num_threads(args.threads)
        minilm = build_minilm(args)
        log, vectors = build_log(
            records,
            minilm=minilm,
            mdbr_dir=Path(args.mdbr_dir).expanduser(),
            vectors_in=files,
            repeats=args.repeats,
            top_k=args.top_k,
            threads=args.threads,
            engine_overlap_value=engine,
        )
        if args.vectors_out:
            fingerprint = log["columns"]["minilm"]["fingerprint"]
            write_vectors(Path(args.vectors_out), ids, vectors["minilm"], fingerprint)
            say(f"Vectors written: {Path(args.vectors_out).name}")
    if args.out:
        write_log(log, Path(args.out))
        say(f"Log written: {Path(args.out).name}")
    for name in COLUMN_NAMES:
        column = log["columns"][name]
        say(f"{name}: {column['status']}" + (f" ({column['reason']})" if column["reason"] else ""))
    if args.render_page:
        if not args.out:
            say("--render-page needs --out.", error=True)
            return 2
        return render_command(Path(args.render_page), Path(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
