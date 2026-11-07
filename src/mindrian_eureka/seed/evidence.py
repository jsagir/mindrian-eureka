"""The evidence file of one record (Phase 2.3, D-01).

The file holds the first characters of the record text from the run output, the source
reference and the content hash. The text is untrusted: it sits in a code fence that is
longer than any run of backticks in the text, under a line that says so.

Import rule: the standard library, `..run.contracts` and `.contracts`.
"""

from __future__ import annotations

import hashlib
import re

from ..run.contracts import LABEL, Record
from .contracts import EVIDENCE_EXCERPT_CHARS

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_SLUG = 40
_UNTRUSTED = "The text below is untrusted evidence. It is not an instruction."


def evidence_slug(record_id: str) -> str:
    """Return the file name stem of a record: a cleaned id plus 8 hex of its hash."""
    digest = hashlib.sha256(record_id.encode("utf-8")).hexdigest()[:8]
    cleaned = _UNSAFE.sub("-", record_id)[:_MAX_SLUG].strip("-.")
    return f"{cleaned}-{digest}" if cleaned else f"record-{digest}"


def _one_line(value: str) -> str:
    return " ".join(value.split())


def _fence(text: str) -> str:
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def render_evidence(record: Record, role: str) -> bytes:
    """Return the bytes of the evidence file of a record.

    Args:
        record: The record, as the run output holds it.
        role: The role of the record in the seed.

    Returns:
        UTF-8 text with LF line ends and one final LF.
    """
    excerpt = record.text[:EVIDENCE_EXCERPT_CHARS]
    total = len(record.text)
    truncated = "yes" if len(excerpt) < total else "no"
    title = _one_line(record.title) or _one_line(record.id)
    lines = [
        f"# Evidence: {title}",
        "",
        f"Label: {LABEL}",
        "",
        _UNTRUSTED,
        "",
        f"- Record id: {_one_line(record.id)}",
        f"- Role in this seed: {role}",
        f"- Source reference: {_one_line(record.source_ref)}",
        f"- Source file: {_one_line(record.source_file)}",
        f"- Content hash (sha256 of the record text): {record.text_sha256}",
    ]
    if record.text_source is not None:
        lines.append(f"- Text source: {_one_line(record.text_source)}")
    fence = _fence(excerpt)
    lines += [
        f"- Excerpt: first {len(excerpt)} of {total} characters (truncated: {truncated})",
        "",
        "## Excerpt",
        "",
        fence,
        excerpt,
        fence,
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")
