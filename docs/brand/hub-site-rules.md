# Hub site rules: the pair and record pages

Phase 2.3.1 plan 08 (HUB-11, HUB-06). The hub is a small site: every pair and every record opens as a page with a breadcrumb, a Back knob, Previous and Next knobs, a position line and keyboard keys. The owner asked for it on 2026-11-08: "the opps need to be clickable with flow back knobs, it's a mini site". The patterns come from the owner's prototype of that day (section 8). The rules below are the testable form; the browser test is `tests/test_hub_browser_pages.py`.

## 1 Route grammar

Every route is a hash. A hash that starts with `/` follows this grammar; every other hash keeps the Phase 2.1 meaning (a view name, an in-page anchor, a record id, the `record:` prefix).

| Route | Page | Parent | Back target | Position source |
|-------|------|--------|-------------|-----------------|
| `#/` | the Opportunity bank view | none | none | none |
| `#/graph` | the Connection graph view | none | none | none |
| `#/catalogue` | the Catalogue view | none | none | none |
| `#/pair/<engine key>/<rank>` | the pair page | the bank | `#/` | the pairs of that engine sorted by rank, weak pairs included; `Pair n of k` |
| `#/record/<encoded id>` | the record page | the catalogue | `#/catalogue` | the order of the payload records; `Record n of k` |

The rank rule: `<rank>` matches `^[1-9][0-9]{0,8}$` (1 to 9 digits, no leading zero) and a pair with that engine and rank exists in the payload. `<engine key>` must be an own property of the payload engines (`__proto__` and `constructor` are not). The id rule: `<encoded id>` is percent-encoded by `encodeURIComponent`; the page decodes it in a try block and looks it up in the record index (a Map, so a record named `bank`, `hub-results` or `__proto__` opens its own page). Unknown routes: any other text under `/` (a bad rank, a leading zero, an unknown engine, a bad percent code, an empty id, a missing part) shows the existing notice E05 with the typed text and changes nothing else; the page or view that was shown stays.

The old routes keep working: `#bank`, `#graph`, `#catalogue`, `#<id>` (the record in the panel) and `#record:<id>`.

## 2 The Back knob rule

The Back knob is a link to the parent route (`#/` for a pair, `#/catalogue` for a record) with the attribute `data-back` (`bank` or `catalogue`). One listener on the document decides on a plain click (button 0, no modifier key, default not prevented):

- When the previous displayed page is the parent (`HubApp.nav.previous` equals `data-back`) and the history has more than one entry, the knob runs `history.back()`. Nothing is pushed; the history stays clean; the place on the list comes back (section 4).
- Otherwise the knob follows its link and adds one history entry (the person came from a neighbouring page or from another view).
- A page opened by a direct link has no previous page in this document (`nav.previous` is null after the first route), so Back follows the link and never leaves the hub.

`HubApp.nav` tracks `current` and `previous` as a view name or `kind:key` (`pair:<pair key>`, `record:<id>`), so a record whose id is `bank` can never pass as the bank view.

## 3 Keys

| Key | On a page | On a view |
|-----|-----------|-----------|
| ArrowLeft | opens the Previous page when its link exists; nothing at the start of the list | nothing |
| ArrowRight | opens the Next page when its link exists; nothing at the end of the list | nothing |
| Escape | closes the reading panel when it is open; otherwise runs the Back knob | closes the reading panel when it is open |

Guards: none of the keys acts when the default is prevented, when Alt, Ctrl or Meta is down, or when the target is an `input`, a `textarea`, a `select` or an editable element.

## 4 Focus, title, scroll

- On every route change the document title is set: a view sets `G01.<view>`; a pair page sets `G19.doc.pair` (`Pair {n}: {x} and {y} | MindrianOS Eureka`); a record page sets `G19.doc.record`.
- The focus moves to the page heading: a view route focuses the view heading `#hub-title`; a page route focuses the page `h1` (`tabindex="-1"`), with `preventScroll`. The first load of a deep link does not take focus.
- A page opens at its top: `scrollTo(0, 0)` with `behavior: "instant"`.
- Return keeps place: when a page opens from a view, the view's scroll offset and the `href` of the link that was used (the active element, when it is a link inside that view) are saved under `HubApp.nav.scroll` and `HubApp.nav.opener`. When a view route follows a page, the hub focuses the visible link with that `href` (compared as strings, never built into a selector) and restores the scroll offset. When the opener is gone, the focus stays on the view heading.

## 5 Panel and page

Recorded decision: the reading panel stays an overlay for a quick read; a page is the full read. The panel has one link, `Open the full page` (plan 07). When a person opens a page from the panel, the panel closes first (`clearSelection`), then the page takes focus. The panel keeps its Phase 2.1 behaviour on the views.

## 6 The twin and the 768 px switch

The pair page shows the detail figure drawn from the words of the two records, with a real-text HTML twin of the same facts (`section.hub-pair-twin`: both titles, the distinctive words of each record, the shared words or the sentence that none is shared, the labels, both numerals as the payload text, and the description of the drawing). The drawing is `aria-hidden`; the twin is never hidden from assistive technology.

The switch is 768 px (LD-34, an owner decision listed in the report). The arithmetic: the canvas is 1400 units wide and the smallest drawing text is 28 units, so its size on screen is 28 times the drawn width over 1400. At 768 px the content is 708 px wide (768 minus two 30 px gutters) and the text is 14.2 px, over the 13 px floor; at 640 px the content is 600 px wide (two 20 px gutters) and the text is 12.0 px, under the floor. The owner brief said 640 px; the floor rules the switch (LD-34). From 768 px the drawing is shown and the twin is visually hidden (the same declarations as `.hub-visually-hidden`: absolute, 1 px by 1 px, overflow hidden, `clip-path: inset(50%)`, no wrap; never `display: none` or `visibility: hidden`). Below 768 px the twin is shown and the drawing is `display: none`.

The drawing rounds the two scores to 2 decimals (`f-num`); the twin shows the payload text with 4 decimals. The test accepts that difference as the same fact.

## 7 Proposed segment "document pages"

The book is silent on page-to-page knobs, breadcrumbs and keyboard arrows. Each item is a PROPOSAL for the book, built here under owner ruling R-01.

- PS-01 (PROPOSAL) The heading of a page is the display face at `clamp(30px, 3.6vw, 44px)`, line height 1.05, under a 13 px mono eyebrow with the square red dot; the page head ends with a 1 px ink rule.
- PS-02 (PROPOSAL) A missing knob (Previous on the first page, Next on the last) is a dimmed word in a hairline frame, not a control: no `href`, no `tabindex`, no role, `aria-hidden="true"`. No knob is a dead link.
- PS-03 (PROPOSAL) The parent of a page is fixed: a pair goes back to the Opportunity bank, a record to the Catalogue. The Back knob is the first knob, with a 2 px ink border and a left chevron.
- PS-04 (PROPOSAL) Return keeps place: the scroll offset and the link that was used come back when the Back knob returns to the parent; the history is not grown when the previous page was the parent.
- PS-05 (PROPOSAL) ArrowLeft and ArrowRight move between neighbouring pages; Escape runs the Back knob when no panel is open; the keys never act in a form field or with a modifier key.

## 8 Source of the patterns

The owner's prototype of 2026-11-08 (`build_preview2.py`, `test_v2.js`, 24 checks). Not from Refero: Refero is not connected to this session and its library needs a login (open owner item O-12). Every pattern in this file is marked "prototype, not Refero".

## 9 Known limits

- A jump over several history entries (the browser's own Back held down, or a typed route) can make the Back knob land on a neighbouring page, because the rule uses the previous displayed page. The link still works; the hub is never left.
- The scroll offset and the opener are kept for the session only (plain objects on `HubApp.nav`; no storage).
- The 3D graph has no page route of its own; it opens pages through its pair list (`Open this pair`) and the reading panel.
- The twin repeats the facts of the drawing as text; it does not read the positions of the shapes.

## 10 Measured text fit

Measured on 2026-11-09 by `test_detail_text_fits_in_a_real_browser` (Chromium, 1280 px, the vendored fonts loaded: `document.fonts.check` true for JetBrains Mono 500, Figtree 700 and DM Sans 500). Six detail figures were measured with `getBBox()` on every `text` element: on the public fixture the pair with the longest titles, a pair with no shared word, the pair with the most shared words (6) and the first pair; on a synthetic run of 40 records and 40 pairs an engine the first pair and the pair with the longest titles.

| Face | Measured advance per character (fraction of the font size) | Model of plan 04 |
|------|-------------------------------------------------------------|------------------|
| JetBrains Mono (labels, chips, numerals of the band) | 0.5833 (min 0.58334, max 0.58334) | 0.6 times 1.1 margin |
| Figtree (titles, numerals) | 0.424 to 0.580 (the 2-decimal numerals are the widest) | 0.58 times 1.1 margin |
| DM Sans (band sentence) | 0.413 to 0.434 | 0.58 times 1.1 margin |

Largest ratio of a text box width to its container width: 0.811 (a title line in its 520 unit panel). Every box lay inside the canvas and inside its container (chip rect, panel, column or band); no two text boxes overlapped. The width model of plan 04 (mono 0.6, display 0.58, both with a 10 percent margin) is wider than every measured advance, so `figures.py`, the six goldens and `tests/test_hub_figures.py` were not changed (the plan's rule: change them only when a text is wider than its box).
