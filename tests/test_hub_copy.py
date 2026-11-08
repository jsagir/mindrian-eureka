"""Tests for the copy deck: coverage of UI-SPEC section 9 and the text rules."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from mindrian_eureka.hub.contracts import has_dash, has_internal_name
from mindrian_eureka.hub.deck import DECK, SLOT_NAMES, deck_js_bytes, fill
from mindrian_eureka.run.contracts import LABEL, UNUSUAL_PAIRS_NAME, WORDING_AND_MEANING_NAME

ROOT = Path(__file__).resolve().parents[1]
UI_SPEC = (
    ROOT
    / ".planning"
    / "phases"
    / "02.1-opportunity-hub-in-the-mos-brand-format"
    / "02.1-UI-SPEC.md"
)
ID_ROW = re.compile(r"^\| ((?:G|B|Gr|C|P|D|L|E)\d{2}) \|", re.MULTILINE)
SLOT = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
TEMPORARY = re.compile(
    r"\b(temporary|temporarily|partial|partially|coming soon|not yet|placeholder|beta|"
    r"preview|work in progress|todo|for now)\b",
    re.IGNORECASE,
)
# Where the word "eureka" may appear: the product name, the owner-ruled label
# "Potential eureka" (CONTEXT D-14) and the command name `eureka hub`.
EUREKA_ALLOWED = re.compile(r"MindrianOS Eureka|potential eurekas?|eureka hub", re.IGNORECASE)


def spec_ids() -> list[str]:
    if not UI_SPEC.is_file():
        pytest.skip("the UI-SPEC file is missing on this machine")
    text = UI_SPEC.read_text(encoding="utf-8")
    start = text.index("## 9. Copy deck")
    end = text.index("## 10.", start)
    return ID_ROW.findall(text[start:end])


def test_every_spec_id_has_a_deck_key() -> None:
    ids = spec_ids()
    assert len(ids) == len(set(ids))
    # G01-G16, B01-B16, Gr01-Gr19, C01-C11, P01-P10, D01-D03, L01-L08, E01-E05,
    # plus G17 (the run reading band, Phase 2.3.1 D-04)
    assert len(ids) == 16 + 16 + 19 + 11 + 10 + 3 + 8 + 5 + 1
    missing = [
        spec_id
        for spec_id in ids
        if not any(key == spec_id or key.startswith(spec_id + ".") for key in DECK)
    ]
    assert missing == []


def test_every_deck_key_belongs_to_a_spec_id() -> None:
    ids = set(spec_ids())
    stray = [key for key in DECK if key.split(".")[0] not in ids]
    assert stray == []


def test_label_and_engine_names_come_from_the_run_contracts() -> None:
    assert DECK["G08"] == LABEL
    assert LABEL in DECK["G14"]
    assert DECK["G15.unusual_pairs"] == UNUSUAL_PAIRS_NAME
    assert DECK["G15.wording_and_meaning"] == WORDING_AND_MEANING_NAME
    assert UNUSUAL_PAIRS_NAME in DECK["B04.body"]
    assert WORDING_AND_MEANING_NAME in DECK["B04.body"]
    assert LABEL in DECK["Gr14.line"]


def test_added_keys_exist() -> None:
    assert DECK["P06.hidden"] == "Hidden by default"
    assert DECK["G03.lockup_alt"] == "MindrianOS"
    assert "{floor}" in DECK["B05.one.unusual_pairs"]
    assert "{floor}" in DECK["B05.one.wording_and_meaning"]
    assert "{floor_unusual_pairs}" in DECK["B05"]
    assert "{floor_wording_and_meaning}" in DECK["B05"]


def test_values_are_plain_ascii_without_dashes_or_internal_names() -> None:
    for key, value in DECK.items():
        assert value.isascii(), key
        assert not has_dash(value), key
        assert not has_internal_name(value), key
        assert value == value.strip(), key
        assert value, key


def test_no_wording_that_marks_a_feature_as_temporary_or_partial() -> None:
    for key, value in DECK.items():
        assert TEMPORARY.search(value) is None, key


def test_the_word_eureka_appears_only_in_allowed_phrases() -> None:
    for key, value in DECK.items():
        rest = EUREKA_ALLOWED.sub("", value)
        assert "eureka" not in rest.lower(), key
    # The product name is in the header and the footer.
    assert "Eureka" in DECK["G03"]
    assert "Eureka" in DECK["G14"]
    # No bridge or result is called "eureka" without the word "potential".
    for key in ("Gr03.eureka", "Gr05.tour", "Gr05.next", "Gr14.bridge", "Gr15", "P06.eureka"):
        assert "otential eureka" in DECK[key], key


def test_slots_are_known() -> None:
    for key, value in DECK.items():
        for name in SLOT.findall(value):
            assert name in SLOT_NAMES, (key, name)


def test_deck_has_no_stray_braces() -> None:
    for key, value in DECK.items():
        assert SLOT.sub("", value).count("{") == 0, key
        assert SLOT.sub("", value).count("}") == 0, key


# --- fill ------------------------------------------------------------------


def test_fill_replaces_every_slot() -> None:
    assert fill(DECK["C05"], a=3, b=40) == "Showing 3 of 40 records."
    assert fill("{n} and {n}", n=2) == "2 and 2"
    assert fill(DECK["B06"]) == DECK["B06"]


def test_fill_missing_value_raises_key_error() -> None:
    with pytest.raises(KeyError):
        fill(DECK["C05"], a=3)


def test_fill_unknown_slot_raises_value_error() -> None:
    with pytest.raises(ValueError):
        fill("Hello {nobody}", nobody="x")


def test_fill_never_uses_format_syntax() -> None:
    # A value that looks like a slot or a format field is inserted as plain text.
    assert fill("Read {ID}", ID="{n}") == "Read {n}"
    assert fill("Read {ID}", ID="{0.__class__}") == "Read {0.__class__}"
    assert fill("Read {ID}", ID="%s") == "Read %s"


def test_fill_ignores_unused_values() -> None:
    assert fill("Rank {n}", n=1, other="x") == "Rank 1"


def test_fill_converts_values_with_str() -> None:
    assert fill("{x}", x=0.5) == "0.5"


# --- deck_js_bytes -----------------------------------------------------------


def test_deck_js_bytes_is_stable_and_round_trips() -> None:
    first = deck_js_bytes()
    assert first == deck_js_bytes()
    text = first.decode("utf-8")
    assert text.startswith("window.HUB_COPY = ")
    assert text.endswith(";\n")
    assert "&" not in text
    assert json.loads(text[len("window.HUB_COPY = ") : -2]) == DECK
