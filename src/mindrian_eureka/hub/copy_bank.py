"""Copy deck part: the finding rows of the opportunity bank (Phase 2.3.1, plan 06 owns this part).

`deck.py` merges `COPY` into `DECK`. A key that another part or the base deck already
defines raises at import. Keys follow the copy-deck ID rule of the UI-SPEC: these are sub
keys of the row ID B08.

The words are a screening aid. No string claims novelty, evidence or value.

Import rule: the standard library only. ASCII only, no dash character.
"""

from __future__ import annotations

COPY: dict[str, str] = {
    "B08.caption.meaning": "meaning",
    "B08.caption.wording": "wording",
    "B08.open": "Open this pair",
    "B08.and": "and",
    "B08.shared": "Shared distinctive words: {list}.",
    "B08.shared_none": "No distinctive word is shared.",
    "B08.use.label": "Use it when:",
    "B08.use.meaning": (
        "Two records may say the same thing in different words. "
        "Read both to check whether they overlap or complement each other."
    ),
    "B08.use.wording": (
        "Two records share words but may mean different things. "
        "Read both to check whether the shared words hide a real difference."
    ),
    "B08.use.agree": (
        "Wording and meaning agree on this pair. "
        "Read both records to check what they share and where they differ."
    ),
}
