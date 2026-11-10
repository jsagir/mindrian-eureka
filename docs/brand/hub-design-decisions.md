# Hub design decisions (phase 2.1)

This file records every design choice of the opportunity hub, the book segment that rules it, and the `mos-brand context` line for that segment. The book is the only design authority. Where the book is silent, this file says "book silent, proposed segment" and returns the gap to the book (D-03).

## Status

| Item | Value |
|------|-------|
| Date | 2026-10-24 |
| mos-brand CLI version | 2.43.0 |
| Book commit (`git -C ~/mos-brand rev-parse --short HEAD`) | 9f4ee34 |
| `mos-brand doctor` status | PASS (no problems; limits: technical consistency only, no human approval implied) |
| Context packet | 59 segments, saved to `build/brand-context.json` (ignored by git) |
| Intake | `.mindrian/intake.json`, surfaces website, app-ui, graph-visualization. Confirmed by the owner on 2026-10-24. |
| Human approval | Not given. Visual verification pending. |

The CLI is run by absolute path: `node ~/mos-brand/bin/mos-brand.cjs {command}`. Nothing is installed with npm in this repo. `.mindrian/brand.lock.json` and `.mindrian/WORKFLOW.md` hold the absolute paths of one machine, so git ignores them. A fresh checkout runs `configure --intake .mindrian/intake.json` to rebuild both files.

## Decision table

Segment paths are relative to the book checkout. The context column copies the `path`, `kind` and first `reasons` entry from `build/brand-context.json`.

| Area | Hub choice | Cited segment path | `mos-brand context` line | Plan |
|------|------------|--------------------|--------------------------|------|
| Colour | Paper `#F7F5EE` dominant, white and quiet panels, ink text and lines. Cobalt only for pair lines and the evidence rule. Yellow only for the Potential eureka sphere and chip, always with ink text. Red only for errors and data check flags. No other colour carries meaning. | `segments/foundations/color` | path: foundations/color, kind: task, reason: Declared surface: graph-visualization | 10, 11, 13, 15, 18 |
| Tokens | Token CSS copied unchanged. Radius 0. Spacing steps 4 to 96 px. | `segments/foundations/tokens` | path: foundations/tokens, kind: task, reason: Declared surface: website | 06, 10 |
| Type | Figtree for display, DM Sans for body and UI, JetBrains Mono for IDs and scores. Sizes 40/28, 22/20, 18/17, 16 and 13 px. Weights 400, 600, 700. No italics. | `segments/foundations/typography` | path: foundations/typography, kind: task, reason: Declared surface: website | 06, 10 |
| Layout | 4, 6 and 12 columns. Header bar 64 px. Title band, counts strip, view navigation, active view, reading panel, data check, footer. 44 px targets. 3 px focus ring with 3 px offset. Logical properties only. | `segments/experience/layout` | path: experience/layout, kind: task, reason: Declared surface: website | 08, 10 to 15 |
| Accessibility | 13 px label floor, 44 px targets, contrast table, keyboard routes for every pointer action, reduced motion honoured, no flashing. | `segments/experience/accessibility` | path: experience/accessibility, kind: task, reason: Declared surface: website | 10 to 15, 18, 19 |
| Motion | No ambient motion. Motion only on a person's action. Camera moves use 760 ms, instant under `prefers-reduced-motion`. No pause control because nothing plays. | `segments/experience/motion` and `segments/experience/visual-language/shaper/motion` | path: experience/motion, kind: task, reason: Declared surface: graph-visualization; path: experience/visual-language/shaper/motion, kind: task, reason: Active ruling set shaper-motion-ruling | 10, 15, 18 |
| Graph | Three-dimensional map with a list of pairs, a legend in words, Find, Zoom in, Zoom out, Reset view, a static diagram under 15 records, and the Potential eureka tour. Two deviations are listed below. | `segments/experience/graph-visualization` | path: experience/graph-visualization, kind: task, reason: Declared surface: graph-visualization | 05, 15, 18 |
| CSS capabilities | None required. Any new capability needs `@supports`, an off switch, a tested fallback and a recorded test (rule 21). Default: use none. | `segments/experience/css-capabilities` | path: experience/css-capabilities, kind: task, reason: Declared surface: website | 10 |
| Theo face | Rest before data loads, Handover when ready, Limit for a step that found nothing or failed, Boundary for the locked screen. No Found, Challenge, Contradiction, Search, Listen, Reframe or Your decision state. | `segments/identity/theo/states` | path: identity/theo/states, kind: task, reason: Declared surface: app-ui | 06, 08, 10, 14 |
| Logo and lockup | Exact parent lockup in the header, unchanged, not a link. Favicon is the Theo mark alone. No signature mark for Eureka (D-20). | `segments/identity/logo` | path: identity/logo, kind: task, reason: Declared surface: website | 06, 08 |
| Evidence labels | Every claim and opportunity carries "candidate, not verified" and a source link. A pair does not mean new, wanted or valuable. | `segments/writing/editorial-integrity` | path: writing/editorial-integrity, kind: task, reason: Declared surface: graph-visualization | 03, 05, 11, 13 |
| UI ruling system | Rule set `uiux-ruling-system` applies to the hub, but the CLI reports status "planned", no source and result "not-implemented-not-passed". The hub cannot cite a rule from it. Book silent, proposed segment: the ruling system for UI is not yet written. The hub follows the segments above meanwhile. | rule set `uiux-ruling-system` (status planned, no segment path) | ruleSet id: uiux-ruling-system, status: planned, applies: true, source: none | 19 |
| Copy and voice | Plain English in the voice of the book. No em dash and no en dash. No internal engine abbreviation. Every number has a source or is absent. | `segments/writing/voice` and `segments/writing/punctuation` | path: writing/voice, kind: mandatory, reason: Shared baseline; path: writing/punctuation, kind: mandatory, reason: Shared baseline | 03 to 15, 18 |

## Book-silent register (D-03)

Each item below is "book silent, proposed segment". The hub does what the right-hand text says until the book answers. The list goes back to the book at the final review (plan 19).

1. Offline vendoring of a script library (D-12). Book silent, proposed segment. Hub: vendor a pinned copy, load it by relative path, keep the licence, run two network tests.
2. Password gate (D-17). Book silent, proposed segment. Hub: the default in UI-SPEC section 12, kept by the owner on 2026-10-24.
3. A "filed or bridge" idea for a pairs-only tool (D-14). Book silent, proposed segment. Hub: the "Potential eureka" label. Owner ruling 2026-10-24: keep, label Potential eureka.
4. Exact breakpoint values. Book silent, proposed segment. Hub: phone under 768 px, tablet 768 to 1023 px, desktop 1024 px and up.
5. Phone column gap and tablet page margin. Book silent, proposed segment. Hub: 16 px and 32 px.
6. Theo face size on a page. Book silent, proposed segment. Hub: 64 px from 768 px up, 48 px on phone.
7. Keyboard and button alternative for the 3D camera. Book silent, proposed segment. Hub: Zoom in, Zoom out, Reset view, Find, the tour and the list of pairs.
8. Contrast rule for neighborhood tints and dimmed context. Book silent, proposed segment. Hub: drop the four tints under 3:1; the dimmed state is a deliberate de-emphasis.
9. Telling two engine line kinds apart in 3D. Book silent, proposed segment. Hub: same colour; words, filter, tip and panel tell them apart.
10. Graph guide label floor (12 px) against the accessibility floor (13 px). Book silent, proposed segment. Hub: 13 px. Hub applies 13 px at all widths. The book fails only below 13 px at 1024 px and up. Stricter by choice, proposed segment.
11. Table pattern for a catalogue. Book silent, proposed segment. Hub: a real table from 768 px up.
12. Hash route collisions between view names and record IDs. Book silent, proposed segment. Hub: the `#record:ID` form.
13. One H1 that changes per view. Book silent, proposed segment. Hub: focus and document title change on view switch.
14. Reading panel measure and sheet breakpoint. Book silent, proposed segment. Hub: a 400 px panel at 1024 px and up, a sheet below.
15. Forced-colors and high-contrast mode. Book silent, proposed segment. Hub: not specified; test and report.
16. Camera move timing for a user action. Book silent, proposed segment. Hub: reuse `--mos-time-reframe` 760 ms.
17. Rank-score scale across the two engines. Book silent, proposed segment. Hub: never mix; a potential eureka score uses one engine at a time (plan 05 confirms).
18. Page size and run size limits for the map. Book silent, proposed segment. Hub: none set; plan 05 and plan 19 record a tested limit.

## Deviations from the book guide

These two rows are not counted in the 18 items.

| Item | Book guide | Hub | Reason | Status |
|------|------------|-----|--------|--------|
| 1. Links to a potential eureka (bridge links) and particles | Thick yellow links with red particles (graph guide, GUIDE 17-27) | Cobalt, width 1.6 for crossing pairs, no particles | D-21 no ambient motion (rule 19). Yellow alone is 1.54:1 on paper. | Deviation, not book-derived; proposed segment |
| 2. Camera moves and the motion setting | The guide does not say whether a short camera move needs an in-page motion setting | Camera moves are user-triggered, 760 ms, and instant under prefers-reduced-motion. No in-page motion setting. | They are not substantial or ambient motion. | Book silent, proposed segment. The owner may require one control (Instant camera) at the plan 17 brand stop. |

Exact text of row 1: "Bridge links thick yellow with red particles (GUIDE 17-27) -> hub: cobalt, width 1.6 for crossing pairs, no particles. Reason: D-21 no ambient motion (rule 19), and yellow alone is 1.54:1 on paper. Status: deviation, not book-derived; proposed segment."

Exact text of row 2: "Camera moves are short (760 ms), user-triggered, and instant under prefers-reduced-motion. They are not substantial or ambient motion, so the hub has no in-page motion setting. Status: book silent, proposed segment; the owner may require one control (Instant camera) at the plan 17 brand stop."

Plans 15 and 18 repeat row 1 in code comments and in `docs/brand/hub-model-rules.md`. The hub adds no control for motion.

## OWNER-WORD answers

The owner answered on 2026-10-24 through the main session. All items were approved as written, except where a ruling is named.

- Intake text, the third surface `graph-visualization`, consumer kind `product` and team `MindrianOS Eureka maintainers`: owner approved on 2026-10-24. The third surface is needed so that `mos-brand context` lists colour, the graph guide and motion.
- D-14 owner ruling 2026-10-24: keep, label Potential eureka.
  - The label stays a candidate. It always sits with the hub wording "candidate, not verified" and with the meaning "a place to look, not a result".
  - All user-facing strings say "Potential eureka". The tour button says "Show me the potential eurekas". Code identifiers may keep the word bridge.
  - The yellow sphere and chip, the tour, and the strings Gr09 and P07 stay in plans 05, 13, 15 and 18.
- D-17: keep the password gate as drafted. Owner approved on 2026-10-24. The gate uses AES-GCM, is an optional extra, and protects the file at rest only. It does not protect a machine that already holds the passphrase. The weakness is recorded honestly in the page (L07), in the README and in this file.
  - D-07 uses derived salt and nonce, so repeated inputs produce the same encrypted file and can be linked. An offline guess costs the fixed 600,000 PBKDF2 rounds; the gate protects the hub at rest only. The [gate record](hub-gate-record.md) explains public provenance metadata and the other limits.
- HUB-05 mapping of the October leads page: owner approved on 2026-10-24. The hub reproduces it as the first 16 pairs of the Opportunity bank with their reading panels, plus the "Show me the potential eurekas" tour. The narrative text stays out (CONTEXT deferred list).
- Source-link choice: owner approved on 2026-10-24. The default links to the catalogue row. The optional `--source-dir` option gives file links.
- Workflow reference: owner approved on 2026-10-24. `docs/brand/hub-workflow.md` receives the brand reference. `CLAUDE.md` is not touched.
- Git: owner approved on 2026-10-24. `.mindrian/brand.lock.json` and `.mindrian/WORKFLOW.md` are ignored. `configure` rebuilds them on any machine.

## Brand stop

A person approves before anything publishes. Plan 17 records that approval.

## Records written by later plans

- [hub-model-rules.md](hub-model-rules.md) (plan 05)
- [hub-probe-results.md](hub-probe-results.md) (plan 04)
- [hub-vendor-record.md](hub-vendor-record.md) (plan 06)
- [hub-gate-record.md](hub-gate-record.md) (plan 14)
- [hub-jhtv-view-mapping.md](hub-jhtv-view-mapping.md) (plan 16)
- [hub-review-result.md](hub-review-result.md) (plan 19)

## Review results

Implementation complete; visual verification pending the owner. The [review record](hub-review-result.md) records seven CLI reviews with REVIEW-REQUIRED, no findings and exit 2, measured browser checks, every inspected capture and the remaining human checks. Raw results and public-only images are in the [evidence folder](../../.planning/phases/02.1-opportunity-hub-in-the-mos-brand-format/evidence). Approval remains pending Plan 17; no CLI run approval or publication is recorded.

## Phase 2.3 additions

Plan 02.3-04 (D-04, SEED-05) adds one row under each pair of the bank: the exact seed command, as text to copy. The page runs nothing. Segment paths are relative to the book checkout. The context column copies the `path`, `kind` and first `reasons` entry from `build/brand-context.json` of 2026-10-24. On 2026-11-07 `mos-brand context` and `mos-brand doctor` returned BLOCKED, because the book moved from commit 9f4ee34 to 2263b84 and the installed `tokens.css` differs from the lock. The lines below are therefore not regenerated. All four cited segment paths exist in the book checkout at 2263b84. The lock was not rebuilt in this plan.

| Area | Hub choice | Cited segment path | `mos-brand context` line | Plan |
|------|------------|--------------------|--------------------------|------|
| Layout | The seed row spans the full width of the bank row and is its last child. It holds one chip and one mono text. It is not a `hub-bank-labels` row, so the bank CSS does not place it in the role label cell. The only new CSS is one selector in the full-width list and one flex rule that uses existing spacing tokens. No colour, border, radius or motion is added. | `segments/experience/layout` | path: experience/layout, kind: task, reason: Declared surface: website (build/brand-context.json, 2026-10-24; not regenerated, book moved) | 04 |
| Copy | Label "Start a room from this pair". One hint above the list: "Copy the command under a pair and run it in a terminal. Replace RUN_FOLDER with your run folder. The command writes a new folder that MindrianOS can open as a room. It changes no room." Plain English, no dash, no stack term, no engine word. | `segments/writing/voice` and `segments/writing/punctuation` | path: writing/voice, kind: mandatory, reason: Shared baseline; path: writing/punctuation, kind: mandatory, reason: Shared baseline (build/brand-context.json, 2026-10-24; not regenerated, book moved) | 04 |
| Interaction | The command is text to copy. The page has no copy button, no clipboard code and no handler for the row. A person with a keyboard or a pointer selects the text. No new control is added, so no new target, focus or motion rule applies. | `segments/experience/accessibility` | path: experience/accessibility, kind: task, reason: Declared surface: website (build/brand-context.json, 2026-10-24; not regenerated, book moved) | 04 |

Observation, not changed in this plan: the Phase 2.2 carried-cell row (`hub-bank-extras`) carries the class `hub-bank-labels`, which the bank CSS places at an explicit grid cell. It therefore shares the cell of the role labels. A measurement on 2026-11-07 in Chromium shows the two boxes overlap at 360, 768 and 1280 px, and a captured image shows the text of the chips and the role labels printed over each other. The owner checks this in the visual pass, and the Phase 2.2 visual pass records it. The seed row does not share this cell.

## Phase 2.3.1 look change

The owner rejected the Phase 2.1 look on 2026-11-08 and named a live target site. This section records the ruling, the book status, the colour roles that change, the cited segments and every difference between the hub and the target stylesheet. The older sections above stay as history; where they conflict with this section, this section rules the page look.

| Item | Value |
|------|-------|
| Date | 2026-11-08 |
| mos-brand CLI version | 2.43.0 |
| Book commit (`git -C ~/mos-brand rev-parse --short HEAD`) | 2263b84 |
| `mos-brand doctor` status | NEEDS-ATTENTION, 36 problems (the book moved since the lock; the installed `tokens.css` equals the book file byte for byte, only the lock hash is old) |
| `mos-brand context`, `catalog`, `checklist`, `refresh`, `image templates` | BLOCKED (stale lock). The segment lines of this section are read from the book checkout at 2263b84 and are not regenerated. |
| Brand lock reconciliation | Not approved by the owner (BRAND-LOCK-RECONCILE, 2026-11-08). No book write command runs in this phase. |
| Book review (success criterion 2) | Advisory. Recorded: not run, lock not reconciled, by owner ruling R-01. |
| Human approval | Pending plan 09 (the owner looks at the built hub in both themes). |

1. Owner ruling 2026-11-08. The Phase 2.1 look was not approved. In the owner's words: "looks very bad, the original look was way way way better". The owner named the live target site (the current build of the partner hub). The hub follows its colour roles, its type scale, its header and section pattern, its finding rows and its black band. Reviewer label: Maintainer.

1a. R-01, 2026-11-08. The decisions made in the redesign session overrule the mos-brand book wherever they conflict. In the owner's words: "make sure the decision we made here overshadow the mos brand". The book stays the reference for everything the session did not decide. Where a session decision differs from a book rule, the session decision is built, the difference is logged as an LD row or a register item, and a proposed book segment is written so the book can follow later. BRAND-LOCK-RECONCILE is not approved. No executor runs `mos-brand asset --replace`, `mos-brand refresh --apply`, `mos-brand adopt --apply`, `init`, `configure` or `run approve`. Read-only book commands may run. The book review is advisory and is recorded "not run: lock not reconciled, by owner ruling R-01". It is not a gate. This applies to the hub only.

2. Owner words and checks. Source: `.planning/phases/02.3.1-hub-look-matches-the-live-jhtv-site-cobalt-red-and-yellow-ac/02.3.1-CONTEXT.md`, section Owner words, and `02.3.1-OWNER-DECISIONS.md`. Checks the owner did: looked at the page. Checks the owner did not do (recorded as not done): keyboard-only pass, screen reader, Safari, 200 percent zoom, Theo face states. No name of a person or a partner from the target is stored in this repository (D-06); only the target stylesheet is kept as evidence.

3. Colour. Owner ruling 2026-11-08 overrules the Phase 2.1 colour rule (row Colour of the table of 2026-10-24) for the page look. The old row stays above as history. New roles: cobalt for links, the eyebrow, the header label and row numerals; red for the mono rank index and the eyebrow dot (a square); yellow for the band marker and for a Potential eureka; ink for rules, headings and the band ground; paper dominant. Cited segment: `segments/foundations/color` (palette values, "Keep accents restrained", ink ground, contrast table). Where the book meaning differs (red is an interruption, yellow is a possibility, cobalt is inquiry and attention), owner ruling overrides the book meaning for these decorative uses; proposed segment. The uses are listed in the register below (items 24 and 25) and in the deviation rows LD-13, LD-22, LD-24 and LD-33. Contrast, measured by the review test: cobalt on paper 7.63:1, on white 8.33:1, on quiet 6.91:1; paper on ink 17.4:1; soft on paper 8.5:1. Yellow is never text.

| Area | Hub choice | Cited segment path | Plan |
|------|------------|--------------------|------|
| Colour | Roles of item 3: cobalt links, eyebrow, header label and numerals; red rank index and square eyebrow dot; yellow band marker and Potential eureka; ink rules and band ground. | `segments/foundations/color` | 01, 03, 06 |
| Type | Figtree display, DM Sans body, JetBrains Mono for labels, ids and scores. Body 16 px under 768 px and 17 px from 768 px, line height 1.58. Display heading clamp(34px, 4.2vw, 52px) at line height 1.02 and letter spacing -0.04em. Counts numeral 32 px and 42 px. Labels 13 px (the floor). Weights 400, 600, 700; `font-synthesis: none`. | `segments/foundations/typography` | 03 |
| Layout and sticky header | One wrapper of 1200 px plus two gutters (20 px, 30 px from 768 px). A sticky header on solid paper with the lockup, a two-line context block, the three view links and a bordered action link; two rows under 1024 px, one row from 1024 px. Under 768 px the sub line of the context block is hidden (it would wrap to 4 lines beside the lockup and the sticky header would cover a quarter of a phone screen; the same sentence G05 stays in the footer) and the links row scrolls sideways when it does not fit, as the target's nav does; the phone header is about 104 px. The header sets `--hub-header-height` from its measured height and `scroll-padding-block-start` follows it (the book: a sticky stage sets scroll-padding-top from its own height variable). Active view link: weight 700 and a 2 px ink underline, 44 px high, 13 px text (Beat selector row). | `segments/experience/layout` | 03 |
| Accessibility | 13 px label floor, 44 px targets, 3 px ink focus ring with 3 px offset, reduced motion honoured, no ambient motion, logical properties only. | `segments/experience/accessibility` | 03 |
| CSS capabilities | No blur behind the header (the target uses `backdrop-filter`); rule 21 asks for a fallback, an off switch and a test for a new capability, so the hub uses solid paper instead. | `segments/experience/css-capabilities` | 03 |
| Logo | The exact parent lockup in the header, not a link, 116 px wide under 768 px and 156 px from 768 px. | `segments/identity/logo` | 03 |
| Motion | Unchanged. No hover transform, no smooth scrolling. Only colour, background colour, border colour and underline thickness transition, 200 ms, none under reduced motion. | `segments/experience/motion` | 03 |

Look contract deviations. The contract is `tests/hub_look_contract.py`; the static test `tests/test_hub_look_tokens.py` proves each row against the stored target stylesheet and the hub stylesheets and checks that every id below is explained here.

| Id | Target | Hub | Reason | Plan |
|----|--------|-----|--------|------|
| LD-01 | Line colour #c9c6bd | `--mos-paper-dim` #c7c6bf | Nearest book token; no new colour literal. | 03 |
| LD-02 | Body 17 px, 16 px only at 470 px and under | Body 16 px under 768 px, 17 px from 768 px | The hub has two breakpoints (LD-16). | 03 |
| LD-03 | Heading 35 px at 470 px and under | Heading minimum 34 px (the clamp floor) | One clamp rule for every width; 1 px difference at phone width. | 03 |
| LD-04 | Labels of 12 px and 11 px | 13 px | D-03 floor and the book accessibility segment. | 01, 03, 06 |
| LD-05 | Index column 38 px | 44 px with a two-digit number; the word Rank in hidden text for assistive technology (the prototype of 2026-11-08 does the same) | 44 px targets. | 06 |
| LD-06 | Description colour #393731 | `--mos-soft` | Book token. | 06 |
| LD-07 | Weight 650 | Weight 600 | Book weights 400, 600, 700. | 03 |
| LD-08 | Header on rgba paper with a 10 px blur | Solid paper, no filter | Rule 21 of css-capabilities and the palette test (no functional colour). | 03 |
| LD-09 | Button 48 px, action link about 40 px | Both follow the 44 px floor | Book target size. | 03 |
| LD-10 | Colours on the ink band #eeece5, #d9e1ff, #d4dcff, #c9c6bd | Paper and paper-dim | Book ink ground tokens. | 01 |
| LD-11 | Counts numeral 36 px and 32 px under 760 px and 470 px | 32 px under 768 px, 42 px from 768 px | Two breakpoints (LD-16). | 03 |
| LD-12 | Phone gutter 19 px and 22 px | 20 px, 30 px from 768 px | Book phone gutter. | 03 |
| LD-13 | Eyebrow dot is a circle | A square (radius 0, token `--mos-radius`) | Book radius 0; owner ruling O-08. | 03 |
| LD-14 | Button hover moves up 2 px | No hover transform | The css test bans a transform transition; motion only on colour. | 03 |
| LD-15 | Smooth scrolling | None | No ambient motion; reduced motion by default. | 03 |
| LD-16 | Breakpoints at 470, 760 and 1000 px, desktop first | Two breakpoints, 768 px and 1024 px, mobile first; lockup 116 px and 156 px | Book breakpoints of the Phase 2.1 register (item 4). | 03 |
| LD-17 | Numeral caption beside the numeral | Caption under the numeral | Reads in one column at every width. | 06 |
| LD-18 | Band padding 16 px and 18 px | 16 px and 24 px | Book spacing steps. | 01 |
| LD-19 | Data check panel padding 14 px and 16 px | 16 px and 24 px | Book spacing steps. | 03 |
| LD-20 | Focus ring cobalt, offset 4 px | Ink on paper, offset 3 px | Book Focus row; the exact string is pinned by the css test. | 03 |
| LD-21 | Row padding 19 px and 20 px | 24 px | Book spacing step. | 06 |
| LD-22 | The id in a row is soft code | A cobalt source link | Every pair keeps a source link (D-03); cobalt links (S22). | 06 |
| LD-23 | The row action is a cobalt arrow link | An outlined button named Open this pair and a cobalt text button named Read this pair (the prototype of 2026-11-08 shows one outlined button and one text link in each row; plan 06 kept an ink Read button because of the plan 03 hover pin; plan 11 restyled it and moved the pin to the unlock button) | 44 px target with a clear name. | 06, 11 |
| LD-24 | Primary button ink to cobalt on hover | The same, while the book primary action is cobalt fill | Owner ruling D-01 over the book button. | 03 |
| LD-25 | The target's own catalogue page has a dark ground | Catalogue and panel use the paper look; the dark theme gives the dark one | Owner ruling O-05; the catalogue page is not the named target. | 07 |
| LD-26 | Header 76 px | 76 px (the Phase 2.1 spec said 64 px) | Owner ruling O-07; the owner chose the target. | 03 |
| LD-27 | Finding rows have no picture | A fifth grid column holds the generated figure of a pair | Owner decision D-07. | 06 |
| LD-28 | Photographs made by an image tool | Generated SVG figures | Owner decision D-07: no image generator is needed. | 04, 06, 07, 08 |
| LD-29 | Row title 18 px at line height 1.15 | 20 px under 768 px, 22 px from 768 px, line height 1.25 (prototype 20 px) | Book subheading sizes. | 06 |
| LD-30 | One count at 27 px | Two numerals, meaning in cobalt and wording in red, 40 px from 768 px and 28 px under (prototype 38 px) | Book heading sizes; both scores shown. | 06 |
| LD-31 | Row description 13 px at line height 1.48 | 16 px at line height 1.5 (prototype 15.5 px) | Book UI size. | 06 |
| LD-32 | No dark page | The dark theme values are a proposal | The book is silent on a dark page (register item 26). | 05 |
| LD-33 | Red is an interruption in the book | Red names the wording score and cobalt the meaning score in numerals, bars and figures (prototype of 2026-11-08) | Owner ruling over the book meaning of red; words and numbers sit beside every colour. | 04, 06 |
| LD-34 | Detail picture is a photograph at every width | An SVG from 768 px and a real-text HTML twin under it | The 13 px floor: the owner brief said 640 px, but the figure text must stay at 13 px or more. | 08 |

### Theme (plan 05)

Owner request of 2026-11-08, in the owner's words: "need to add dark/light toggle" (requirement HUB-10). Built by plan 05 on 2026-11-08; the full record is [hub-theme-rules.md](hub-theme-rules.md).

| Item | Value |
|------|-------|
| Status of the dark values | A PROPOSAL. The book is silent on a dark page. Register item 26 below ("the dark theme values"). The light values are the book tokens, unchanged. |
| What the owner saw | The prototype of 2026-11-08 with a working toggle. The hub now offers the same on the book tokens. |
| Where the dark set lives | `hub-theme.css`, the last sheet of the page: `:root[data-theme="dark"]` and the same list under `prefers-color-scheme: dark` when no choice is saved. |
| The toggle | `button#hub-theme` in the header after the Data check link, on the open and the locked page; `aria-pressed`; fixed name "Dark mode"; visible word "Light" or "Dark" (copy keys G03.theme.name, G03.theme.dark, G03.theme.light); 44 px; hidden without JavaScript. |
| The choice | `localStorage` key `hub-theme`, values `dark` and `light`, inside try and catch; the only storage use of the hub; the page works without storage. |
| No flash | `hub-boot.js` sets `data-theme` before the first paint. No inline script; the Content-Security-Policy constant and its record are unchanged. |
| Lockup, face, figures | The book's reverse lockup (byte-identical, `mos-lockup-reverse-v2.svg`) replaces the paper one in dark; no filter (brand rules 2 and 3). The Theo tile keeps its paper ground and gets a 3 px light ring in dark (ink-ground rule). Figures follow through the class rules of plan 03 and the tokens. |
| Contrast | Measured in both themes by `tests/test_hub_theme.py` and swept in the browser by `tests/test_hub_browser_theme.py`; the table is in hub-theme-rules.md. Light on paper: ink 17.31, soft 8.25, cobalt 7.63, red 4.60 (the book report). Dark on paper: ink 16.73, soft 9.13, cobalt 7.84, red 7.10 (the prototype). |
| Dark rules beyond the tokens | Text on a yellow block uses the paper token in dark (ink would be 1.50 on yellow). The focus ring on the ink ground uses the paper token in dark (the band is light there). Both are in `hub-theme.css` with token values only. |
| The band in dark | The band inverts: a light band on the dark page with dark text, as in the prototype. A dark band would need a token of its own; the book has no dark set and no band token (checked 2026-11-08, plan 11), so plan 11 changed no code. Owner question for the plan 09 brand stop. Two renders in the session scratchpad folder closeout-11 show it: band-dark-1280.png (the page band in dark, a light band with dark text) and figure-band-dark.png (the band of a detail picture in dark, the same inversion through the class rule f-band). |
| Book | Under R-01 no book write command ran. Read-only `doctor` on 2026-11-08: NEEDS-ATTENTION, recorded, not fixed. Book silent, proposed segment: dark theme. |

Narrow test extensions of plan 05, each loosened only as far as the dark theme needs, with a positive check in place of the old ban:

- `tests/test_hub_css.py`: the nine dark values are allowed only in `hub-theme.css`, only as the value of a custom property, only inside a rule whose selector names `data-theme="dark"` or inside the `prefers-color-scheme: dark` media block; that query joins the allowed queries. Negative controls: a dark value in another sheet, a dark value as a `color` value, a `max-width` query and a `prefers-color-scheme: light` query all fail.
- `tests/test_hub_js_rules.py`: `localStorage` is allowed only in `hub-boot.js` and `hub-theme.js`, only as `getItem("hub-theme")` or `setItem("hub-theme", value)` with the value `"dark"` or `"light"` (a literal or a name assigned only from those two words), and only inside a `try` block. Every other script keeps the ban. Negative controls: another key, a payload value, a call outside try, the theme key in another script.
- `tests/test_hub_page.py`: the header structure gains the toggle and the second lockup; no old assertion was removed.
- `tests/hub_browser/driver.cjs`: the scenario option `colorScheme` (light, dark, no-preference); every older scenario keeps light.
- `tests/test_hub_browser_core.py::test_focus_order` and `tests/test_hub_browser_shell.py::test_panel_open_keeps_the_header_links_in_one_row`: the toggle is Tab stop 5 before the band link (stop 6), and the header links row has three children. Both pins describe the header of plan 03, which this plan extends on purpose.

### Close-out of wave 3 (plan 11)

Gap plan 11 closed the loose ends that the RISKS and NEXT sections of the SUMMARY files of plans 05, 06, 07 and 10 named, on 2026-11-08, before plan 08 (the pages and the router) and plan 09 (the owner's look). Each item that a test can hold got a failing test first. Measured in Chromium on the public fixture unless the row says otherwise.

| Item | Change | Measured | Test |
|------|--------|----------|------|
| L1 The Read action | `.hub-bank-read` is the prototype's cobalt text button (13 px, 700, underlined, transparent, no border, 44 px block size; contract R10, LD-23, LD-04, LD-09). The plan 03 hover pin moved from the Read button to `#hub-unlock`, the only always visible ink button. | Light rgb(31, 63, 191), dark rgb(143, 162, 255), background transparent, 44 px high, in Chromium and Firefox; the Read button still opens the panel. | `test_read_action_is_a_cobalt_text_button`, `test_primary_button_hover`, R10 in `test_hub_look_parity` |
| L2 The phone header | The toggle and the Data check link never shrink (`flex: none`); the toggle's phone padding is 4 px with the word centred; the links row gaps are 12 px under 768 px (16 px from 768 px). | Before: at 320 px both controls were squeezed to 44 px and their words cut (toggle scrollWidth 45 in a 42 px box; Firefox 58). After: the row content is 343 px; at 390 px it sits in a 350 px box with 7 px of slack and no scroll; at 320 px it scrolls by 63 px in a 280 px box; the toggle is 44 px and the Data check link 99 px; both words whole in both themes and both browsers. | `test_toggle_word_is_whole_at_phone_widths` |
| L3 The figure class list | `FIGURE_CLASSES` of the theme test equals `CLASS_TABLE` of the generator: `f-fan` out, `f-label` and `f-label-s` in. | 25 classes; the old list had 24 with `f-fan`. | `test_figure_class_list_matches_the_generator`, `test_figures_follow_the_theme` |
| L4 The figure attribute lists | One stated relation in `hub-figure-rules.md` (Text and safety): the page list is the generator list plus `aria-hidden` (22 names), the shell test tuple equals the page list in order. | 21, 22, 22 names. | `tests/test_hub_figure_lists.py` (reads all three lists and the sentence) |
| L5 The phone row | The figure caption is a `details.hub-bank-figure-caption` element with the legend summary as a 44 px target, closed under 768 px and open with no summary line from 768 px (one media query, the `open` property, a change listener); the summary sits above the stretched title link like the other controls; the card is 300 px wide on a phone (420 px at most from 768 px). The class is not `hub-bank-caption`, which is the mono caption of a numeral (R08). | First row of the public fixture at 390 px: 1147.3 px before (1153.3 px on the wave 3 tree, 6 px less after L1), 1030.7 px after (the figure part 368.8 to 252.1 px: the card 300 by 200 px and the 44 px summary); the first row at 1280 px stays 414.6 px. The test's synthetic run: 910.7 px. Bound 1050 px = the tallest prototype row at 390 px (940.3 px) + the shared words line (24 px) + the summary (44 px) + two grid gaps (24 px) = 1032.3 px, rounded up. The 280 px fallback was not needed. | `test_phone_row_is_bounded_and_the_caption_folds`, `test_row_has_the_prototype_parts`, `test_widths_and_reduced_motion` |
| L6 HUB-06 | The clause "small card picture (no text)" became "it carries the records' distinctive words and the shared words; no sentence" in `02.3.1-REQUIREMENTS-NOTE.md` and `.planning/REQUIREMENTS.md`, with the amendment line that names gap plan 02.3.1-10. | grep: "(no text)" 0 times, "no sentence" once in each file. | grep in the plan verification |
| L7 The band in dark | No code: the book has no dark set and no band token (checked 2026-11-08). Recorded as an owner question for plan 09 with two renders in the session scratchpad folder closeout-11: band-dark-1280.png and figure-band-dark.png. | The page band and the figure band invert to a light band with dark text (16.73). | `test_hub_decisions` (this record), `test_record_document` (theme rules) |

### Results of the build (plan 09)

Plan 09 collected the evidence of the new look on 2026-11-10 and put it in front of the owner. The record is the section "Phase 2.3.1 look" of [hub-review-result.md](hub-review-result.md); the status there is "Implementation complete; visual verification pending the owner." until the owner answers. The evidence folder is `.planning/phases/02.3.1-hub-look-matches-the-live-jhtv-site-cobalt-red-and-yellow-ac/evidence` (44 screens at 320, 390, 768, 1280 and 1600 px in the light theme and 8 in the dark theme, the inventory `data/files.json`, the read-only doctor result `data/review-status.json` and the two projection provenance files). The Phase 2.1 evidence is untouched (its inventory is re-checked by `tests/test_hub_look_record.py`).

The rules of the phase, one file each, all linked here as the plan asks: [hub-model-rules.md](hub-model-rules.md) (the run reading band and the model limits), [hub-figure-rules.md](hub-figure-rules.md) (the lead figure), [hub-terms-rules.md](hub-terms-rules.md) (the distinctive words), [hub-theme-rules.md](hub-theme-rules.md) (the dark theme) and [hub-site-rules.md](hub-site-rules.md) (the routes, the knobs and the keys).

Tests that prove the look (static unless named as browser tests): `test_hub_look_tokens` (the look contract against the stored target stylesheet, LD-01 to LD-34), `test_hub_look_parity` (browser; computed styles of the shell, the band and the rows), `test_hub_css`, `test_hub_page`, `test_hub_theme` (contrast of both themes), `test_hub_browser_theme` (browser; the toggle, the saved choice, the storage block), `test_hub_browser_review` (browser; the 13 px floor, the 44 px targets, reflow, contrast), `test_hub_browser_shell` (browser; the sticky header and the phone header), `test_hub_browser_bank` (browser; the row parts and the phone row bound), `test_hub_browser_pages` (browser; the routes, the knobs, the keys, focus, the twin and the detail text fit with the vendored fonts), `test_hub_figures` and `test_hub_figures_payload` (the SVG pictures, their sizes and their safety), `test_hub_terms` (the words), `test_hub_pattern` (the band from run numbers), `test_hub_public_example` (two byte-identical builds), `test_hub_scale` (load time and the 3000 record bound), `test_hub_look_record` (this evidence and the record forms).

The carried-cell overlap of Phase 2.2 (the observation above under Phase 2.3 additions: the `hub-bank-extras` row shared the grid cell of the role labels) is resolved: plan 06 rebuilt the row grid, and `test_hub_browser_bank::test_row_has_the_prototype_parts` measures that no two parts of a row overlap at 390 and 1280 px.

Decisions of the later plans carried into this record:

- Plan 07: the graph canvas re-reads the tokens on the theme event (register item 30 below).
- Plan 08: the empty desktop panel is hidden in page mode (a page is the full read; the panel belongs to the views), and `history.scrollRestoration` is set to manual so that a page opens at its top and a view gets its saved place back through `restorePlace`. Both are owner questions for the look (Q-6 and Q-7 of the record).
- Plan 10: the card carries the top 3 distinctive words of each record and the shared words in a chip; the fan of plan 04 is retired; the only seeded element is the rule position, named structure in the description (D-07, D-09, owner words of 2026-11-08; register item 31 below).

UNVERIFIED after this plan (the record lists each): a keyboard-only pass by a person; a screen reader (the panel announcement with a picture inside, the twin on a pair page); Safari and WebKit; 200 percent zoom; the Theo face states in both themes by a person; real touch; the network page against its stylesheet (matched by screenshot only); the dark values by eye; the owner's own look, which is the brand stop of plan 09 Task 3. The book review is advisory and not run (R-01). Refero was not connected (O-12).

## Book-silent register, Phase 2.3.1

The numbers continue the register of Phase 2.1. Each item is "Book silent, proposed segment"; the hub does what the item says until the book answers.

19. A generated reading of a run (the band of plan 01; rules in `docs/brand/hub-model-rules.md`, section Run reading band). Book silent, proposed segment.
20. A lead figure made by code from the records' own words (plan 04, `docs/brand/hub-figure-rules.md`). Book silent, proposed segment.
21. Header height 76 px and a sticky header on solid paper with the view links inside it (plan 03). Book silent, proposed segment.
22. Hairline colour on paper from the paper-dim token (plan 03, LD-01). Book silent, proposed segment.
23. Cobalt text links in running text (the layout row says underline and readable ink; plan 03, S22). Book silent, proposed segment.
24. Red mono rank index (owner ruling over the book meaning of red; plan 06). Book silent, proposed segment.
25. Yellow square marker in the black band (owner ruling D-01 over the Phase 2.1 colour rule F3 and the book meaning of yellow; plan 01). Book silent, proposed segment.
26. The dark theme values (plan 05, `docs/brand/hub-theme-rules.md`). Book silent, proposed segment.
27. Distinctive words by tf-idf as a screening aid (plan 02, `docs/brand/hub-terms-rules.md`). Book silent, proposed segment.
28. Red names the wording score and cobalt the meaning score (plans 04 and 06). Book silent, proposed segment.
29. Routes, breadcrumbs and the Back, Previous and Next knobs of a mini site (plan 08, `docs/brand/hub-site-rules.md`). Book silent, proposed segment.
30. A canvas that re-reads the colour tokens on a theme event, so the 3D map follows the dark theme (plan 07, carried by plan 09). Book silent, proposed segment: theme-aware canvas.
31. A card picture that carries the records' own distinctive words and the shared words in a chip, with no fan and the rule position as the only seeded element (plan 10, carried by plan 09; `docs/brand/hub-figure-rules.md`). Book silent, proposed segment: lead figure (amended).
