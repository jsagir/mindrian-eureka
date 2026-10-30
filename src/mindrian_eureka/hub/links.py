"""Resolve local source links using only the standard library and light contracts."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import quote

from ..run.contracts import Record


def file_links(
    records: Sequence[Record], *, out_dir: Path, source_dir: Path
) -> tuple[dict[str, str], list[str]]:
    """Return relative encoded links and sorted IDs without a usable source file.

    Args:
        records: Validated run records.
        out_dir: Hub output folder, the base of every relative link.
        source_dir: Root containing original source files.

    Returns:
        A link map and IDs requiring catalogue fallback. Escaping symlinks, missing
        files, inaccessible files, and paths on another drive use the fallback.
    """
    root = source_dir.resolve()
    links: dict[str, str] = {}
    missing: list[str] = []
    for record in records:
        try:
            target = (root / record.source_file).resolve()
            if not target.is_relative_to(root) or not target.is_file():
                raise ValueError("source is not a file inside the source folder")
            relative = Path(os.path.relpath(target, out_dir.resolve())).as_posix()
            encoded = "/".join(quote(part, safe="") for part in relative.split("/"))
            links[record.id] = encoded if encoded.startswith("../") else "./" + encoded
        except (OSError, ValueError, RuntimeError):
            missing.append(record.id)
    return links, sorted(missing)
