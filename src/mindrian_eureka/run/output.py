"""Write the output files of `eureka run`.

One canonical JSON writer serves every JSON file. Files go to a staging folder next
to the output folder and one rename publishes them, so an interrupted run never leaves
a folder that looks complete. A folder is replaced only when it already is an Eureka run.
A caller can pass its own test and kind word (the hub does) to replace its own earlier folder.

This module imports only the standard library and `.contracts`.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import TracebackType
from typing import Any

from .contracts import CORPUS_SCHEMA, LABEL, MANIFEST_SCHEMA, SUMMARY_LINE, Record, UsageError

OUTPUT_UNUSUAL = "unusual-pairs.json"
OUTPUT_WORDING = "wording-and-meaning-pairs.json"
OUTPUT_MARKDOWN = "ranked-pairs.md"
OUTPUT_CORPUS = "corpus/records.jsonl"
OUTPUT_MANIFEST = "manifest.json"
OUTPUT_RUN_INFO = "run-info.json"

_MAX_TITLE_CHARS = 80
_DIR_MODE = 0o700
_FILE_MODE = 0o600


# --- Canonical JSON ---------------------------------------------------------


def round_floats(value: object, digits: int | None = 6) -> Any:
    """Return a copy of `value` with every float rounded and every minus zero mapped to zero.

    Args:
        value: Any JSON-like value. bool and int stay unchanged.
        digits: The number of decimals, or None for no rounding.

    Returns:
        The cleaned copy. Lists and tuples become lists.

    Raises:
        ValueError: A float is NaN or infinite.
    """
    if isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("NaN and infinity cannot be written to an output file")
        rounded = value if digits is None else round(value, digits)
        return 0.0 if rounded == 0 else rounded
    if isinstance(value, Mapping):
        return {key: round_floats(item, digits) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [round_floats(item, digits) for item in value]
    return value


def canonical_json(value: object, *, digits: int | None = 6) -> bytes:
    """Return the canonical JSON bytes of `value`.

    The format is sorted keys, indent 2, UTF-8 without a byte order mark, LF line ends
    and one final LF. Lists keep their order.

    Args:
        value: Any JSON-like value.
        digits: The number of decimals for floats, or None for no rounding.

    Returns:
        The bytes to write.

    Raises:
        ValueError: The value holds NaN or infinity.
    """
    cleaned = round_floats(value, digits)
    text = json.dumps(cleaned, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
    return (text + "\n").encode("utf-8")


def corpus_lines(records: Sequence[Record]) -> bytes:
    """Return the JSON Lines bytes of the clean corpus.

    Args:
        records: The records, in output order.

    Returns:
        A header line and then one line for each record.
    """
    header = {
        "record_type": "header",
        "schema_version": CORPUS_SCHEMA,
        "label": LABEL,
        "record_count": len(records),
    }
    lines = [_compact(header)]
    for record in records:
        item: dict[str, Any] = {
            "record_type": "record",
            "id": record.id,
            "title": record.title,
            "text": record.text,
            "source_ref": record.source_ref,
            "source_file": record.source_file,
            "text_sha256": record.text_sha256,
        }
        if record.outcome_class is not None:
            item["outcome_class"] = record.outcome_class
        if record.extras:
            item["extras"] = dict(record.extras)
        if record.text_source is not None:
            item["text_source"] = record.text_source
        lines.append(_compact(item))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _compact(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


# --- Markdown report --------------------------------------------------------


def _cell(text: str) -> str:
    flat = " ".join(str(text).split())
    return flat.replace("|", "\\|")


def _record_cell(side: Mapping[str, Any]) -> str:
    record_id = str(side.get("id", ""))
    title = " ".join(str(side.get("title", "")).split())
    if not title:
        return _cell(record_id)
    if len(title) > _MAX_TITLE_CHARS:
        title = title[: _MAX_TITLE_CHARS - 3] + "..."
    return _cell(f"{title} ({record_id})")


def _score(scores: Mapping[str, Any], key: str) -> str:
    value = scores.get(key)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return f"{float(value):.4f}"
    return "-"


def _engine_section(projected: Mapping[str, Any]) -> list[str]:
    engine = projected.get("engine", {})
    lines = [
        f"## {engine.get('name', '')}",
        "",
        f"Label: {LABEL}",
        "",
        str(projected.get("score_meaning", "")),
        "",
    ]
    notes = projected.get("notes", [])
    if notes:
        lines.extend(f"- {_cell(str(note))}" for note in notes)
        lines.append("")
    counts = projected.get("counts", {})
    with_classes = isinstance(counts, Mapping) and "pair_classes" in counts
    header = "| Rank | Left record | Right record | Wording | Meaning | Rank score | Reading |"
    divider = "| --- | --- | --- | --- | --- | --- | --- |"
    if with_classes:
        header += " Class |"
        divider += " --- |"
    lines.append(header)
    lines.append(divider)
    for pair in projected.get("pairs", []):
        scores = pair.get("scores", {})
        cells = [
            _cell(str(pair.get("rank", ""))),
            _record_cell(pair.get("left", {})),
            _record_cell(pair.get("right", {})),
            _score(scores, "wording_similarity"),
            _score(scores, "meaning_similarity"),
            _score(scores, "rank_score"),
            _cell(str(pair.get("reading", ""))),
        ]
        if with_classes:
            cells.append(_cell(str(pair.get("pair_class", ""))))
        lines.append("| " + " | ".join(cells) + " |")
    if with_classes:
        classes = counts["pair_classes"]
        lines.append("")
        lines.append(
            f"Classes: cross {classes.get('cross', 0)}, "
            f"open_open {classes.get('open_open', 0)}, "
            f"licensed_licensed {classes.get('licensed_licensed', 0)}."
        )
    lines.append("")
    return lines


def render_ranked_markdown(unusual: Mapping[str, Any], wording: Mapping[str, Any]) -> str:
    """Render the Markdown report of both ranked lists.

    Args:
        unusual: The projected file of the unusual-pairs engine.
        wording: The projected file of the wording-and-meaning engine.

    Returns:
        The report text with LF line ends.
    """
    lines = ["# Ranked pairs", "", SUMMARY_LINE, "", f"Label: {LABEL}", ""]
    lines.extend(_engine_section(unusual))
    lines.extend(_engine_section(wording))
    return "\n".join(lines).rstrip("\n") + "\n"


# --- Staged output folder ---------------------------------------------------


@dataclass(frozen=True)
class FileDigest:
    """The hash and size of one written file.

    Attributes:
        path: The path of the file, relative to the output folder, with "/" separators.
        sha256: The sha256 of the bytes, as lowercase hex.
        bytes: The number of bytes.
    """

    path: str
    sha256: str
    bytes: int

    def as_dict(self) -> dict[str, Any]:
        """Return the digest as a JSON-ready dictionary."""
        return {"path": self.path, "sha256": self.sha256, "bytes": self.bytes}


def _chmod(path: Path, mode: int) -> None:
    """Set the mode where the OS supports it. A failure of this call is ignored."""
    try:
        os.chmod(path, mode)
    except OSError:
        return


def is_eureka_run_folder(path: Path) -> bool:
    """Return True when `path` is a folder with a valid Eureka run manifest."""
    manifest = path / OUTPUT_MANIFEST
    if not path.is_dir() or not manifest.is_file():
        return False
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and data.get("schema_version") == MANIFEST_SCHEMA


def _is_empty_dir(path: Path) -> bool:
    return path.is_dir() and not any(path.iterdir())


def _not_replaceable(kind: str) -> UsageError:
    """Build the error for an existing folder that the caller may not replace."""
    earlier = kind.removeprefix("Eureka ")
    return UsageError(
        f"output folder exists and is not an {kind}",
        fix=f"Choose a new folder name, an empty folder, or the folder of an earlier {earlier}.",
    )


def ensure_out_dir_allowed(
    input_dir: Path,
    out_dir: Path,
    *,
    replaceable: Callable[[Path], bool] | None = None,
    kind: str = "Eureka run",
) -> None:
    """Refuse an output folder that could damage the input or a foreign folder.

    Args:
        input_dir: The input folder.
        out_dir: The requested output folder.
        replaceable: A test for an existing non-empty folder that may be replaced.
            None means `is_eureka_run_folder`.
        kind: The name of the folder kind, used in the error text. The default is
            "Eureka run".

    Raises:
        UsageError: The output folder is, holds or lies inside the input folder; or it
            is a file; or it is a non-empty folder that `replaceable` refuses; or no
            parent folder can hold it.
    """
    may_replace = is_eureka_run_folder if replaceable is None else replaceable
    source = input_dir.resolve()
    target = out_dir.resolve()
    if target == source or target.is_relative_to(source):
        raise UsageError(
            "output folder is the input folder or lies inside it",
            fix="Choose an --out folder outside the input folder.",
        )
    if source.is_relative_to(target):
        raise UsageError(
            "input folder lies inside the output folder",
            fix="Choose an --out folder that does not hold the input folder.",
        )
    if target.exists():
        if not target.is_dir():
            raise UsageError(
                "output path is a file",
                fix="Choose a folder name that does not exist, or an empty folder.",
            )
        if not may_replace(target) and not _is_empty_dir(target):
            raise _not_replaceable(kind)
        return
    parent = target.parent
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent
    if not parent.is_dir():
        raise UsageError(
            "the parent of the output folder is a file",
            fix="Choose an --out folder inside a folder.",
        )


def _check_relative(relative_path: str) -> PurePosixPath:
    if not relative_path or "\0" in relative_path:
        raise ValueError("relative path is empty or invalid")
    unified = relative_path.replace("\\", "/")
    if (
        PurePosixPath(unified).is_absolute()
        or PureWindowsPath(relative_path).is_absolute()
        or PureWindowsPath(relative_path).drive
    ):
        raise ValueError(f"path must be relative: {relative_path}")
    parts = PurePosixPath(unified).parts
    if not parts or ".." in parts:
        raise ValueError(f"path must not contain '..': {relative_path}")
    return PurePosixPath(*parts)


class StagedRun:
    """A staging folder next to the output folder, published by one rename.

    Use it as a context manager. Leaving the block without `publish()`, or with an
    exception, removes the staging folder.

    Attributes:
        path: The staging folder.
        out_dir: The final output folder.
        replaceable: The test for an existing non-empty folder that `publish` may replace.
        kind: The name of the folder kind, used in the error text.
    """

    def __init__(
        self,
        out_dir: Path,
        *,
        replaceable: Callable[[Path], bool] | None = None,
        kind: str = "Eureka run",
    ) -> None:
        """Create the staging folder.

        Args:
            out_dir: The final output folder.
            replaceable: A test for an existing non-empty folder that `publish` may
                replace. None means `is_eureka_run_folder`.
            kind: The name of the folder kind, used in the error text.
        """
        self.out_dir = out_dir
        self.replaceable = is_eureka_run_folder if replaceable is None else replaceable
        self.kind = kind
        self.path = out_dir.parent / f".{out_dir.name}.staging-{os.getpid()}"
        out_dir.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            shutil.rmtree(self.path)
        self.path.mkdir(mode=_DIR_MODE)
        _chmod(self.path, _DIR_MODE)

    def __enter__(self) -> StagedRun:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.discard()

    def write(self, relative_path: str, data: bytes) -> FileDigest:
        """Write `data` into the staging folder.

        Args:
            relative_path: The path inside the output folder. No absolute path, no "..".
            data: The bytes to write.

        Returns:
            The digest of the written file.

        Raises:
            ValueError: The path is absolute, empty or contains "..".
        """
        relative = _check_relative(relative_path)
        target = self.path.joinpath(*relative.parts)
        root = self.path.resolve()
        if not target.resolve().is_relative_to(root):
            raise ValueError(f"path leaves the staging folder: {relative_path}")
        current = self.path
        for part in relative.parts[:-1]:
            current = current / part
            if not current.exists():
                current.mkdir(mode=_DIR_MODE)
                _chmod(current, _DIR_MODE)
        target.write_bytes(data)
        _chmod(target, _FILE_MODE)
        return FileDigest(
            path=relative.as_posix(),
            sha256=hashlib.sha256(data).hexdigest(),
            bytes=len(data),
        )

    def publish(self) -> None:
        """Move the staging folder to the output folder.

        An existing folder that `replaceable` accepts (by default an Eureka run) or an
        empty folder is replaced. Any other existing path raises UsageError and leaves
        the staging folder in place.

        Raises:
            UsageError: The output path exists and is neither accepted by `replaceable`
                nor an empty folder.
        """
        out = self.out_dir
        if not out.exists() and not out.is_symlink():
            os.replace(self.path, out)
            return
        if out.is_symlink() or not out.is_dir():
            raise UsageError(
                "output path exists and is not a folder",
                fix="Choose a folder name that does not exist.",
            )
        if not self.replaceable(out) and not _is_empty_dir(out):
            raise _not_replaceable(self.kind)
        aside = out.parent / f".{out.name}.old-{os.getpid()}"
        if aside.exists():
            shutil.rmtree(aside)
        os.replace(out, aside)
        try:
            os.replace(self.path, out)
        except OSError:
            os.replace(aside, out)
            raise
        shutil.rmtree(aside, ignore_errors=True)

    def discard(self) -> None:
        """Remove the staging folder if it exists."""
        if self.path.exists():
            shutil.rmtree(self.path, ignore_errors=True)
