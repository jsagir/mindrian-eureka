"""HTML cleanup for CSV cells (standard library only).

`looks_like_html` tells whether a cell holds HTML. `html_to_text` turns HTML
into plain text with one line break at each block tag.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Final

_HTML_HINT: Final[re.Pattern[str]] = re.compile(r"<[A-Za-z/!]")
_SKIP_TAGS: Final[frozenset[str]] = frozenset({"script", "style", "head"})
_BLOCK_TAGS: Final[frozenset[str]] = frozenset(
    {
        "p", "div", "br", "li", "ul", "ol", "tr", "table", "section", "article",
        "header", "footer", "blockquote", "pre", "hr",
        "h1", "h2", "h3", "h4", "h5", "h6",
    }
)  # fmt: skip
_SPACES: Final[re.Pattern[str]] = re.compile(r"[ \t\r\f\v]+")
_BLANK_RUN: Final[re.Pattern[str]] = re.compile(r"\n{3,}")


def looks_like_html(value: str) -> bool:
    """Return True when `value` has a tag-like start, such as `<p`, `</` or `<!`.

    A text such as `x < 5` is not HTML.
    """
    return _HTML_HINT.search(value) is not None


class _TextExtractor(HTMLParser):
    """Collect visible text and put a line break at block tags."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def _break(self) -> None:
        if self._parts and not self._parts[-1].endswith("\n"):
            self._parts.append("\n")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS and not self._skip_depth:
            self._break()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BLOCK_TAGS and not self._skip_depth:
            self._break()

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag in _BLOCK_TAGS and not self._skip_depth:
            self._break()

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self._parts.append(data)

    def text(self) -> str:
        return "".join(self._parts)


def html_to_text(value: str) -> str:
    """Convert HTML to plain text.

    Content of script, style and head tags is dropped. Block tags give one line
    break. Entities are decoded. Runs of spaces become one space and at most one
    blank line stays between blocks.

    Args:
        value: A string that may hold HTML.

    Returns:
        The plain text, stripped.
    """
    parser = _TextExtractor()
    parser.feed(value)
    parser.close()
    raw = parser.text().replace("\xa0", " ")
    lines = [_SPACES.sub(" ", line).strip() for line in raw.split("\n")]
    return _BLANK_RUN.sub("\n\n", "\n".join(lines)).strip()
