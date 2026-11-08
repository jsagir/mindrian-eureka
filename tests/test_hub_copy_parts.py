"""The deck is one dict assembled from `deck.py` and four part modules (plan 02.3.1-03).

Each later plan fills its own part, so plans of one wave never edit the same file. A key that
two parts define raises at import. Every deck test runs on the merged dict.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest
from mindrian_eureka.hub import copy_bank, copy_pages, copy_theme, copy_views, deck
from mindrian_eureka.hub.deck import DECK

ROOT = Path(__file__).resolve().parents[1]
PARTS = (copy_theme, copy_bank, copy_views, copy_pages)
ID_RULE = re.compile(r"^(?:G|B|Gr|C|P|D|L|E)\d{2}(?:\.|$)")


def test_parts_exist_and_hold_dicts() -> None:
    assert deck.PARTS == tuple(part.COPY for part in PARTS)
    for part in PARTS:
        assert isinstance(part.COPY, dict)
        for key, value in part.COPY.items():
            assert isinstance(key, str) and isinstance(value, str), key


def test_deck_is_the_merge_of_the_base_and_the_parts() -> None:
    part_keys = {key for part in PARTS for key in part.COPY}
    base = {key: value for key, value in DECK.items() if key not in part_keys}
    merged = dict(base)
    for part in PARTS:
        merged.update(part.COPY)
    assert DECK == merged
    assert deck.merge_parts(dict(base), deck.PARTS) == DECK


def test_a_key_defined_twice_raises_at_import() -> None:
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(copy_theme, "COPY", {"G01.bank": "a second title"})
        with pytest.raises(ValueError, match="G01.bank"):
            importlib.reload(deck)
    importlib.reload(deck)
    assert deck.DECK == DECK
    with pytest.raises(ValueError, match="G02"):
        deck.merge_parts({"G02": "a"}, ({"G02": "b"},))


def test_part_keys_follow_the_copy_deck_id_rule() -> None:
    for part in PARTS:
        for key in part.COPY:
            assert ID_RULE.match(key), key


def test_part_files_are_ascii_without_dashes() -> None:
    for part in PARTS:
        text = Path(part.__file__).read_text(encoding="utf-8")
        assert text.isascii(), part.__name__
        assert "–" not in text and "—" not in text
        assert '"""' in text and "COPY: dict[str, str]" in text
