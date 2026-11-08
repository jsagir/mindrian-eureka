# Hub theme rules: the light and the dark theme

Phase 2.3.1, plan 05. Owner request of 2026-11-08: "need to add dark/light toggle" (requirement HUB-10). This record holds the token table of both themes, the measured contrast of every pair the page uses, the default rule, the storage rule, the no flash rule, the lockup and face rule, and the book status. The dark values are a proposal, not book values.

## What the toggle does

The header holds a button, `#hub-theme`. Its accessible name is fixed: "Dark mode" (`aria-label`). Its visible word names the theme that is on now: "Light" or "Dark". `aria-pressed` is `true` while the dark theme is on and `false` while the light theme is on. The button is at least 44 px high and wide at every width. One click switches the theme; the next click switches it back. Without JavaScript the button is not shown (`.no-js .hub-theme-toggle { display: none; }`), because a dead control is never shown; the system preference still applies through the stylesheet.

The button carries a decorative square mark (half filled) from 768 px. Under 768 px the mark is not drawn: the header links row scrolls sideways on a phone (plan 03), and the mark pushed the toggle's word past the edge of a 390 px screen. Measured in Chromium on 2026-11-08 (plan 11): at 390 px the row content is 343 px in a 350 px box and the toggle is 44 px wide with its word whole in both themes; at 320 px the row content is 343 px in a 280 px box, so the row scrolls sideways by 63 px, as the plan 03 rule says, and nothing is cut. The toggle and the Data check link never shrink (`flex: none`); the toggle's phone padding is 4 px with the word centred; the 13 px padding returns from 768 px with the mark. The gaps of the links row are 12 px under 768 px (16 px from 768 px): the Data check link is 99 px at its natural width, and with 16 px gaps the row was 351 px, 1 px over the box. Before plan 11 the row squeezed both controls to 44 px at 320 px and cut their words. The toggle is 44 px high at every width and adds no height to the header (76 px at 1280 px, 115 px at 390 px).

The theme is one attribute on the root element, `data-theme="dark"` or `data-theme="light"`. Every colour of the page reads a token, so one attribute changes the page, the band, the figures, the panel and the graph chrome.

## Token table

Light values are the book tokens (`tokens.css`, byte-identical to the book file). Dark values are a proposal from the prototype of 2026-11-08; two values are the planner's choice and are marked.

| Token | Light (book) | Dark (proposal) | Used for |
|-------|--------------|-----------------|----------|
| `--mos-paper` | #F7F5EE | #121210 | page ground |
| `--mos-white` | #FFFFFF | #1B1A17 | panels, fields, the selected row |
| `--mos-quiet` | #ECEAE2 | #22211D | quiet panels, tracks |
| `--mos-ink` | #111111 | #F4F2EA | text, rules, frames, the band ground |
| `--mos-soft` | #4B4943 | #B8B5AA | secondary text |
| `--hub-line` | `var(--mos-paper-dim)` (#C7C6BF) | #3A3833 | hairlines on the page ground |
| `--mos-blue` | #1F3FBF | #8FA2FF | links, meaning, eyebrow |
| `--mos-red` | #D6281F | #FF7468 | rank index, wording, flags |
| `--mos-yellow` | #F2C200 | #F2C200 | possibility mark (unchanged) |
| `--mos-paper-dim` | #C7C6BF | #4B4943 (planner's choice) | secondary text on the ink ground (the band) |
| `--mos-ink-hairline` | #595954 | #B8B5AA (planner's choice) | hairline on the ink ground |
| `--hub-ring` | transparent | `var(--mos-ink)` | 3 px ring around the Theo tile on the dark page |
| `--hub-dim` | #D8D4C8 | `var(--hub-line)` | dimmed nodes and lines in the graph (plan 07 reads it) |

The dark set sits in `hub-theme.css` under `:root[data-theme="dark"]` and, as the same list, under `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) }`. The sheet also sets `color-scheme` (light or dark) so form controls and scrollbars follow. `hub-theme.css` is the last sheet in the page, so its rules win over equal rules of the other sheets.

## Contrast table

Measured by `tests/test_hub_theme.py::test_token_tables_and_contrast` on 2026-11-08 (WCAG 2 ratio). The floor is 4.5 for text and 3.0 for the focus ring. A pair with "report" has no floor and is recorded only.

| Theme | Pair | Text | Ground | Ratio | Floor |
|-------|------|------|--------|-------|-------|
| light | ink on paper | #111111 | #F7F5EE | 17.31 | 4.5 |
| light | soft on paper | #4B4943 | #F7F5EE | 8.25 | 4.5 |
| light | cobalt on paper | #1F3FBF | #F7F5EE | 7.63 | 4.5 |
| light | red on paper | #D6281F | #F7F5EE | 4.60 | 4.5 |
| light | ink on white | #111111 | #FFFFFF | 18.88 | 4.5 |
| light | soft on white | #4B4943 | #FFFFFF | 9.00 | 4.5 |
| light | cobalt on white | #1F3FBF | #FFFFFF | 8.33 | 4.5 |
| light | red on white | #D6281F | #FFFFFF | 5.02 | 4.5 |
| light | ink on quiet | #111111 | #ECEAE2 | 15.68 | 4.5 |
| light | soft on quiet | #4B4943 | #ECEAE2 | 7.47 | 4.5 |
| light | cobalt on quiet | #1F3FBF | #ECEAE2 | 6.91 | 4.5 |
| light | red on quiet (not used) | #D6281F | #ECEAE2 | 4.17 | report |
| light | paper on ink (band) | #F7F5EE | #111111 | 17.31 | 4.5 |
| light | paper-dim on ink (band secondary) | #C7C6BF | #111111 | 11.02 | 4.5 |
| light | text on yellow | #111111 | #F2C200 | 11.23 | 4.5 |
| light | focus ring on the band | #F2C200 | #111111 | 11.23 | 3.0 |
| light | line on paper | #C7C6BF | #F7F5EE | 1.57 | report |
| light | ink-hairline on ink | #595954 | #111111 | 2.68 | report |
| dark | ink on paper | #F4F2EA | #121210 | 16.73 | 4.5 |
| dark | soft on paper | #B8B5AA | #121210 | 9.13 | 4.5 |
| dark | cobalt on paper | #8FA2FF | #121210 | 7.84 | 4.5 |
| dark | red on paper | #FF7468 | #121210 | 7.10 | 4.5 |
| dark | ink on white | #F4F2EA | #1B1A17 | 15.53 | 4.5 |
| dark | soft on white | #B8B5AA | #1B1A17 | 8.48 | 4.5 |
| dark | cobalt on white | #8FA2FF | #1B1A17 | 7.28 | 4.5 |
| dark | red on white | #FF7468 | #1B1A17 | 6.59 | 4.5 |
| dark | ink on quiet | #F4F2EA | #22211D | 14.38 | 4.5 |
| dark | soft on quiet | #B8B5AA | #22211D | 7.85 | 4.5 |
| dark | cobalt on quiet | #8FA2FF | #22211D | 6.74 | 4.5 |
| dark | red on quiet | #FF7468 | #22211D | 6.10 | report |
| dark | paper on ink (band) | #121210 | #F4F2EA | 16.73 | 4.5 |
| dark | paper-dim on ink (band secondary) | #4B4943 | #F4F2EA | 8.03 | 4.5 |
| dark | text on yellow | #121210 | #F2C200 | 11.16 | 4.5 |
| dark | focus ring on the band | #121210 | #F4F2EA | 16.73 | 3.0 |
| dark | line on paper | #3A3833 | #121210 | 1.60 | report |
| dark | ink-hairline on ink | #B8B5AA | #F4F2EA | 1.83 | report |

The light values on paper (17.31, 8.25, 7.63, 4.60) equal the book report. The dark values on paper (16.73, 9.13, 7.84, 7.10) equal the prototype measurement of 2026-11-08.

Two dark rules follow from the table and live in `hub-theme.css` with token values only:

- Text on a yellow block (`.hub-role--bridge`, `.hub-graph-chip`) uses the paper token in dark. The ink token is light in dark, and light text on yellow measures 1.50; the paper token measures 11.16.
- The focus ring on the ink ground (`.mos-ground-ink :focus-visible`) uses the paper token in dark. The band is light in dark, and the book's yellow ring on it would measure 1.50; the paper ring measures 16.73.

The band in dark: the band reads the ink token for its ground and the paper token for its text, so in dark it is a light band on a dark page with dark text (the same as the prototype of 2026-11-08). The figure band (`.f-band`) does the same. A dark band on a dark page would need a token of its own; the plan allows no new token, so the inversion is the recorded choice. The owner may ask for a band token at the plan 09 brand stop.

## Default and choice

- The system preference is the default: with no saved choice the page follows `prefers-color-scheme`. The media block of `hub-theme.css` applies the dark set when the system is dark and no choice is saved.
- An explicit choice wins: `data-theme` on the root element overrides the system preference in both directions (a saved `light` on a dark system gives a light page).
- The choice is kept in `localStorage` under the one key `hub-theme`, with the two values `dark` and `light`. This is the only storage use of the whole hub. The rule test (`tests/test_hub_js_rules.py`) allows `localStorage` only in `hub-boot.js` and `hub-theme.js`, only with this key, only with these values, and only inside a `try` block. The passphrase and the run data are never stored.
- Every storage call sits inside `try` and `catch`. When storage is missing or blocked the page loads, no error is raised, and the toggle still switches the theme for the session.
- A stored value that is not exactly `dark` or `light` is ignored; the page stays on the default.
- When the system preference changes while the page is open and no choice is saved, the toggle re-reads its state and the page emits the theme event.

## No flash

`hub-boot.js` is the one external script that runs in the head before the first paint (no `defer`). It reads the saved choice and sets `data-theme` on the root element inside `try` and `catch`. The dark set then applies before the body paints. No inline script is added; the page has no `style` attribute; the Content-Security-Policy constant and its record (`hub-probe-results.md`) are unchanged. The browser test `test_no_flash` records `data-theme` and the root background at `readystatechange` (interactive) and at `DOMContentLoaded`: with a saved dark choice both already show the dark values; with a dark system and no choice the root background is dark at the same moments.

## Lockup and face

- The header holds two lockup images: the paper lockup (`mos-lockup-paper-v2.svg`) and the book's reverse lockup (`mos-lockup-reverse-v2.svg`, byte-identical to the book file `segments/identity/logo/variants/entries/2026-10-19/asset-aafc7b2563.svg`, sha256 `3033e523efd4f78cafd1ed28fe311251e5f58454491c8aabd783bb456a99236b`, 191114 bytes). The theme shows one of them. No `filter` and no blend mode touch the logo (book `identity/logo`, brand rules 2 and 3: the logo is never restyled; the reverse lockup is the reverse colour identity, not a decision state).
- The Theo face tile keeps its own paper ground and ink frame. On the dark page it gets a 3 px ring in the light colour (`--hub-ring`, the ink token in dark), following the book ink-ground rule: "Draw the tile frame as a paper ring so it does not merge with the ground." In light the ring is transparent, so nothing changes there. No `filter` on the face.

## Figures

Every shape of a generated figure carries a class of the figure class table (plan 04) and `hub.css` maps each class to a token. So a figure follows the theme without a second drawing: the paper ground becomes the dark paper, ink becomes the light ink, cobalt and red become their dark values, and yellow stays yellow. The browser test `test_figures_follow_the_theme` inserts a figure with every class through `HubApp.figure` and measures the computed fills in both themes.

## Book status

Book silent, proposed segment: dark theme. The book gives light values and the ink-ground rules; the dark values here are a proposal measured by the prototype of 2026-11-08 and by the test of this plan. Register item 26 in `hub-design-decisions.md`. Under owner ruling R-01 no book write command ran; read-only `doctor` on 2026-11-08 reported NEEDS-ATTENTION (the book moved since the lock) and is recorded, not fixed.

Cited segments (read from the checkout): `foundations/color` (ink ground: paper for primary text and paper-dim for secondary on an ink ground; protect readable contrast; keep accents restrained), `identity/logo` (the reverse lockup; never restyle the logo), `experience/accessibility` (44 px targets, 3 px focus ring, reduced motion).

## Open items

- The 3D stage of the graph draws its own colours in script (plan 07 owns `hub-graph.js`); it reads `--hub-dim` for dimmed nodes and lines. Any stage colour that does not follow the theme is plan 07's item.
- The pair and record pages (plan 08) inherit the theme through the same tokens; plan 08 checks the page chrome in both themes.
- A band token of its own (a dark band on the dark page) is an owner question for the plan 09 brand stop. The book has no dark set and no band token (checked 2026-11-08, plan 11: no colour token in `~/mos-brand/segments` names dark, and `tokens.json` has no key with band or dark), so plan 11 changed no code; two renders in the session scratchpad folder closeout-11 show the question: band-dark-1280.png (the page band in dark) and figure-band-dark.png (the band of a detail picture in dark).

## Tests

- `tests/test_hub_theme.py`: token tables and contrast, sheet order, dark set completeness, system default, dark rules on tokens only, the asset entry, the copy part, this record.
- `tests/test_hub_browser_theme.py` with `tests/hub_browser/checks/theme-state.js`: the toggle and `aria-pressed`, persistence after reload, system preference, no flash, no storage, target size and keys, lockup and face, figures, the contrast sweep in both themes at 390 and 1280 px, the locked page, the theme event, reduced motion, a hostile stored value. Chromium and Firefox.
- `tests/test_hub_css.py`: dark values allowed only as custom properties in the dark scopes of `hub-theme.css`; `prefers-color-scheme: dark` is an allowed query.
- `tests/test_hub_js_rules.py`: the storage rule above.
- `tests/test_hub_page.py`: the toggle and the two lockups in the header, on the open and the locked page.
