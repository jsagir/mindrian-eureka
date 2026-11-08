"""The three figure attribute lists stand in one stated relation (plans 06 and 11).

Static. `hub-core.js` holds the arrays `figureTags` and `figureAttrs`; `figures.py` holds
`FIGURE_TAGS` and `FIGURE_ATTRS`; `tests/test_hub_browser_shell.py` holds the tuple
`FIGURE_ATTRS` that the figure helper test compares with the page. Every tag and every
attribute that the build may write must be one that the page inserts, else `HubApp.figure`
returns null and a row has no picture.

The relation is a stated rule, not a temporary difference. `docs/brand/hub-figure-rules.md`,
section Text and safety, states it: the page list equals the generator list plus
`aria-hidden` (22 names; the plan 03 helper test uses it in its good string and the generator
never writes it), and the shell test tuple equals the page list in order. This module reads
all three lists and that sentence.
"""

from __future__ import annotations

import re
from pathlib import Path

from mindrian_eureka.hub.figures import FIGURE_ATTRS, FIGURE_TAGS

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "src/mindrian_eureka/hub/assets/authored/hub-core.js"
SHELL_TEST = ROOT / "tests/test_hub_browser_shell.py"
RULES = ROOT / "docs/brand/hub-figure-rules.md"
PAGE_ONLY_ATTRS = {"aria-hidden"}


def js_list(name: str) -> list[str]:
    """The quoted names of a `const <name> = [...]` literal of hub-core.js, in order."""
    text = CORE.read_text(encoding="utf-8")
    match = re.search(r"const " + re.escape(name) + r"\s*=\s*\[([^\]]*)\]", text)
    assert match, f"{name} is not an array literal in hub-core.js"
    return re.findall(r'"([^"]+)"', match.group(1))


def js_array(name: str) -> set[str]:
    return set(js_list(name))


def shell_tuple() -> list[str]:
    """The quoted names of the `FIGURE_ATTRS = (...)` tuple of the shell test, in order."""
    # The tuple closes with a parenthesis at the start of a line; its comment lines may hold
    # a parenthesis of their own, but no double quote.
    text = SHELL_TEST.read_text(encoding="utf-8")
    match = re.search(r"^FIGURE_ATTRS\s*=\s*\(\n(.*?)\n\)", text, re.S | re.M)
    assert match, "FIGURE_ATTRS is not a tuple literal in the shell test"
    return re.findall(r'"([^"]+)"', match.group(1))


def test_figure_tags_match() -> None:
    assert js_array("figureTags") == set(FIGURE_TAGS)
    assert len(FIGURE_TAGS) == 7


def test_page_accepts_every_generator_attribute() -> None:
    page = js_array("figureAttrs")
    generator = set(FIGURE_ATTRS)
    assert generator <= page, sorted(generator - page)
    assert page - generator == PAGE_ONLY_ATTRS, sorted(page - generator)
    assert len(FIGURE_ATTRS) == 21
    assert len(page) == 22


def test_shell_tuple_equals_the_page_list_in_order() -> None:
    # The shell test's own test_figure_lists_are_the_agreed_ones compares the same two lists.
    assert shell_tuple() == js_list("figureAttrs")


def test_rules_file_states_the_relation() -> None:
    text = RULES.read_text(encoding="utf-8")
    assert "`aria-hidden` (22 names" in text
    assert "reads all three" in text


def test_extraction_negative_control() -> None:
    assert js_array("figureTextTags") == {"text", "title", "desc"}
    assert js_array("figureTags") != js_array("figureTextTags")
    assert shell_tuple() != list(FIGURE_TAGS)
