"""Copy deck part: the finding rows of the opportunity bank (Phase 2.3.1, plan 06 owns this part).

`deck.py` merges `COPY` into `DECK`. A key that another part or the base deck already
defines raises at import. Keys follow the copy-deck ID rule of the UI-SPEC.

Import rule: the standard library only. ASCII only, no dash character.
"""

from __future__ import annotations

COPY: dict[str, str] = {}
