"""Read a finished run folder for the opportunity hub.

The reader opens `manifest.json` and four fixed files: the corpus, the two pair files and
the Markdown report. It checks the sha256 of each of them against the manifest before it
trusts a byte. It never opens `run-info.json`: that file holds times and may differ
between runs. A path in the manifest is never used to open a file; only the four fixed
names are.

Import rule: the standard library, `..run.contracts`, `..run.output`, `..run.manifest`,
`..run.project` and `.contracts`. No numpy.
"""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from ..run.contracts import (
    CORPUS_SCHEMA,
    PAIRS_SCHEMA,
    UNUSUAL_PAIRS_NAME,
    WORDING_AND_MEANING_NAME,
    Record,
    RunError,
    UsageError,
    sha256_bytes,
)
from ..run.manifest import sha256_file
from ..run.output import (
    OUTPUT_CORPUS,
    OUTPUT_MANIFEST,
    OUTPUT_MARKDOWN,
    OUTPUT_UNUSUAL,
    OUTPUT_WORDING,
    is_eureka_run_folder,
)
from ..run.project import READING_AGREE, READING_MEANING_HIGHER, READING_WORDING_HIGHER
from .contracts import (
    ENGINE_UNUSUAL,
    ENGINE_WORDING,
    EngineRun,
    RunData,
    RunPair,
    has_internal_name,
)

_FIX_RERUN = "Run eureka run again to rebuild the run folder."

# The hub shows only the reading sentences that a run can produce (D-08).
_READINGS = frozenset({READING_MEANING_HIGHER, READING_WORDING_HIGHER, READING_AGREE})

# Engine key, pair file name and full engine name.
_ENGINE_FILES: tuple[tuple[str, str, str], ...] = (
    (ENGINE_UNUSUAL, OUTPUT_UNUSUAL, UNUSUAL_PAIRS_NAME),
    (ENGINE_WORDING, OUTPUT_WORDING, WORDING_AND_MEANING_NAME),
)


# --- Small checks -----------------------------------------------------------


def _damaged(message: str) -> RunError:
    return RunError(message, fix=_FIX_RERUN)


def _refuse_constant(name: str) -> Any:
    raise ValueError(f"{name} is not allowed in JSON")


def _loads(data: bytes | str, what: str) -> Any:
    try:
        return json.loads(data, parse_constant=_refuse_constant)
    except ValueError as error:
        raise _damaged(f"{what} is not valid JSON") from error


def _mapping(value: object, what: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _damaged(f"{what} is missing or has the wrong shape")
    return value


def _sequence(value: object, what: str) -> list[Any]:
    if not isinstance(value, list):
        raise _damaged(f"{what} is missing or has the wrong shape")
    return value


def _text(value: object, what: str) -> str:
    if not isinstance(value, str):
        raise _damaged(f"{what} is missing or is not text")
    return value


def _number(value: object, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise _damaged(f"{what} is missing or is not a number")
    return float(value)


def _integer(value: object, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _damaged(f"{what} is missing or is not a whole number")
    return value


def _is_safe_relative(path: str) -> bool:
    """Return True for a relative path without "..", as a manifest may list it."""
    if not path or "\0" in path:
        return False
    unified = path.replace("\\", "/")
    if (
        PurePosixPath(unified).is_absolute()
        or PureWindowsPath(path).is_absolute()
        or PureWindowsPath(path).drive
    ):
        return False
    parts = PurePosixPath(unified).parts
    return bool(parts) and ".." not in parts


# --- Manifest and file checks -----------------------------------------------


def _read_manifest(run_dir: Path) -> tuple[dict[str, Any], str]:
    """Return the manifest data and the sha256 of the whole manifest file."""
    if not is_eureka_run_folder(run_dir):
        raise UsageError(
            "this folder is not a finished Eureka run",
            fix="Run eureka run first, then give its output folder to eureka hub.",
        )
    try:
        raw = (run_dir / OUTPUT_MANIFEST).read_bytes()
    except OSError as error:
        raise _damaged(f"{OUTPUT_MANIFEST} cannot be read") from error
    return _mapping(_loads(raw, OUTPUT_MANIFEST), OUTPUT_MANIFEST), sha256_bytes(raw)


def _listed_hashes(manifest: dict[str, Any]) -> dict[str, str]:
    """Return the sha256 that the manifest lists for each safe relative path."""
    listed: dict[str, str] = {}
    for item in _sequence(manifest.get("outputs"), f"the outputs list of {OUTPUT_MANIFEST}"):
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        digest = item.get("sha256")
        if not isinstance(path, str) or not isinstance(digest, str):
            continue
        if not _is_safe_relative(path):
            continue
        if listed.get(path, digest) != digest:
            raise _damaged(f"{OUTPUT_MANIFEST} lists {path} twice with different hashes")
        listed[path] = digest
    return listed


def _expected_hash(name: str, listed: dict[str, str]) -> str:
    expected = listed.get(name)
    if expected is None:
        raise _damaged(f"{OUTPUT_MANIFEST} does not list {name}")
    return expected


def _verify_file(run_dir: Path, name: str, listed: dict[str, str]) -> bytes:
    """Read one fixed file and check its hash. Return the bytes that were hashed."""
    expected = _expected_hash(name, listed)
    try:
        data = run_dir.joinpath(*name.split("/")).read_bytes()
    except OSError as error:
        raise _damaged(f"{name} is missing or cannot be read") from error
    if sha256_bytes(data) != expected:
        raise _damaged(f"{name} does not match the hash in {OUTPUT_MANIFEST}")
    return data


def _verify_only(run_dir: Path, name: str, listed: dict[str, str]) -> None:
    """Check the hash of a file that the hub does not parse."""
    expected = _expected_hash(name, listed)
    try:
        actual = sha256_file(run_dir.joinpath(*name.split("/")))
    except OSError as error:
        raise _damaged(f"{name} is missing or cannot be read") from error
    if actual != expected:
        raise _damaged(f"{name} does not match the hash in {OUTPUT_MANIFEST}")


# --- Corpus -----------------------------------------------------------------


def _read_records(data: bytes) -> tuple[Record, ...]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise _damaged(f"{OUTPUT_CORPUS} is not UTF-8 text") from error
    # Split on LF only. A record text may hold other line separators.
    lines = [line for line in text.split("\n") if line.strip()]
    if not lines:
        raise _damaged(f"{OUTPUT_CORPUS} is empty")
    header = _mapping(_loads(lines[0], OUTPUT_CORPUS), f"the header of {OUTPUT_CORPUS}")
    if header.get("record_type") != "header" or header.get("schema_version") != CORPUS_SCHEMA:
        raise _damaged(f"{OUTPUT_CORPUS} has an unknown schema")
    records: list[Record] = []
    seen: set[str] = set()
    for line in lines[1:]:
        item = _mapping(_loads(line, OUTPUT_CORPUS), f"a line of {OUTPUT_CORPUS}")
        if item.get("record_type") != "record":
            raise _damaged(f"{OUTPUT_CORPUS} holds a line that is not a record")
        record = Record(
            id=_text(item.get("id"), "a record id"),
            title=_text(item.get("title"), "a record title"),
            text=_text(item.get("text"), "a record text"),
            source_ref=_text(item.get("source_ref"), "a record source reference"),
            source_file=_text(item.get("source_file"), "a record source file"),
            text_sha256=_text(item.get("text_sha256"), "a record text hash"),
        )
        if record.id in seen:
            raise _damaged(f"{OUTPUT_CORPUS} holds the record id {record.id} twice")
        seen.add(record.id)
        records.append(record)
    if header.get("record_count") != len(records):
        raise _damaged(f"{OUTPUT_CORPUS} holds a different number of records than its header")
    return tuple(records)


# --- Engines ----------------------------------------------------------------


def _clean_notes(notes: list[Any], file_name: str) -> tuple[tuple[str, ...], int]:
    """Drop the notes that carry an internal name. Return the kept notes and the drop count."""
    kept: list[str] = []
    dropped = 0
    for note in notes:
        text = _text(note, f"a note of {file_name}")
        if has_internal_name(text):
            dropped += 1
        else:
            kept.append(text)
    return tuple(kept), dropped


def _read_pair(engine: str, file_name: str, item: Any, record_ids: set[str]) -> RunPair:
    pair = _mapping(item, f"a pair of {file_name}")
    left = _mapping(pair.get("left"), f"the left record of a pair in {file_name}")
    right = _mapping(pair.get("right"), f"the right record of a pair in {file_name}")
    left_id = _text(left.get("id"), f"a left record id in {file_name}")
    right_id = _text(right.get("id"), f"a right record id in {file_name}")
    if left_id not in record_ids or right_id not in record_ids:
        raise _damaged(f"{file_name} names a record that is not in {OUTPUT_CORPUS}")
    scores = _mapping(pair.get("scores"), f"the scores of a pair in {file_name}")
    percentile = scores.get("percentile")
    reading = _text(pair.get("reading"), f"the reading of a pair in {file_name}")
    if reading not in _READINGS:
        raise _damaged(f"{file_name} holds a reading sentence that the hub does not know")
    return RunPair(
        engine=engine,
        rank=_integer(pair.get("rank"), f"a rank in {file_name}"),
        pair_id=_text(pair.get("pair_id"), f"a pair id in {file_name}"),
        left_id=left_id,
        right_id=right_id,
        wording=_number(scores.get("wording_similarity"), f"a wording score in {file_name}"),
        meaning=_number(scores.get("meaning_similarity"), f"a meaning score in {file_name}"),
        rank_score=_number(scores.get("rank_score"), f"a rank score in {file_name}"),
        percentile=None if percentile is None else _number(percentile, "a percentile"),
        reading=reading,
    )


def _min_percentile(manifest: dict[str, Any], key: str) -> float:
    settings = manifest.get("settings")
    if not isinstance(settings, dict):
        return 0.0
    section = settings.get(key)
    if not isinstance(section, dict) or "min_percentile" not in section:
        return 0.0
    return _number(section["min_percentile"], f"the cut-off of the {key} engine")


def _read_engine(
    key: str,
    file_name: str,
    name: str,
    data: bytes,
    manifest: dict[str, Any],
    record_ids: set[str],
) -> tuple[EngineRun, int]:
    doc = _mapping(_loads(data, file_name), file_name)
    if doc.get("schema_version") != PAIRS_SCHEMA:
        raise _damaged(f"{file_name} has an unknown schema")
    engine = _mapping(doc.get("engine"), f"the engine section of {file_name}")
    if engine.get("name") != name:
        raise _damaged(f"{file_name} does not belong to the engine {name}")
    meanings = _mapping(manifest.get("score_meaning"), f"the score meaning of {OUTPUT_MANIFEST}")
    raw_notes = _sequence(doc.get("notes"), f"the notes of {file_name}")
    notes, dropped = _clean_notes(raw_notes, file_name)
    pairs = tuple(
        _read_pair(key, file_name, item, record_ids)
        for item in _sequence(doc.get("pairs"), f"the pairs of {file_name}")
    )
    counts = _mapping(doc.get("counts"), f"the counts of {file_name}")
    if _integer(counts.get("pairs"), f"the pair count of {file_name}") != len(pairs):
        raise _damaged(f"{file_name} holds a different number of pairs than its counts")
    reached = counts.get("top_k_reached")
    if not isinstance(reached, bool):
        raise _damaged(f"the top-k flag of {file_name} is missing")
    run = EngineRun(
        key=key,
        name=name,
        score_meaning=_text(meanings.get(key), f"the score meaning of the {key} engine"),
        notes=notes,
        min_percentile=_min_percentile(manifest, key),
        top_k=_integer(counts.get("top_k"), f"the top-k value of {file_name}"),
        top_k_reached=reached,
        pairs=pairs,
    )
    return run, dropped


def _dict_items(value: object, what: str) -> tuple[dict[str, Any], ...]:
    return tuple(dict(_mapping(item, what)) for item in _sequence(value, what))


# --- Entry point ------------------------------------------------------------


def load_run(run_dir: Path) -> RunData:
    """Read a finished run folder and check the hash of every file that is read.

    Args:
        run_dir: The output folder of `eureka run`.

    Returns:
        The records, the two engines with their pairs and the corpus report. The values
        are passed through from the files; nothing is scored or recomputed.

    Raises:
        UsageError: The folder is not a finished Eureka run.
        RunError: A file is missing, has the wrong hash or schema, has a wrong shape,
            or a pair holds a reading sentence that a run cannot produce.
    """
    manifest, manifest_sha256 = _read_manifest(run_dir)
    listed = _listed_hashes(manifest)
    corpus_bytes = _verify_file(run_dir, OUTPUT_CORPUS, listed)
    pair_bytes = {name: _verify_file(run_dir, name, listed) for _, name, _ in _ENGINE_FILES}
    _verify_only(run_dir, OUTPUT_MARKDOWN, listed)

    records = _read_records(corpus_bytes)
    record_ids = {record.id for record in records}
    engines: dict[str, EngineRun] = {}
    dropped_notes = 0
    for key, file_name, name in _ENGINE_FILES:
        engine, dropped = _read_engine(
            key, file_name, name, pair_bytes[file_name], manifest, record_ids
        )
        engines[key] = engine
        dropped_notes += dropped

    tool = _mapping(manifest.get("tool"), f"the tool section of {OUTPUT_MANIFEST}")
    corpus = _mapping(manifest.get("corpus"), f"the corpus section of {OUTPUT_MANIFEST}")
    return RunData(
        manifest_sha256=manifest_sha256,
        tool_version=_text(tool.get("version"), "the tool version"),
        records=records,
        engines=engines,
        records_read=_integer(corpus.get("records_read"), "the number of records read"),
        dropped=_dict_items(corpus.get("dropped"), "the dropped records"),
        caps_hit=_dict_items(corpus.get("caps_hit"), "the limits that were reached"),
        dropped_note_count=dropped_notes,
    )
