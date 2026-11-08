# Hub figure rules

Phase 2.3.1 plan 04 (D-07, HUB-06, HUB-04). Owner words of 2026-11-08: the pictures must show the core of each opportunity, not a generic image, and anyone must be able to make them with no image generator. The hub draws every picture itself, as SVG, from the run data and the run's own record text, with the standard library only. The same run gives the same bytes. The code is `src/mindrian_eureka/hub/figures.py`; the strings are in `figure_copy.py`.

## What a picture shows

One lead. A lead is a pair of records that one engine ranked. The picture shows the two records, the proposed link between them, how strongly each engine reads the pair (the meaning score and the wording score), and the words that make each record distinctive and that the two records share. Nothing in a picture is a claim. The words are a screening aid for a person who decides where to read first.

## The two variants

The card carries the core of the lead in a few words (plan 10, 2026-11-08; owner words: the images must represent the core of the opportunity, not a generic image). Two record markers at the top, record A at the left and record B at the right, joined by a dashed link. Under each marker the `CARD_WORDS` (3) most distinctive words of that record, as small mono labels in the display form of hub-terms-rules.md step 7. On the link a chip with the words both records share, when any. Below, the meaning bar and the wording bar, one ink square for each shared word, and the blocks. It is the small picture of a bank row, a catalogue thumbnail and the reading panel. Its title and its description carry the same words and the real numbers for a screen reader. Two pairs with different words give two different cards; two pairs with the same words differ only in the position of the vertical rule.

The detail has text inside: each record's title, its 5 distinctive words, the two scores and the words both records share. It is the big picture of a pair page. Under 768 px the page shows an HTML twin with the same words as real text (plan 08), because the drawn text would fall under the 13 px floor.

Every word in a card or a detail is a display form: the most frequent whole surface form of the stem in the record's own text (hub-terms-rules.md, step 7). A cut stem such as `claus` never shows.

## Encoding table

Canvas for both variants: `viewBox 0 0 1400 934` (the size of the target's pictures). Ground: a paper rectangle. Frame: inset 3, stroke 6, no fill.

The card:

| Element | Shape and place | Data | Source field | Role word |
|---------|-----------------|------|--------------|-----------|
| Rule | ink line, width 6, at x R from y 0 to 934; R = 1100 + 20 * (first byte of sha256(pair id) modulo 3) | none; the description says it is structure, not data | pair_id | structure |
| Marker A, marker B | white rectangles with an ink stroke 5, 110 by 110, at (70, 60) and (870, 60), each with an ink square of 36 in its top left corner | none; they stand for the two records | left, right | record |
| Link | dashed ink line, width 8, dash 28 on and 32 off, from x 190 to x 860 at y 115 | none; it stands for the proposed pair | pair | Proposed |
| Record A words | up to 3 mono labels (class f-label, 60 units, or f-label-s, 44 units) at x 70, baselines 254, 326 and 398, in column A (x 70 to 510) | the display forms of the first 3 distinctive words of record A | terms.records[left] | distinctive words |
| Record B words | the same labels right-aligned by computation to x 980: x = 980 minus the label width, in column B (x 540 to 980) | the first 3 distinctive words of record B | terms.records[right] | distinctive words |
| Shared chip | paper rectangle with an ink stroke 3 (class f-chip), height 52, at y 89, centred on x 525, width = label width + 30; text in f-label-s f-chip-t at (chip x + 15, 125): the shared words joined by a comma and a space while the text has 22 characters or fewer; no chip when no word is shared or the first word alone is longer than 22 | the shared words | terms.pairs[pair_id] | shared words |
| Ticks | 3 ink lines, width 2, opacity .35, at x 70, 525 and 980 from y 440 to 760 | the scale: lo, the middle and hi | engine scale | scale |
| Meaning bar | cobalt rectangle at (70, 470), height 110, width round(910 * t), at least 8 | meaning score | meaning | meaning score |
| Wording bar | red rectangle at (70, 620), height 110, same width rule | wording score | wording | wording score |
| Shared squares | ink squares 64 by 64 at x 70 + 96 * i, y 790, one for each shared word, at most 8 | number of shared words | terms.pairs[pair_id] | shared words |
| Cobalt block | cobalt rectangle from x R + 3 to 1397, y 150, height 140 | both engines list the pair and the second signal confirmed it | both engine lists, confirmed | agreement |
| Yellow block | yellow rectangle with an ink stroke 6, same x, y 3, height 140 | a record of the pair is a Potential eureka | records[].bridge | Potential eureka |

Card label rule (`card_label`, `label_width`): a word of 11 letters or fewer is drawn whole in f-label (60 units); 12 to 15 letters in f-label-s (44 units); a longer word is cut to its first 12 letters plus three ASCII dots and drawn in f-label-s; the description lists the whole word. The label width is `len * size * 66 / 100` rounded up (the mono advance 0.6 with the 10 percent margin of the width model, in exact integer arithmetic), so an 11-letter label at 60 units is 436 units wide and stays in its column. The card draws, in this order: ground, rule, markers, link, shared chip, record A words, record B words, ticks, meaning bar, wording bar, squares, blocks. `CARD_WORDS` is 3; the orchestrator allowed 2 or 3, and 3 is used because every measured card stays under the cap (see Sizes).

The detail (coordinates as built; the executor tuned them inside the plan's rules and records them here):

| Element | Shape and place | Data | Source field |
|---------|-----------------|------|--------------|
| Panel A, panel B | white rectangles with an ink stroke 5, 520 by 570, at (50, 100) and (830, 100); an ink strip 22 high at the top of each (no colour meaning) | the two records | left, right |
| Panel label | mono 28, soft, at (x + 14, 166): RECORD A or RECORD B | fixed | labels |
| Title | display 36, bold, ink, wrapped to 22 characters a line, 4 lines at most, three dots at a cut, baselines at 214 + 44 * i, x + 14 | record title | records[].title |
| Words label | mono 28, soft, at (x + 14, 410): DISTINCTIVE WORDS | fixed | labels |
| Word chips | paper rectangles with an ink stroke 3, width 18 * letters + 30, height 52, gap 10, row pitch 62, from (x + 14, 426), wrapping inside the panel; mono 28 ink text at (chip x + 15, chip y + 36) | the 5 distinctive words | terms.records[id] |
| Link | dashed ink line, width 8, dash 28 and 32, from x 570 to 830 at y 400 | the proposed pair | pair |
| Meaning | label MEANING at (600, 236); track 200 by 36 at (600, 250), quiet fill, ink stroke 3; cobalt bar on the track, width by the scale, at least 4; numeral with 2 decimals, display 72, cobalt, baseline 352 | meaning score | meaning |
| Wording | label WORDING at (600, 452); track at (600, 466); red bar; red numeral at baseline 568 | wording score | wording |
| Band | ink rectangle 1300 by 210 at (50, 702); label WORDS BOTH RECORDS SHARE, mono 28, paper, at (78, 750) | the shared words | terms.pairs[pair_id] |
| Band chips | paper rectangles with a paper stroke 3, same chip rule, from (78, 770), at most 6, two rows if needed; mono 28 ink text | the shared words | terms.pairs[pair_id] |
| Band sentence | when no word is shared: body 34, paper, two lines at baselines 818 and 866: No distinctive word is shared. The link is in meaning only. | none | terms.pairs[pair_id] |
| Cobalt block | cobalt rectangle 297 by 70 at (800, 3) | agreement | both engine lists, confirmed |
| Yellow block | yellow rectangle with an ink stroke 6, 297 by 70 at (1100, 3) | Potential eureka | records[].bridge |

A chip word longer than 27 characters is cut to 24 characters and three dots. A chip that would fall below its panel or band is not drawn; the description still lists every word. The description lists all words, both scores with 4 decimals and the scale.

## Class vocabulary

Every shape and text sets a class. The page stylesheet maps each class to a book token, so the theme changes the colours. Each element also carries the light-palette value as a presentation attribute, so the picture reads outside the page.

| Class | Meaning | Rule (token) |
|-------|---------|--------------|
| f-paper | ground | fill paper |
| f-frame | frame | no fill, stroke ink, width 6 |
| f-rule | vertical or horizontal rule | stroke ink, width 6 |
| f-panel | record marker or record panel | fill white, stroke ink, width 5 |
| f-ink | ink block, ink strip, shared-word square | fill ink |
| f-blue | meaning bar, cobalt agreement block | fill blue |
| f-red | wording bar | fill red |
| f-yellow | Potential eureka block | fill yellow, stroke ink, width 6 |
| f-tick | scale tick | stroke ink, width 2, opacity .35 |
| f-link | dashed proposed link | stroke ink, width 8, dash 28 on and 32 off |
| f-track | bar track | fill quiet, stroke ink, width 3 |
| f-band | shared-word band | fill ink |
| f-chip | word chip | fill paper, stroke ink, width 3 |
| f-chip-on | word chip on the band | fill paper, stroke paper, width 3 |
| f-mono | label and chip text of the detail | font code, 28 px, weight 500, fill ink |
| f-label | card word of 11 letters or fewer | font code, 60 px, weight 600, fill ink |
| f-label-s | card word of 12 to 15 letters, a cut word, the shared chip text | font code, 44 px, weight 600, fill ink |
| f-soft | quiet text | fill soft (added to f-mono) |
| f-title | record title | font display, 36 px, weight 700, fill ink |
| f-body | sentence | font body, 34 px, weight 500, fill ink |
| f-num | score numeral | font display, 72 px, weight 700 |
| f-blue-t | text in cobalt | fill blue |
| f-red-t | text in red | fill red |
| f-band-t | text on the band | fill paper |
| f-chip-t | text on a chip | fill ink |

The table holds 25 classes: 14 shapes, 6 text sizes and 5 text modifiers. Plan 10 retired f-fan (the fan was decoration) and added f-label and f-label-s; the page sizes in px are the canvas units of the 1400-unit drawing, so a 60-unit label is 60 px only when the card is drawn 1400 px wide.

The light palette: paper #F7F5EE, white #FFFFFF, ink #111111, soft #4B4943, quiet #ECEAE2, cobalt #1F3FBF, red #D6281F, yellow #F2C200. No other colour value appears in a figure.

## Why the card words are small

At the 300 px bank column (plan 06) a 60-unit label is about 12.9 px tall and a 44-unit label about 9.4 px; both are under the 13 px floor of page text. The card is an exposed picture whose title and description carry the same words, and the bank row prints the shared words and the titles as real text, so the 13 px floor of page text is kept by the page, not by the picture. The detail and its HTML twin are the readable form. At 1400 px (a pair page) the labels are 60 px and 44 px.

## Scale

The wording engine declares a 0 to 1 scale, so its bars run from 0 to 1. The unusual-pairs engine puts both scores on a common scale that is not 0 to 1 (the public fixture's meaning scores reach 1.299088). For that engine the scale ends are the smallest and the largest of 0, 1 and every wording or meaning score of its shown pairs. A bar length is `(score - lo) / (hi - lo)` of the track, clamped to 0 to 1, in whole units (halves up). The description names the scale in numbers: `on a scale from 0 to 1.2991`. A clamp to 0 to 1 would clip real scores, so it was not used.

## Colour roles

Cobalt is the meaning bar and the agreement block. Red is the wording bar. Yellow is the Potential eureka block only. Ink and paper are structure, text, markers and the band. Every yellow block carries an ink stroke of 6, so it never touches paper without a line. A reading never rests on colour alone: a number or a word sits beside every colour in the detail, and the card's description names every mark.

Red and cobalt as data colours (the prototype that the owner saw) differ from the book meaning (red is an interruption, cobalt is inquiry): owner ruling O-02, logged as a deviation for the book. Differences from the prototype of 2026-11-08, decided in this plan: the record panels have a neutral ink strip (the prototype coloured them cobalt and red, which gave one colour two meanings); the agreement block is cobalt, not yellow; the bar scale is the engine's declared scale, not a clamp; the detail text is at least 28 units; the chip width is 18 units a letter (the plan said 17; 18 keeps every chip word inside its chip by the width model).

## The yellow decision

The book allows yellow for a possibility, a tension or a reframe (`foundations/color`). The prototype used yellow for agreement between the two engines. The book has no such meaning, and a gold mark on an agreement can read as a better result (brand rule 15: highlighting never upgrades evidence status). This plan uses cobalt for the agreement block and keeps yellow for a Potential eureka (owner default O-03). The owner may choose otherwise; the switch is one class in one place.

## What a picture never shows

Novelty, evidence, demand or value. Position is not a score: the markers and the word labels sit at the same place in every card. The fan of plan 04 was decoration and is retired (plan 10); the only seeded element left is the position of the vertical rule, which is structure, and the description says so. The words are a screening aid, not evidence; the limit sentence is in every description and the label `candidate, not verified` ends it. The HTML next to every picture keeps the label and the word Proposed beside the dashed link.

## Text and safety

Record text enters a figure in two forms only: a title and words. A title is wrapped, XML-escaped (`<`, `>`, `&` and both quote characters), and its en dash and em dash are folded to a hyphen; nothing else of a title changes. An empty title shows `(no title)`. A word is lower-case letters and hyphens only (plan 02). So a hostile title becomes escaped text, never markup.

A figure holds only the 7 tags `svg`, `title`, `desc`, `rect`, `line`, `circle` and `text`, and only the 21 attributes `xmlns`, `viewBox`, `role`, `class`, `x`, `y`, `width`, `height`, `x1`, `y1`, `x2`, `y2`, `cx`, `cy`, `r`, `fill`, `stroke`, `stroke-width`, `stroke-dasharray`, `opacity` and `font-size`. No `id`, no `href`, no `style`, no handler, no `image`, no `script`, no `foreignObject`, no declaration. `figure_problems` checks all of this and runs in the generator tests and in `verify_payload`; a build refuses a payload with a problem.

## Sizes

The caps are set by measurement, each the largest measured value rounded up to the next 1024 bytes. Plan 04 measured on 2026-11-08 over the public fixture, the hostile synthetic run and the 2000-record scale run: cards 2432 to 3123 bytes, details 4762 to 6880 bytes. Plan 10 (the same day, cards with words and no fan, display forms in both variants) measured over the same three runs: cards 2279 to 3220 bytes (public 2279 to 3220, hostile 2281 to 3183, scale 2900 to 3171), details 4762 to 6884 bytes (public 5249 to 6884, hostile 4762 to 6220, scale 5804 to 6208). The 7 fan lines cost about 735 bytes; the 6 labels, the chip and the two description sentences cost about the same, so the cards did not grow. `CARD_MAX_BYTES` stays 4096 and `DETAIL_MAX_BYTES` stays 7168; `CARD_WORDS` is 3 (the cap did not move). The six goldens of plan 10: pair-both-engines-card 2501 (plan 04: 2615), pair-wording-only-card 2629 (2514), pair-unusual-only-card 2303 (2445), pair-both-engines-detail 5813 (5801), pair-shared-words-detail 5630 (5628), pair-no-shared-detail 5599 (5599) bytes.

5054 bytes is the size of the one hand-built SVG of the target site. It is a hard ceiling for a card: a card above it fails the tests and the payload check. It is not a goal, and it does not bind the detail, which carries text.

## The target's own picture

Kept from the target's hand-built SVG: the paper ground, the 6 px ink frame, the vertical ink rule at the right, flat cobalt, red and yellow blocks. Changed: the thin fan lines of the target are no longer kept (plan 04 called them decoration; plan 10 retired them, because they had no readable meaning and their bytes pay for the words); the card and the detail carry text from the run; there is no photograph and no image generator; the data shapes (bars, squares, blocks) carry real values with fixed positions.

## Storage

Decision of plan 10 (2026-11-08): the figures stay inline in `hub-data.js`, inside the payload, under `figures.pairs[key].card` and `.detail`. No figure file is written next to `hub.html`.

Four reasons, all proven by reading the code and the tests:

1. The hub opens from `file://` and its content security policy says `connect-src 'none'`, so the page cannot fetch a figure file at run time.
2. An `img` element cannot follow the `data-theme` toggle. Plan 05 tests that the figure shapes follow the theme through the class rules of `hub.css`, which needs the SVG inline in the document.
3. A locked hub must hold no svg text, no word and no title in clear (`test_locked_build_holds_no_word_and_no_figure_in_clear`, which now also checks the shared words and the class `f-label`). Plain figure files next to `hub.html` would leak the words of a locked hub.
4. Plans 03, 05, 06, 07 and 08 read `HubApp.data.figures.pairs[key]` synchronously through `HubApp.figure`. A separate store needs script shards with per-shard envelopes and asynchronous consumers.

The budget. The escaped cost of one pair key in `hub-data.js` (both figures after JSON and script escaping) is `PAYLOAD_COST_PER_KEY_MAX` = 16896 bytes, the two caps 4096 and 7168 times 1.5. Measured on 2026-11-08 by `test_scale_cost_is_measured` on the 2000-record run with 200 pair keys: 12669 bytes a key (`hub-data.js` 4566857 bytes with figures and terms, 2033013 without; figures 1795864 bytes raw). `test_scale_3000` bounds `hub-data.js` of the 3000-record run (400 pair keys) at 12000000 bytes; measured 9993906 bytes (9946779 with the plan 04 cards; 5021056 before the words and the figures). The public fixture (36 records, 263 pair keys) gives a `hub-data.js` of 3106070 bytes (3122578 with the plan 04 cards, 393655 before the words and the figures).

The load-time probe. `tests/hub_browser/checks/load-timing.js` reads the navigation timing entry of the 2000-record hub in Chromium and returns `domContentLoadedEventEnd`, `loadEventEnd`, `duration`, the ready state and the count of rendered bank rows. `test_scale_hub_load_time_is_measured` prints the line and bounds `loadEventEnd` at 5000 ms, a generous first bound that is ASSUMED until measured on the owner's machine. Plan 09 copies the printed JSON of this test and of `test_scale_3000` into the Measurements part of the Phase 2.3.1 look record.

The alternative, recorded and not built: script shards under `hub-figures/`, one shard for a group of pair keys, loaded by a `script` element on demand, each shard an encrypted envelope in a locked hub, with asynchronous consumers in every view. Trigger: a follow-up plan opens after plan 08 if the measured `loadEventEnd` of the 2000-record hub passes 2000 ms in Chromium on the owner's machine, or if the owner says the page is slow.

## Book citations

- `segments/experience/visual-language/entries/2026-10-20/GUIDE.md`: choose the encoding first; position is not a numerical score; a connector is not proof; the complete still. Applied: the encoding table above, fixed marker positions, the dashed link with the word Proposed in the HTML, no motion.
- `segments/foundations/color`: cobalt is inquiry and attention, red is interruption, yellow is possibility; dashed plus the word Proposed for an untested connection; dash values scale with the figure when the figure records them; keep accents restrained. Applied: yellow for a Potential eureka only; the dash pair 28 and 32 (the specimen 7 and 8 scaled by 4), recorded here; paper, white and ink take most of every picture.
- `references/brand-rules.md` rules 5 (keep facts, assumptions, proposed connections and results distinct), 15 (highlighting never upgrades evidence status), 17 (rendering preflight: no image generator is required), 18 (visual explanation grammar) and 20 (geometry follows meaning).

## Book silent, proposed segment

Book silent, proposed segment: lead figure. A data-driven picture of a lead, made by code from the run's own words, with its encoding table printed in words. Proposal: the encoding table of this file.

## Tests

`tests/test_hub_figures.py` pins the goldens, the determinism, the safety allow-lists, the class vocabulary (25 classes), the size caps, the card encoding, the card words and the seeded rule (`test_card_carries_the_words_and_the_rule_is_seeded_by_the_pair_id`), the label sizes and cuts (`test_card_word_sizes_and_cuts`), the shared chip (`test_shared_chip_rule`), the detail text, the width model for cards and details, the frame and overlap rules, the honesty of every description, the figure copy and this file. `tests/test_hub_figures_payload.py` pins the payload keys, the verify checks, the locked privacy, the folder scans, the hostile run and the measured cost. The goldens live in `tests/fixtures/hub_figures/`.

To rewrite a golden on purpose: delete the six files, run the golden test with `EUREKA_WRITE_FIGURE_GOLDENS=1` (it writes them and fails with `golden written, review it`), render the new files to PNG outside the repository and look at them, then commit with the reason. The write run always fails, so a rewrite is never silent.
