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

import csv
import io
import json
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
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
    CELL_BLANK,
    CELL_CARRIED,
    CELL_EXPORT_ONLY,
    CELL_TEXT,
    OUTCOME_LICENSED,
    OUTCOME_OPEN,
    PAIR_CLASS_CROSS,
    Record,
    RunError,
    UsageError,
    normalize_text,
    sha256_bytes,
    sha256_text,
)
from .mapping import CsvMapping, MappingConfig, skeleton_mapping
from .textclean import html_to_text, looks_like_html

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
class TextSidecar:
    """A side-car file of text keyed by the raw record id.

    Attributes:
        entries: The text of each id. Ids and texts are normalized.
        sha256: The sha256 of the raw file bytes.
        bytes: The size of the file in bytes.
        records: The number of entries kept.
        id_header: The name of the id column, or `id` for a JSON object.
        skipped: The number of rows with a blank id or a blank text.
    """

    entries: Mapping[str, str]
    sha256: str
    bytes: int
    records: int
    id_header: str
    skipped: int


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
        outcome_classes: The record count of each outcome class, or None without a rule.
        text_coverage: The 4 text coverage counts (`records_total`, `own_text_ok`,
            `filled_from_sidecar`, `still_thin`), or None without a text side-car.
        text_sidecar: The side-car hash, size and match counts, or None without one.
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
    outcome_classes: Mapping[str, int] | None = None
    text_coverage: Mapping[str, int] | None = None
    text_sidecar: Mapping[str, Any] | None = None

    def manifest_inputs(self) -> dict[str, Any]:
        """Return the input section of the manifest as JSON-ready data."""
        data: dict[str, Any] = {
            "files": [
                {"path": item.path, "bytes": item.bytes, "sha256": item.sha256}
                for item in self.input_files
            ],
            "mapping_sha256": self.mapping_sha256,
            "folder_digest": self.folder_digest,
        }
        if self.text_sidecar is not None:
            data["text_sidecar"] = dict(self.text_sidecar)
        return data

    def manifest_corpus(self) -> dict[str, Any]:
        """Return the corpus section of the manifest as JSON-ready data."""
        data: dict[str, Any] = {
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
        if self.outcome_classes is not None:
            data["outcome_classes"] = dict(self.outcome_classes)
        if self.text_coverage is not None:
            data["text_coverage"] = dict(self.text_coverage)
        return data


@dataclass(frozen=True)
class _Candidate:
    """A record before drops, caps and checks.

    `raw_id` is the id cell of a CSV row before the file-stem prefix and before
    sanitizing. It is empty for Markdown records and for hash ids. The text side-car
    joins on it.
    """

    id: str
    title: str
    text: str
    source_ref: str
    source_file: str
    where: str
    outcome_class: str | None = None
    extras: Mapping[str, str] = field(default_factory=dict)
    raw_id: str = ""
    text_source: str | None = None
    room_cells: Mapping[str, str] = field(default_factory=dict)


# --- Discovery --------------------------------------------------------------


def _is_hidden(name: str) -> bool:
    return name.startswith(".") or name in _SKIP_DIR_NAMES


def _discover(
    root: Path, warnings: list[str], *, exclude: Path | None = None
) -> list[tuple[str, Path]]:
    """Return (relative posix path, readable path) for every Markdown and CSV file.

    An entry whose resolved path equals `exclude` (the text side-car) is skipped
    without a warning. The side-car is read once by its own loader, never as input.
    """
    resolved_root = root.resolve()
    excluded = exclude.resolve() if exclude is not None else None
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
            if excluded is not None and not entry.is_dir() and entry.resolve() == excluded:
                continue
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


# --- Text side-car ----------------------------------------------------------

_SIDECAR_TEXT_COLUMN = "text"
_SIDECAR_SUFFIXES = (".csv", ".json")


def _sidecar_csv_pairs(rel: str, text: str) -> tuple[str, list[tuple[str, str]]]:
    """Return the id header and the (id, text) cells of a side-car CSV."""
    old_limit = csv.field_size_limit()
    csv.field_size_limit(MAX_RECORD_CHARS)
    pairs: list[tuple[str, str]] = []
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""), restval="")
        try:
            headers = list(reader.fieldnames or [])
            if not headers:
                raise UsageError(
                    f"The side-car file {rel} is empty",
                    fix=(
                        "Add a header row with the id column first and a "
                        f"{_SIDECAR_TEXT_COLUMN} column"
                    ),
                )
            if _SIDECAR_TEXT_COLUMN not in headers or headers[0] == _SIDECAR_TEXT_COLUMN:
                raise UsageError(
                    f"The side-car file {rel} needs the id in the first column and a column "
                    f"named {_SIDECAR_TEXT_COLUMN}. Headers found: {', '.join(headers)}",
                    fix=f"Put the id column first and name the text column {_SIDECAR_TEXT_COLUMN}",
                )
            id_header = headers[0]
            for row in reader:
                key = row.get(id_header)
                value = row.get(_SIDECAR_TEXT_COLUMN)
                pairs.append(
                    (key if isinstance(key, str) else "", value if isinstance(value, str) else "")
                )
        except csv.Error as exc:
            raise RunError(
                f"The side-car file {rel} cannot be read at line {reader.line_num}: {exc}",
                fix="Check the delimiter and the quotes, or a cell above the size limit",
            ) from exc
    finally:
        csv.field_size_limit(old_limit)
    return id_header, pairs


def _sidecar_json_pairs(rel: str, text: str) -> tuple[str, list[tuple[str, str]]]:
    """Return the id header and the (id, text) items of a side-car JSON object."""
    try:
        document = json.loads(text)
    except ValueError as exc:
        raise UsageError(
            f"The side-car file {rel} is not valid JSON", fix="Save one JSON object of id to text"
        ) from exc
    if not isinstance(document, dict) or not all(
        isinstance(value, str) for value in document.values()
    ):
        raise UsageError(
            f"The side-car file {rel} must hold one JSON object of id string to text string",
            fix='Write the file as {"<id>": "<text>", ...}',
        )
    return "id", list(document.items())


def load_text_sidecar(path: Path) -> TextSidecar:
    """Read a side-car file of text keyed by the raw record id.

    A `.csv` file gives the id in its first column and the text in the column named
    `text`. A `.json` file holds one object of id string to text string. Ids and texts
    are normalized. A row with a blank id or a blank text is skipped and counted.
    Messages carry the file name, header names and counts, never an id or a text.

    Args:
        path: The side-car file. It is only read.

    Returns:
        The entries, the file hash and size, and the counts.

    Raises:
        UsageError: A suffix other than .csv or .json, a CSV without a `text` column,
            or a JSON document that is not an object of strings.
        RunError: A duplicate id, a size limit or a file that cannot be read.
    """
    rel = path.name
    suffix = path.suffix.lower()
    if suffix not in _SIDECAR_SUFFIXES:
        raise UsageError(
            f"The side-car file {rel} is not a .csv or .json file",
            fix=(
                "Give a CSV with the id in the first column and a text column, "
                "or a JSON object of id to text"
            ),
        )
    raw, text = _read_file(rel, path)
    if suffix == ".csv":
        id_header, pairs = _sidecar_csv_pairs(rel, text)
    else:
        id_header, pairs = _sidecar_json_pairs(rel, text)
    entries: dict[str, str] = {}
    duplicates = 0
    skipped = 0
    for raw_key, raw_value in pairs:
        key = normalize_text(raw_key)
        value = normalize_text(raw_value)
        if not key or not value:
            skipped += 1
            continue
        if key in entries:
            duplicates += 1
            continue
        entries[key] = value
    if duplicates:
        raise RunError(
            f"The side-car file {rel} repeats {duplicates} id(s)",
            fix="Keep one row for each id",
        )
    return TextSidecar(
        entries=entries,
        sha256=sha256_bytes(raw),
        bytes=len(raw),
        records=len(entries),
        id_header=id_header,
        skipped=skipped,
    )


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


# --- CSV --------------------------------------------------------------------

_ID_UNSAFE = re.compile(r"[^A-Za-z0-9_.-]+")
_GUESS_DELIMITERS = (",", ";", "\t", "|")
_MAX_EXAMPLES = 5
_EXAMPLE_CHARS = 40


def _guess_headers(text: str) -> tuple[str, list[str]]:
    """Return the best delimiter and the header names of a CSV text."""
    first_line = text.split("\n", 1)[0]
    best: tuple[str, list[str]] = (",", [])
    for delimiter in _GUESS_DELIMITERS:
        try:
            row = next(csv.reader(io.StringIO(first_line, newline=""), delimiter=delimiter), [])
        except csv.Error:
            row = []
        if len(row) > len(best[1]):
            best = (delimiter, row)
    return best


def _unmapped_error(rel: str, text: str) -> UsageError:
    if not text.strip():
        return UsageError(
            f"The CSV file {rel} is empty",
            fix="Remove the file or add a header row and data rows",
        )
    delimiter, headers = _guess_headers(text)
    skeleton_data = json.loads(skeleton_mapping(rel, headers))
    if delimiter != ",":
        skeleton_data["files"][rel]["delimiter"] = delimiter
    skeleton = json.dumps(skeleton_data, indent=2, ensure_ascii=False)
    shown = ", ".join(headers)
    return UsageError(
        f"The CSV file {rel} has no column mapping.\n"
        f"Headers found: {shown}\n"
        "Save this mapping, edit the column names, and run again with --mapping <file>:\n"
        f"{skeleton}",
        fix="Pass --mapping <file>, or pass --text-column <header> (and --id-column <header>)",
    )


def _sanitize_id(value: str) -> str:
    return _ID_UNSAFE.sub("_", value)


def _short(value: str) -> str:
    return value if len(value) <= _EXAMPLE_CHARS else value[:_EXAMPLE_CHARS] + "..."


def _check_headers(rel: str, headers: list[str], entry: CsvMapping) -> None:
    duplicates = sorted({name for name in headers if headers.count(name) > 1})
    if duplicates:
        raise UsageError(
            f"The CSV file {rel} repeats these header names: {', '.join(duplicates)}",
            fix="Make every header name unique",
        )
    wanted = [
        *entry.text_columns,
        *entry.extra_fields,
        *(c for c in (entry.id_column, entry.title_column, entry.source_column) if c),
        *entry.carry_columns,
        *(entry.outcome_rule.columns if entry.outcome_rule is not None else ()),
        *(entry.room_sections.columns if entry.room_sections is not None else ()),
    ]
    missing = [name for name in dict.fromkeys(wanted) if name not in headers]
    if missing:
        raise UsageError(
            f"The CSV file {rel} has no column named {', '.join(missing)}. "
            f"Available headers: {', '.join(headers)}",
            fix="Correct the column names in the mapping",
        )


def _read_csv(
    rel: str, text: str, mapping: MappingConfig | None, warnings: list[str]
) -> list[_Candidate]:
    """Turn one CSV file into candidate records using its mapping."""
    entry = mapping.for_file(rel) if mapping is not None else None
    if entry is None:
        raise _unmapped_error(rel, text)
    id_base = rel[: -len(Path(rel).suffix)]
    unmapped: dict[str, dict[str, int]] = {}
    bad_counts: dict[str, int] = {}

    def cell(row: dict[str | None, Any], column: str) -> str:
        value = row.get(column)
        return value if isinstance(value, str) else ""

    def classify(row: dict[str | None, Any]) -> str | None:
        """Return the outcome class of a row under the mapping rule, or None without one."""
        rule = entry.outcome_rule
        if rule is None:
            return None
        licensed = False
        for condition in rule.conditions:
            value = normalize_text(cell(row, condition.column))
            if condition.equals is not None:
                if value.strip().casefold() == condition.equals.strip().casefold():
                    licensed = True
            elif condition.greater_than is not None:
                number = _whole_number(value)
                if number is None:
                    bad_counts[condition.column] = bad_counts.get(condition.column, 0) + 1
                    number = 0
                if number > condition.greater_than:
                    licensed = True
        return OUTCOME_LICENSED if licensed else OUTCOME_OPEN

    def cell_states(row: dict[str | None, Any], cleaned: Mapping[str, str]) -> dict[str, str]:
        """Return the fill state of each `room_sections` column of a row. No value is kept."""
        block = entry.room_sections
        if block is None:
            return {}
        carried = set(entry.carry_columns)
        states: dict[str, str] = {}
        for column in block.columns:
            value = cleaned[column] if column in cleaned else normalize_text(cell(row, column))
            if not value:
                states[column] = CELL_BLANK
            elif column in carried:
                states[column] = CELL_CARRIED
            elif column in cleaned:
                states[column] = CELL_TEXT
            else:
                states[column] = CELL_EXPORT_ONLY
        return states

    def clean(column: str, raw: str) -> str:
        value = raw
        table = entry.value_maps.get(column)
        if table is not None and value.strip():
            decoded = table.get(value.strip())
            if decoded is None:
                counts = unmapped.setdefault(column, {})
                counts[value.strip()] = counts.get(value.strip(), 0) + 1
            else:
                value = decoded
        if entry.html == "always" or (entry.html == "auto" and looks_like_html(value)):
            value = html_to_text(value)
        return normalize_text(value)

    old_limit = csv.field_size_limit()
    csv.field_size_limit(MAX_RECORD_CHARS)
    candidates: list[_Candidate] = []
    blank_rows = 0
    try:
        reader = csv.DictReader(
            io.StringIO(text, newline=""), delimiter=entry.delimiter, restval=""
        )
        try:
            headers = list(reader.fieldnames or [])
            if not headers:
                raise RunError(f"The CSV file {rel} is empty", fix="Add a header row and data rows")
            _check_headers(rel, headers, entry)
            for row_number, row in enumerate(reader, start=1):
                if not any(
                    isinstance(v, str) and v.strip() for k, v in row.items() if k is not None
                ):
                    blank_rows += 1
                    continue
                where = f"{rel} row {row_number}"
                body_blocks: list[str] = []
                cleaned: dict[str, str] = {}
                for column in entry.text_columns:
                    value = clean(column, cell(row, column))
                    cleaned[column] = value
                    if not value:
                        continue
                    label = entry.labels.get(column)
                    body_blocks.append(f"{label}:\n{value}" if label else value)
                extra_lines: list[str] = []
                for column in entry.extra_fields:
                    value = clean(column, cell(row, column))
                    cleaned[column] = value
                    if value:
                        extra_lines.append(f"{entry.labels.get(column, column)}: {value}")
                if extra_lines:
                    body_blocks.append("\n".join(extra_lines))
                body = "\n\n".join(body_blocks)
                if entry.id_column is not None:
                    raw_id = normalize_text(cell(row, entry.id_column))
                    if not raw_id:
                        raise RunError(
                            f"The id cell is empty in {where}",
                            fix="Fill the id cell, or remove the row",
                        )
                    id_part = _sanitize_id(raw_id)
                    if not id_part.strip("."):
                        raise RunError(
                            f"The id value in {where} has no usable characters",
                            fix="Use an id with letters, digits, underscore, dot or hyphen",
                        )
                else:
                    raw_id = ""
                    id_part = "h" + sha256_text(unicodedata.normalize("NFC", body))[:12]
                title = (
                    clean(entry.title_column, cell(row, entry.title_column))
                    if entry.title_column is not None
                    else ""
                )
                source = (
                    normalize_text(cell(row, entry.source_column))
                    if entry.source_column is not None
                    else ""
                )
                if len(body) > MAX_RECORD_CHARS:
                    raise RunError(
                        f"The text of {where} is longer than {MAX_RECORD_CHARS} characters",
                        fix="Shorten the cell or split the record",
                    )
                outcome_class = classify(row)
                extras = {
                    column: normalize_text(cell(row, column)) for column in entry.carry_columns
                }
                room_cells = cell_states(row, cleaned) if entry.room_sections is not None else {}
                candidates.append(
                    _Candidate(
                        id=unicodedata.normalize("NFC", f"{id_base}/{id_part}"),
                        title=title,
                        text=body,
                        source_ref=source or f"{rel}#{id_part}",
                        source_file=rel,
                        where=where,
                        outcome_class=outcome_class,
                        extras=extras,
                        raw_id=raw_id,
                        room_cells=room_cells,
                    )
                )
        except csv.Error as exc:
            raise RunError(
                f"The CSV file {rel} cannot be read at line {reader.line_num}: {exc}",
                fix="Check the delimiter and the quotes, or a cell above the size limit",
            ) from exc
    finally:
        csv.field_size_limit(old_limit)
    if blank_rows:
        warnings.append(f"Skipped {blank_rows} blank row(s) in {rel}.")
    for column in entry.value_maps:
        counts = unmapped.get(column)
        if counts:
            examples = ", ".join(_short(v) for v in sorted(counts)[:_MAX_EXAMPLES])
            warnings.append(
                f"In {rel}, column {column}: {sum(counts.values())} cell(s) have a value "
                f"that is not in the value map. Examples: {examples}"
            )
    for column in sorted(bad_counts):
        warnings.append(
            f"In {rel}, column {column}: {bad_counts[column]} cell(s) are not whole numbers. "
            "They count as 0."
        )
    return candidates


def _whole_number(value: str) -> int | None:
    """Parse a count cell. Blank is 0. A cell that is not a whole number gives None."""
    text = value.strip()
    if not text:
        return 0
    try:
        return int(text)
    except ValueError:
        return None


def _class_notes(candidates: list[_Candidate], warnings: list[str]) -> dict[str, int] | None:
    """Count the outcome classes and add the plain-English notes on small classes.

    Returns:
        The count of each class, or None when no candidate carries a class.
    """
    classed = [item for item in candidates if item.outcome_class is not None]
    if not classed:
        return None
    counts = {
        OUTCOME_LICENSED: sum(1 for item in classed if item.outcome_class == OUTCOME_LICENSED),
        OUTCOME_OPEN: sum(1 for item in classed if item.outcome_class == OUTCOME_OPEN),
    }
    for name in (OUTCOME_LICENSED, OUTCOME_OPEN):
        if counts[name] < 2:
            warnings.append(
                f"The outcome class {name} holds {counts[name]} record(s). "
                f"No {name}_{name} pair is possible."
            )
    if min(counts.values()) == 0:
        warnings.append(
            f"No {PAIR_CLASS_CROSS} pair is possible. One outcome class holds 0 record(s)."
        )
    return counts


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
                fix=(
                    "Add an id column to the mapping, or remove the duplicate row"
                    if candidate.source_file.lower().endswith(".csv")
                    else "Rename or remove one of the files"
                ),
            )
        seen[candidate.id] = candidate


def build_corpus(
    input_dir: Path,
    *,
    mapping: MappingConfig | None,
    max_artifacts: int = MAX_ARTIFACTS,
    text_sidecar: Path | None = None,
) -> Corpus:
    """Build the clean corpus from an input folder.

    Args:
        input_dir: The folder with Markdown and CSV files. It is only read.
        mapping: The CSV mapping, or None when the input holds no CSV file.
        max_artifacts: The most records to keep. The first ids in sorted order win.
        text_sidecar: A side-car file keyed by the raw record id, or None. Its text is
            added after the own text of a record whose body is under the thin-text
            limit. It is never read as an input file, even inside the input folder.

    Returns:
        The corpus with records sorted by id, the report and the digests.

    Raises:
        UsageError: A bad argument, an empty folder, a CSV without a mapping or a
            side-car in an unknown format.
        RunError: A duplicate id, a size limit, a bad file or too few records.
    """
    _check_arguments(input_dir, max_artifacts)
    warnings: list[str] = []
    sidecar = load_text_sidecar(text_sidecar) if text_sidecar is not None else None
    discovered = _discover(input_dir, warnings, exclude=text_sidecar)
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
    coverage: dict[str, int] = {
        "records_total": 0,
        "own_text_ok": 0,
        "filled_from_sidecar": 0,
        "still_thin": 0,
    }
    matched: set[str] = set()
    for candidate in sorted(candidates, key=lambda item: item.id):
        coverage["records_total"] += 1
        thin_before = len(candidate.text) < MIN_BODY_CHARS
        if sidecar is not None and candidate.raw_id and candidate.raw_id in sidecar.entries:
            matched.add(candidate.raw_id)
            if thin_before:
                extra = sidecar.entries[candidate.raw_id]
                joined = f"{candidate.text}\n\n{extra}".strip() if candidate.text else extra
                candidate = replace(candidate, text=joined, text_source="sidecar")
        if len(candidate.text) < MIN_BODY_CHARS:
            coverage["still_thin"] += 1
            dropped.append(
                Dropped(candidate.id, f"body_under_{MIN_BODY_CHARS}_chars", candidate.source_file)
            )
        else:
            coverage["filled_from_sidecar" if thin_before else "own_text_ok"] += 1
            usable.append(candidate)
    if dropped:
        warnings.append(
            f"Dropped {len(dropped)} record(s) with a body under {MIN_BODY_CHARS} characters. "
            "The ids are listed in the manifest."
        )
    text_coverage: dict[str, int] | None = None
    sidecar_report: dict[str, Any] | None = None
    if sidecar is not None:
        text_coverage = coverage
        unmatched = sidecar.records - len(matched)
        sidecar_report = {
            "sha256": sidecar.sha256,
            "bytes": sidecar.bytes,
            "records": sidecar.records,
            "matched": len(matched),
            "unmatched": unmatched,
        }
        if not any(item.raw_id for item in candidates):
            warnings.append("The side-car matched no record. The input holds no CSV record id.")
        elif unmatched > 0:
            warnings.append(f"{unmatched} side-car id(s) matched no record.")
    with_class = sum(1 for item in usable if item.outcome_class is not None)
    if 0 < with_class < len(usable):
        warnings.append(
            "Records without an outcome class exist next to classed records. "
            "The pair classes are not attached."
        )
        usable = [replace(item, outcome_class=None) for item in usable]
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
    outcome_classes = _class_notes(kept, warnings)

    records = tuple(
        Record(
            id=item.id,
            title=item.title,
            text=item.text,
            source_ref=item.source_ref,
            source_file=item.source_file,
            text_sha256=sha256_text(item.text),
            outcome_class=item.outcome_class,
            extras=dict(item.extras),
            text_source=item.text_source,
            room_cells=dict(item.room_cells),
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
        outcome_classes=outcome_classes,
        text_coverage=text_coverage,
        text_sidecar=sidecar_report,
    )
