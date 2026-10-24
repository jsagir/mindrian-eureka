"""Scan written hub files for network loads and authored-copy violations.

Vendored JS and binary fonts are skipped, since their canonical bytes and notices
are separately checked. Record content is excluded from copy checks, not from
executable-load checks. Known data scripts must parse wholly as passive JSON;
actual link fields are validated, while source text and ciphertext are not loads.
Unknown text file types still receive a network scan.
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
_ASSIGNMENTS = {"hub-data.js": {"HUB", "HUB_ENVELOPE"}, "hub-copy.js": {"HUB_COPY"}}
_LINK_FIELDS = {"source_link", "file_link", "catalogue_link"}
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



def _invalid_constant(value: str) -> None:
    raise ValueError("nonfinite JSON constant")


def _assignment(text: str, name: str) -> tuple[str, Any]:
    """Parse the whole data script; trailing executable code is never accepted."""
    match = re.fullmatch(r"window\.(HUB|HUB_ENVELOPE|HUB_COPY) = ([\s\S]*);\n?", text)
    if match is None or match.group(1) not in _ASSIGNMENTS[name]:
        raise ValueError("not a passive data assignment")
    value = json.loads(match.group(2), parse_constant=_invalid_constant)
    if not isinstance(value, dict):
        raise ValueError("data must be an object")
    return match.group(1), value


def _link_loads(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in _LINK_FIELDS and item is not None:
                if not isinstance(item, str) or not item or re.search(
                    r"^[a-z][a-z0-9+.-]*:|^[\\/]|[\x00-\x20\x7f]", item, re.I
                ):
                    return True
            elif _link_loads(item):
                return True
    elif isinstance(value, list):
        return any(_link_loads(item) for item in value)
    return False

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
        elif path.name in _ASSIGNMENTS:
            try:
                _, data = _assignment(text, path.name)
                if _link_loads(data):
                    findings.append(f"{name}: nonlocal data link")
            except ValueError:
                findings.append(f"{name}: data script is not a passive JSON assignment")
        elif path.suffix == ".js":
            without_namespace = re.sub(re.escape(_SVG) + r"(?=[\"'\s<>]|$)", "", text)
            if _JS.search(text) or _URL.search(without_namespace):
                findings.append(f"{name}: remote URL or network API")
        elif path.suffix == ".css":
            # Canonical CSS may mention a URL in a comment; only load constructs count.
            uncommented = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
            for match in re.finditer(r"(?:url\s*\([^)]*\)|@import[^;]+)", uncommented, re.I):
                if re.search(r"(?:https?:|wss?:|ftp:|//)", match.group(), re.I):
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
            variable, data = _assignment(text, path.name)
            if variable == "HUB_ENVELOPE":
                # Ciphertext, salt and nonce are opaque bytes, never rendered copy or URLs.
                values = [str(data.get("schema", "")), str(data.get("kdf", {}).get("name", "")),
                          str(data.get("cipher", {}).get("name", ""))]
            else:
                values = list(_strings(data))
        elif path.suffix == ".html":
            # Strip the source text nodes using the already provenance-checked payload.
            data_path = folder / "hub-data.js"
            values = [text]
            if data_path.exists():
                variable, data = _assignment(data_path.read_text(), data_path.name)
                from html import escape
                for record in data.get("records", []) if variable == "HUB" else []:
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
