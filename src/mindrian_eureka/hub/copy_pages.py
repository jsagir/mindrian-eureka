"""Copy deck part: the pair and record pages of the mini site (Phase 2.3.1, plan 08 owns this part).

`deck.py` merges `COPY` into `DECK`. A key that another part or the base deck already
defines raises at import. Keys follow the copy-deck ID rule of the UI-SPEC (family G19,
02.1-UI-SPEC.md section 9.9). The visible text of a Previous or Next knob is `G19.prev`
or `G19.next`; its accessible name is the `.pair` or `.record` key, which holds the visible
word (owner request of 2026-11-08, HUB-11: pages with flow back knobs).

Import rule: the standard library only. ASCII only, no dash character.
"""

from __future__ import annotations

COPY: dict[str, str] = {
    # --- document titles ----------------------------------------------------
    "G19.doc.pair": "Pair {n}: {x} and {y} | MindrianOS Eureka",
    "G19.doc.record": "{title} | MindrianOS Eureka",
    # --- breadcrumb ---------------------------------------------------------
    "G19.crumb.label": "You are here",
    "G19.crumb.bank": "Opportunity bank",
    "G19.crumb.catalogue": "Catalogue",
    "G19.crumb.pair": "Pair {n}",
    # --- knobs --------------------------------------------------------------
    "G19.back.bank": "Back to the opportunity bank",
    "G19.back.catalogue": "Back to the catalogue",
    "G19.knobs.pair": "Move between pairs",
    "G19.knobs.record": "Move between records",
    "G19.prev": "Previous",
    "G19.next": "Next",
    "G19.prev.pair": "Previous pair",
    "G19.next.pair": "Next pair",
    "G19.prev.record": "Previous record",
    "G19.next.record": "Next record",
    "G19.pos.pair": "Pair {n} of {k}",
    "G19.pos.record": "Record {n} of {k}",
    # --- the pair page ------------------------------------------------------
    "G19.pair.eyebrow": "Pair {n} from the {engine}",
    "G19.pair.also": "The {engine} also lists this pair, at rank {n}.",
    "G19.and": "and",
    "G19.twin.heading": "The pair in words",
    # --- the record page ----------------------------------------------------
    "G19.record.read": "Read this record",
    "G19.record.eyebrow": "Record",
    "G19.record.words": "Distinctive words",
    "G19.record.no_words": "No distinctive words could be found for this record.",
    "G19.record.no_pairs": "This record is in none of the pairs of this run.",
    "G19.more": "...",
}
