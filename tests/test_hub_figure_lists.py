"""The figure allow-lists of the page script cover those of the figure generator (plan 06).

Static. `hub-core.js` holds the arrays `figureTags` and `figureAttrs`; `figures.py` holds
`FIGURE_TAGS` and `FIGURE_ATTRS`. Every tag and every attribute that the build may write must
be one that the page inserts, else `HubApp.figure` returns null and a row has no picture.

Known difference (2026-11-08): the page also accepts `aria-hidden`, which the plan 03 helper
test uses in its good string and which the generator never writes. The page list is therefore
the generator list plus that one name. A later plan may add the name to the generator or drop
it from the page; until then this test pins the exact difference.
"""

from __future__ import annotations

import re
from pathlib import Path

from mindrian_eureka.hub.figures import FIGURE_ATTRS, FIGURE_TAGS

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "src/mindrian_eureka/hub/assets/authored/hub-core.js"
PAGE_ONLY_ATTRS = {"aria-hidden"}


def js_array(name: str) -> set[str]:
    text = CORE.read_text(encoding="utf-8")
    match = re.search(r"const " + re.escape(name) + r"\s*=\s*\[([^\]]*)\]", text)
    assert match, f"{name} is not an array literal in hub-core.js"
    return set(re.findall(r'"([^"]+)"', match.group(1)))


def test_figure_tags_match() -> None:
    assert js_array("figureTags") == set(FIGURE_TAGS)
    assert len(FIGURE_TAGS) == 7


def test_page_accepts_every_generator_attribute() -> None:
    page = js_array("figureAttrs")
    generator = set(FIGURE_ATTRS)
    assert generator <= page, sorted(generator - page)
    assert page - generator == PAGE_ONLY_ATTRS, sorted(page - generator)
    assert len(FIGURE_ATTRS) == 21
    assert len(page) == 21 + len(PAGE_ONLY_ATTRS)


def test_extraction_negative_control() -> None:
    assert js_array("figureTextTags") == {"text", "title", "desc"}
    assert js_array("figureTags") != js_array("figureTextTags")
