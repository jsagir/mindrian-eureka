"""Copy deck part: the graph, catalogue and panel views (Phase 2.3.1, plan 07 owns this part).

`deck.py` merges `COPY` into `DECK`. A key that another part or the base deck already
defines raises at import. Keys follow the copy-deck ID rule of the UI-SPEC.

The three strings are the ways into the pages of plan 08: the catalogue row opens a record
page, the graph pair list and the reading panel open a pair or record page.

Import rule: the standard library only. ASCII only, no dash character.
"""

from __future__ import annotations

COPY: dict[str, str] = {
    # Catalogue row: the page link of a record (visible text and accessible name).
    "C07.open": "Open {ID}",
    # Reading panel: the link to the full page of the pair or record shown.
    "P05.page": "Open the full page",
    # Graph pair list: the link to the page of a pair.
    "Gr16.open": "Open this pair",
}
