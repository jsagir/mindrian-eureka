"""Scan written hub files for network loads and authored-copy violations.

Vendored JS and binary fonts are skipped, since their canonical bytes and notices
are separately checked. Record content is excluded from copy checks, not from
executable-load checks. Unknown text file types still receive a network scan.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterator
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from mindrian_eureka.hub.contracts import has_dash, has_internal_name

_REMOTE = re.compile(r"^(?:https?:|wss?:|ftp:|//)", re.I)
_URL = re.compile(r"(?:https?:|wss?:|ftp:)//|(?<!:)//[\w.-]+/", re.I)
_JS = re.compile(
    r"\b(?:fetch\s*\(|XMLHttpRequest|WebSocket|EventSource|sendBeacon|importScripts|"
    r"navigator\s*\.\s*serviceWorker|import\s*\()"
)
_SVG = "http://www.w3.org/2000/svg"
_SKIP = {".woff", ".woff2", ".ttf", ".otf"}
_SOURCE_FIELDS = {"title", "text", "source_ref", "source_file", "id", "pair_id", "key"}


class _Loads(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.findings: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.lower(): value or "" for name, value in attrs}
        for name in ("src", "href", "srcset", "action", "poster", "data", "ping"):
            value = values.get(name, "")
            candidates = re.split(r"[\s,]+", value) if name in {"srcset", "ping"} else [value]
            if any(_REMOTE.match(candidate.strip()) for candidate in candidates):
                self.findings.append(f"{tag} {name} contains a remote load")
        if tag == "link" and set(values.get("rel", "").lower().split()) & {
            "preconnect", "dns-prefetch", "prefetch", "preload"
        }:
            self.findings.append("link contains speculative loading")
        if tag == "meta" and values.get("http-equiv", "").lower() == "refresh":
            self.findings.append("meta refresh")
        for name, value in values.items():
            if name == "style" and _URL.search(value):
                self.findings.append("inline style contains a remote load")


def _files(folder: Path) -> Iterator[Path]:
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix not in _SKIP:
            if path.suffix == ".js" and "vendor" in path.relative_to(folder).parts:
                continue
            yield path


def scan_for_network(folder: Path) -> list[str]:
    """Return findings for remote loads in HTML, CSS, authored JS and unknown text."""
    findings: list[str] = []
    for path in _files(folder):
        text = path.read_text(encoding="utf-8", errors="replace")
        name = path.relative_to(folder).as_posix()
        if path.suffix in {".html", ".svg"}:
            parser = _Loads()
            parser.feed(text)
            findings.extend(f"{name}: {item}" for item in parser.findings)
        elif path.suffix == ".js":
            if _JS.search(text) or _URL.search(text.replace(_SVG, "")):
                findings.append(f"{name}: remote URL or network API")
        elif path.suffix == ".css":
            # Canonical CSS may mention a URL in a comment; only load constructs count.
            uncommented = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
            for match in re.finditer(r"(?:url\s*\([^)]*\)|@import[^;]+)", uncommented, re.I):
                if _URL.search(match.group()):
                    findings.append(f"{name}: remote CSS load")
        elif path.suffix not in {".json", ".txt", ".md"} and _URL.search(text):
            findings.append(f"{name}: remote URL in unknown file type")
    return findings


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            if key not in _SOURCE_FIELDS:
                yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _copy_findings(folder: Path, check: Callable[[str], bool]) -> list[str]:
    findings = []
    for path in _files(folder):
        if path.suffix not in {".html", ".css", ".js", ".json"}:
            continue
        text = path.read_text(encoding="utf-8")
        if path.name == "hub-data.js":
            data = json.loads(text.removeprefix("window.HUB = ").rstrip(";\n"))
            values = list(_strings(data))
        elif path.suffix == ".html":
            # Strip the source text nodes using the already provenance-checked payload.
            data_path = folder / "hub-data.js"
            values = [text]
            if data_path.exists():
                data = json.loads(data_path.read_text().removeprefix("window.HUB = ").rstrip(";\n"))
                from html import escape
                for record in data["records"]:
                    for key in _SOURCE_FIELDS:
                        value = record.get(key)
                        if isinstance(value, str) and value:
                            values[0] = values[0].replace(escape(value, quote=True), "")
        else:
            values = [text]
        if any(check(value) for value in values):
            findings.append(path.relative_to(folder).as_posix())
    return findings


def scan_dashes(folder: Path) -> list[str]:
    """Check authored files and payload copy, excluding vendor, fonts and source fields."""
    return _copy_findings(folder, has_dash)


def scan_internal_names(folder: Path) -> list[str]:
    """Check authored files and payload copy, excluding vendor, fonts and source fields."""
    return _copy_findings(folder, has_internal_name)
