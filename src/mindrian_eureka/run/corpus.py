"""Clean corpus builder for `eureka run`.

The builder reads an input folder (Markdown and CSV files), gives every record a
stable id, normalizes the text, reports every drop and every cap, hashes every
input file and computes the corpus digest for the manifest.

Id rules:
    * Markdown: the relative posix path without the `.md` suffix. A file in the
      root of the input folder gets its stem as id (for example `b.md` gives `b`).
      The reference engine skips root-level files. This is a deliberate difference.
    * CSV: see the CSV section of this module.

The builder is read-only on the input folder. It never follows a directory
symlink and never reads a file symlink that leads outside the folder. Messages
carry ids, file names and counts, never record text.

The module imports no numpy, so importing it is cheap.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..limits import (
    HARD_MAX_ARTIFACTS,
    MAX_ARTIFACTS,
    MAX_INPUT_FILE_BYTES,
    MAX_RECORD_CHARS,
    MAX_TOTAL_TEXT_BYTES,
    MIN_BODY_CHARS,
)
from .contracts import (
    Record,
    RunError,
    UsageError,
    normalize_text,
    sha256_bytes,
    sha256_text,
)
from .mapping import MappingConfig

_SKIP_DIR_NAMES = frozenset({"node_modules"})
_MIN_USABLE_RECORDS = 2
_ENGINE_MIN_RECORDS = 5

_FRONT_MATTER = re.compile(r"\A---\n(?:([\s\S]*?)\n)?---[ \t]*(?:\n|\Z)")
_HEADING = re.compile(r"^# (.+)$", re.MULTILINE)


@dataclass(frozen=True)
class InputFile:
    """One input file that was read.

    Attributes:
        path: The relative posix path inside the input folder.
        bytes: The size of the file in bytes.
        sha256: The sha256 of the raw file bytes.
    """

    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class Dropped:
    """One record that was dropped before ranking.

    Attributes:
        id: The id of the dropped record.
        reason: A short code, for example `body_under_50_chars`.
        source_file: The relative path of the file that held the record.
    """

    id: str
    reason: str
    source_file: str


@dataclass(frozen=True)
class CapHit:
    """A cap that cut the corpus.

    Attributes:
        name: The cap name, for example `max_artifacts`.
        limit: The cap value.
        records_in: The number of records before the cut.
        records_used: The number of records after the cut.
        dropped_count: The number of records the cut removed.
        dropped_ids_sha256: The sha256 of the removed ids joined by newline.
    """

    name: str
    limit: int
    records_in: int
    records_used: int
    dropped_count: int
    dropped_ids_sha256: str


@dataclass(frozen=True)
class Corpus:
    """The clean corpus and its report.

    Attributes:
        records: The records kept, sorted by id, after the cap.
        input_files: Every input file that was read, sorted by path.
        records_read: The number of records found before drops and caps.
        dropped: Records dropped for a short body.
        caps_hit: Caps that cut the corpus.
        warnings: Plain English notes for the user.
        corpus_digest: The sha256 over the id and model text of every record.
        folder_digest: The sha256 over the path and sha256 of every input file.
        mapping_sha256: The sha256 of the mapping that was used, or None.
    """

    records: tuple[Record, ...]
    input_files: tuple[InputFile, ...]
    records_read: int
    dropped: tuple[Dropped, ...]
    caps_hit: tuple[CapHit, ...]
    warnings: tuple[str, ...]
    corpus_digest: str
    folder_digest: str
    mapping_sha256: str | None

    def manifest_inputs(self) -> dict[str, Any]:
        """Return the input section of the manifest as JSON-ready data."""
        return {
            "files": [
                {"path": item.path, "bytes": item.bytes, "sha256": item.sha256}
                for item in self.input_files
            ],
            "mapping_sha256": self.mapping_sha256,
            "folder_digest": self.folder_digest,
        }

    def manifest_corpus(self) -> dict[str, Any]:
        """Return the corpus section of the manifest as JSON-ready data."""
        return {
            "records_read": self.records_read,
            "records_used": len(self.records),
            "dropped": [
                {"id": item.id, "reason": item.reason, "source_file": item.source_file}
                for item in self.dropped
            ],
            "corpus_digest": self.corpus_digest,
            "caps_hit": [
                {
                    "name": hit.name,
                    "limit": hit.limit,
                    "records_in": hit.records_in,
                    "records_used": hit.records_used,
                    "dropped_count": hit.dropped_count,
                    "dropped_ids_sha256": hit.dropped_ids_sha256,
                }
                for hit in self.caps_hit
            ],
        }


@dataclass(frozen=True)
class _Candidate:
    """A record before drops, caps and checks."""

    id: str
    title: str
    text: str
    source_ref: str
    source_file: str
    where: str


# --- Discovery --------------------------------------------------------------


def _is_hidden(name: str) -> bool:
    return name.startswith(".") or name in _SKIP_DIR_NAMES


def _discover(root: Path, warnings: list[str]) -> list[tuple[str, Path]]:
    """Return (relative posix path, readable path) for every Markdown and CSV file."""
    resolved_root = root.resolve()
    found: list[tuple[str, Path]] = []

    def walk(folder: Path) -> None:
        try:
            entries = sorted(folder.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            raise RunError(
                f"Cannot read the folder {folder.name}: {exc.strerror or 'read error'}",
                fix="Check the folder permissions",
            ) from exc
        for entry in entries:
            if _is_hidden(entry.name):
                continue
            rel = entry.relative_to(root).as_posix()
            if entry.is_symlink():
                if entry.is_dir():
                    warnings.append(f"Skipped the folder link {rel}. It is not followed.")
                    continue
                target = entry.resolve()
                if not target.is_file() or not target.is_relative_to(resolved_root):
                    warnings.append(
                        f"Skipped the link {rel}. It does not lead to a file in the input folder."
                    )
                    continue
                if entry.suffix.lower() in (".md", ".csv"):
                    found.append((rel, target))
                continue
            if entry.is_dir():
                walk(entry)
            elif entry.is_file() and entry.suffix.lower() in (".md", ".csv"):
                found.append((rel, entry))

    walk(root)
    found.sort(key=lambda item: item[0])
    return found


def _read_file(rel: str, path: Path) -> tuple[bytes, str]:
    """Read one input file once. Return the raw bytes and the decoded text."""
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise RunError(
            f"Cannot read the file {rel}: {exc.strerror or 'read error'}",
            fix="Check the file permissions",
        ) from exc
    if size > MAX_INPUT_FILE_BYTES:
        raise RunError(
            f"The file {rel} is larger than {MAX_INPUT_FILE_BYTES // (1024 * 1024)} MiB",
            fix="Split the file into smaller files",
        )
    try:
        with path.open("rb") as handle:
            raw = handle.read()
    except OSError as exc:
        raise RunError(
            f"Cannot read the file {rel}: {exc.strerror or 'read error'}",
            fix="Check the file permissions",
        ) from exc
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise RunError(
            f"The file {rel} is not valid UTF-8 text", fix="Save the file as UTF-8"
        ) from exc
    return raw, text


# --- Markdown ---------------------------------------------------------------


def _parse_front_matter(content: str) -> tuple[dict[str, str], str]:
    """Split content into front matter fields and the body."""
    match = _FRONT_MATTER.match(content)
    if match is None:
        return {}, content
    fields: dict[str, str] = {}
    for line in (match.group(1) or "").split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip().strip('"').strip("'")
    return fields, content[match.end() :]


def _title_from_stem(rel: str) -> str:
    return Path(rel).stem.replace("-", " ").replace("_", " ")


def _markdown_candidate(rel: str, text: str) -> _Candidate:
    content = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    fields, body = _parse_front_matter(content)
    title = fields.get("title", "").strip()
    if not title:
        heading = _HEADING.search(body)
        if heading is not None:
            title = heading.group(1).strip()
            lines = body.lstrip("\n").split("\n")
            if lines and lines[0].strip() == heading.group(0).strip():
                body = "\n".join(lines[1:])
    if not title:
        title = _title_from_stem(rel)
    record_id = unicodedata.normalize("NFC", rel[: -len(Path(rel).suffix)])
    return _Candidate(
        id=record_id,
        title=normalize_text(title),
        text=normalize_text(body),
        source_ref=rel,
        source_file=rel,
        where=rel,
    )


# --- CSV (filled in by the CSV step of this plan) ---------------------------


def _read_csv(
    rel: str, text: str, mapping: MappingConfig | None, warnings: list[str]
) -> list[_Candidate]:
    raise NotImplementedError("CSV reading is added in the next step")


# --- Build ------------------------------------------------------------------


def _check_arguments(input_dir: Path, max_artifacts: int) -> None:
    if not input_dir.exists() or not input_dir.is_dir():
        raise UsageError(
            f"The input folder {input_dir.name or str(input_dir)} does not exist",
            fix="Give the path of a folder that holds .md or .csv files",
        )
    if max_artifacts < _MIN_USABLE_RECORDS or max_artifacts > HARD_MAX_ARTIFACTS:
        raise UsageError(
            f"--max-artifacts must be between {_MIN_USABLE_RECORDS} and {HARD_MAX_ARTIFACTS}",
            fix=f"Use a value from {_MIN_USABLE_RECORDS} to {HARD_MAX_ARTIFACTS}",
        )


def _check_duplicates(candidates: list[_Candidate]) -> None:
    seen: dict[str, _Candidate] = {}
    for candidate in candidates:
        first = seen.get(candidate.id)
        if first is not None:
            raise RunError(
                f"Two records have the same id '{candidate.id}': "
                f"{first.where} and {candidate.where}",
                fix="Rename or remove one of the files",
            )
        seen[candidate.id] = candidate


def build_corpus(
    input_dir: Path,
    *,
    mapping: MappingConfig | None,
    max_artifacts: int = MAX_ARTIFACTS,
) -> Corpus:
    """Build the clean corpus from an input folder.

    Args:
        input_dir: The folder with Markdown and CSV files. It is only read.
        mapping: The CSV mapping, or None when the input holds no CSV file.
        max_artifacts: The most records to keep. The first ids in sorted order win.

    Returns:
        The corpus with records sorted by id, the report and the digests.

    Raises:
        UsageError: A bad argument, an empty folder or a CSV without a mapping.
        RunError: A duplicate id, a size limit, a bad file or too few records.
    """
    _check_arguments(input_dir, max_artifacts)
    warnings: list[str] = []
    discovered = _discover(input_dir, warnings)
    if not discovered:
        raise UsageError(
            f"The input folder {input_dir.name} holds no .md or .csv file",
            fix="Add Markdown or CSV files to the folder",
        )

    input_files: list[InputFile] = []
    candidates: list[_Candidate] = []
    for rel, path in discovered:
        raw, text = _read_file(rel, path)
        input_files.append(InputFile(path=rel, bytes=len(raw), sha256=sha256_bytes(raw)))
        if rel.lower().endswith(".csv"):
            candidates.extend(_read_csv(rel, text, mapping, warnings))
        else:
            candidates.append(_markdown_candidate(rel, text))

    _check_duplicates(candidates)
    records_read = len(candidates)

    usable: list[_Candidate] = []
    dropped: list[Dropped] = []
    for candidate in sorted(candidates, key=lambda item: item.id):
        if len(candidate.text) < MIN_BODY_CHARS:
            dropped.append(
                Dropped(candidate.id, f"body_under_{MIN_BODY_CHARS}_chars", candidate.source_file)
            )
        else:
            usable.append(candidate)
    if dropped:
        warnings.append(
            f"Dropped {len(dropped)} record(s) with a body under {MIN_BODY_CHARS} characters. "
            "The ids are listed in the manifest."
        )
    if len(usable) < _MIN_USABLE_RECORDS:
        raise RunError(
            f"Only {len(usable)} usable record(s) found: {records_read} read, "
            f"{len(dropped)} dropped. At least {_MIN_USABLE_RECORDS} are needed",
            fix="Add more records or check the column mapping",
        )
    if len(usable) < _ENGINE_MIN_RECORDS:
        warnings.append(
            f"Only {len(usable)} usable records. The unusual-pairs engine needs at least "
            f"{_ENGINE_MIN_RECORDS} records to return candidates."
        )

    caps_hit: list[CapHit] = []
    kept = usable
    if len(usable) > max_artifacts:
        kept = usable[:max_artifacts]
        removed = [item.id for item in usable[max_artifacts:]]
        caps_hit.append(
            CapHit(
                name="max_artifacts",
                limit=max_artifacts,
                records_in=len(usable),
                records_used=len(kept),
                dropped_count=len(removed),
                dropped_ids_sha256=sha256_text("\n".join(removed)),
            )
        )
        warnings.append(
            f"The collection has {len(usable)} usable records. The cap is {max_artifacts}. "
            f"The first {max_artifacts} ids in sorted order were kept and {len(removed)} were cut."
        )

    records = tuple(
        Record(
            id=item.id,
            title=item.title,
            text=item.text,
            source_ref=item.source_ref,
            source_file=item.source_file,
            text_sha256=sha256_text(item.text),
        )
        for item in kept
    )
    total_bytes = 0
    for record in records:
        model_text = record.model_text
        if len(model_text) > MAX_RECORD_CHARS:
            raise RunError(
                f"The record {record.id} is longer than {MAX_RECORD_CHARS} characters",
                fix="Shorten or split the record",
            )
        total_bytes += len(model_text.encode("utf-8"))
    if total_bytes > MAX_TOTAL_TEXT_BYTES:
        raise RunError(
            "The text of the collection is larger than "
            f"{MAX_TOTAL_TEXT_BYTES // (1024 * 1024)} MiB",
            fix="Use fewer or shorter records",
        )

    corpus_digest = sha256_text(
        "\n".join(f"{record.id}\t{sha256_text(record.model_text)}" for record in records)
    )
    ordered_files = tuple(sorted(input_files, key=lambda item: item.path))
    folder_digest = sha256_text("\n".join(f"{item.path}\t{item.sha256}" for item in ordered_files))
    return Corpus(
        records=records,
        input_files=ordered_files,
        records_read=records_read,
        dropped=tuple(dropped),
        caps_hit=tuple(caps_hit),
        warnings=tuple(warnings),
        corpus_digest=corpus_digest,
        folder_digest=folder_digest,
        mapping_sha256=mapping.sha256 if mapping is not None else None,
    )
