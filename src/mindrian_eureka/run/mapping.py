"""CSV column mapping for `eureka run`.

A mapping tells the corpus builder which CSV columns hold the record id, the
title and the text. It comes from a small JSON file or from command line flags,
so new partner headers need no code change.

The module imports only the standard library, jsonschema and the run contracts.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Literal, cast

from jsonschema import Draft202012Validator

from .contracts import MAPPING_SCHEMA, UsageError, sha256_bytes, sha256_text

MAX_MAPPING_FILE_BYTES: Final[int] = 1024 * 1024
MAX_SHOWN_PROBLEMS: Final[int] = 5

HtmlMode = Literal["auto", "always", "never"]

_NAME = {"type": "string", "minLength": 1}

_ENTRY_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "required": ["text_columns"],
    "additionalProperties": False,
    "properties": {
        "text_columns": {
            "type": "array",
            "items": _NAME,
            "minItems": 1,
            "uniqueItems": True,
        },
        "id_column": _NAME,
        "title_column": _NAME,
        "source_column": _NAME,
        "delimiter": {"type": "string", "minLength": 1, "maxLength": 1},
        "labels": {"type": "object", "additionalProperties": {"type": "string"}},
        "extra_fields": {"type": "array", "items": _NAME, "uniqueItems": True},
        "value_maps": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "additionalProperties": {"type": "string"},
            },
        },
        "html": {"enum": ["auto", "always", "never"]},
    },
}

MAPPING_JSON_SCHEMA: Final[dict[str, Any]] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["schema_version", "files"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"const": MAPPING_SCHEMA},
        "files": {
            "type": "object",
            "minProperties": 1,
            "additionalProperties": _ENTRY_SCHEMA,
        },
    },
}


@dataclass(frozen=True)
class CsvMapping:
    """How to read one CSV file.

    Attributes:
        text_columns: Headers whose cells form the record text, in order.
        id_column: Header of the record id, or None to hash the text.
        title_column: Header of the title, or None.
        source_column: Header of the source reference, or None.
        delimiter: The one-character field separator.
        labels: Header to label text for the text columns and extra fields.
        extra_fields: Headers appended to the text as `label: value` lines.
        value_maps: Header to a map from coded cell values to plain text.
        html: Whether to clean HTML in cells: auto, always or never.
    """

    text_columns: tuple[str, ...]
    id_column: str | None = None
    title_column: str | None = None
    source_column: str | None = None
    delimiter: str = ","
    labels: Mapping[str, str] = field(default_factory=dict)
    extra_fields: tuple[str, ...] = ()
    value_maps: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    html: HtmlMode = "auto"


@dataclass(frozen=True)
class MappingConfig:
    """A set of CSV mappings.

    Attributes:
        files: Relative file path (or "*" for every CSV file) to its mapping.
        sha256: The sha256 that identifies this mapping in the manifest.
    """

    files: Mapping[str, CsvMapping]
    sha256: str

    def for_file(self, rel_path: str) -> CsvMapping | None:
        """Return the mapping for a CSV file.

        Args:
            rel_path: The relative posix path of the CSV file.

        Returns:
            The entry with the exact key, else the "*" entry, else None.
        """
        exact = self.files.get(rel_path)
        if exact is not None:
            return exact
        return self.files.get("*")


def _entry_from_data(data: Mapping[str, Any]) -> CsvMapping:
    """Build a CsvMapping from validated JSON data."""
    return CsvMapping(
        text_columns=tuple(data["text_columns"]),
        id_column=data.get("id_column"),
        title_column=data.get("title_column"),
        source_column=data.get("source_column"),
        delimiter=data.get("delimiter", ","),
        labels=dict(data.get("labels", {})),
        extra_fields=tuple(data.get("extra_fields", ())),
        value_maps={key: dict(val) for key, val in data.get("value_maps", {}).items()},
        html=cast(HtmlMode, data.get("html", "auto")),
    )


def _json_path(error: Any) -> str:
    parts = [str(part) for part in error.absolute_path]
    return "/".join(parts) if parts else "(top level)"


def load_mapping_file(path: Path) -> MappingConfig:
    """Load and validate a mapping file.

    Args:
        path: The mapping JSON file.

    Returns:
        The mapping. Its sha256 is the sha256 of the file bytes.

    Raises:
        UsageError: The file is missing, too large, not JSON, or not valid.
    """
    name = path.name
    help_fix = "Run `eureka run --help` to see the mapping file shape"
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise UsageError(
            f"Cannot read the mapping file {name}: {exc.strerror or 'read error'}",
            fix="Check the path of the --mapping file",
        ) from exc
    if size > MAX_MAPPING_FILE_BYTES:
        raise UsageError(
            f"The mapping file {name} is larger than 1 MiB",
            fix="Use a smaller mapping file",
        )
    raw = path.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except UnicodeDecodeError as exc:
        raise UsageError(
            f"The mapping file {name} is not UTF-8 text",
            fix="Save the mapping file as UTF-8",
        ) from exc
    except json.JSONDecodeError as exc:
        raise UsageError(
            f"The mapping file {name} is not valid JSON: {exc.msg} at line {exc.lineno}",
            fix=help_fix,
        ) from exc
    validator = Draft202012Validator(MAPPING_JSON_SCHEMA)
    errors = sorted(validator.iter_errors(data), key=lambda e: (_json_path(e), e.message))
    if errors:
        shown = errors[:MAX_SHOWN_PROBLEMS]
        lines = "; ".join(f"{_json_path(e)}: {e.message}" for e in shown)
        more = len(errors) - len(shown)
        suffix = f" (and {more} more)" if more > 0 else ""
        raise UsageError(
            f"The mapping file {name} has {len(errors)} problem(s): {lines}{suffix}",
            fix=help_fix,
        )
    files = {key: _entry_from_data(value) for key, value in data["files"].items()}
    return MappingConfig(files=files, sha256=sha256_bytes(raw))


def mapping_from_flags(
    *,
    id_column: str | None,
    title_column: str | None,
    text_columns: Sequence[str],
    source_column: str | None,
    delimiter: str | None,
) -> MappingConfig | None:
    """Build a one-entry mapping from command line flags.

    Args:
        id_column: Value of --id-column, or None.
        title_column: Value of --title-column, or None.
        text_columns: Values of --text-column (may repeat).
        source_column: Value of --source-column, or None.
        delimiter: Value of --delimiter, or None.

    Returns:
        A mapping with the single key "*", or None when no flag is set.

    Raises:
        UsageError: A column flag is set without a text column, or the
            delimiter is not one character.
    """
    columns = tuple(text_columns)
    others_set = any(
        value for value in (id_column, title_column, source_column, delimiter)
    )
    if not columns:
        if others_set:
            raise UsageError(
                "--id-column, --title-column, --source-column and --delimiter "
                "need at least one --text-column",
                fix="Add --text-column <header>",
            )
        return None
    if len(set(columns)) != len(columns):
        raise UsageError(
            "A --text-column header is given more than once",
            fix="Give each --text-column header one time",
        )
    if delimiter is not None and len(delimiter) != 1:
        raise UsageError(
            "--delimiter must be exactly one character",
            fix="Use for example --delimiter ';'",
        )
    entry: dict[str, Any] = {"text_columns": list(columns)}
    if id_column:
        entry["id_column"] = id_column
    if title_column:
        entry["title_column"] = title_column
    if source_column:
        entry["source_column"] = source_column
    if delimiter:
        entry["delimiter"] = delimiter
    canonical = json.dumps(
        {"schema_version": MAPPING_SCHEMA, "files": {"*": entry}},
        sort_keys=True,
        separators=(",", ":"),
    )
    return MappingConfig(files={"*": _entry_from_data(entry)}, sha256=sha256_text(canonical))


_ID_GUESSES: Final[frozenset[str]] = frozenset({"id", "case_id", "record_id", "uid", "key"})
_TITLE_GUESSES: Final[frozenset[str]] = frozenset({"title", "name", "subject"})
_TEXT_GUESSES: Final[frozenset[str]] = frozenset(
    {"description", "summary", "abstract", "text", "body", "notes", "details"}
)


def skeleton_mapping(file_name: str, headers: Sequence[str]) -> str:
    """Return a ready-to-edit mapping file for a CSV file.

    Args:
        file_name: The relative path of the CSV file (the mapping key).
        headers: The header names found in the file.

    Returns:
        JSON text (indent 2, trailing newline) that validates against
        MAPPING_JSON_SCHEMA. Columns are guessed from common header names.
    """

    def key(header: str) -> str:
        return re.sub(r"[\s-]+", "_", header.strip().lower())

    def first(guesses: frozenset[str]) -> str | None:
        for header in headers:
            if key(header) in guesses:
                return header
        return None

    id_col = first(_ID_GUESSES)
    title_col = first(_TITLE_GUESSES)
    text_cols = [h for h in headers if key(h) in _TEXT_GUESSES and h]
    if not text_cols:
        fallback = next((h for h in headers if h and h not in (id_col, title_col)), None)
        if fallback is not None:
            text_cols = [fallback]
    if not text_cols and headers:
        text_cols = [headers[0]]
    entry: dict[str, Any] = {}
    if id_col:
        entry["id_column"] = id_col
    if title_col:
        entry["title_column"] = title_col
    entry["text_columns"] = list(dict.fromkeys(text_cols))
    document = {"schema_version": MAPPING_SCHEMA, "files": {file_name: entry}}
    return json.dumps(document, indent=2, ensure_ascii=False) + "\n"
