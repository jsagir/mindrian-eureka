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

Written by plan 19.
