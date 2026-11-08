"""Copy deck part: the light and dark theme (Phase 2.3.1, plan 05 owns this part).

`deck.py` merges `COPY` into `DECK`. A key that another part or the base deck already
defines raises at import. Keys follow the copy-deck ID rule of the UI-SPEC: the three theme
strings are sub keys of G03 (the header), so the UI-SPEC row count does not change.

Import rule: the standard library only. ASCII only, no dash character.
"""

from __future__ import annotations

COPY: dict[str, str] = {
    # The fixed accessible name of the header toggle (aria-label); it never changes.
    "G03.theme.name": "Dark mode",
    # The visible word on the toggle: the name of the theme that is on now.
    "G03.theme.dark": "Dark",
    "G03.theme.light": "Light",
}
