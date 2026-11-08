# Hub model rules

## Pair weights

For each engine, clamp each visible pair's rank score at zero. Divide that value by the largest clamped rank score from the same engine. If the largest value is zero, every pair in that engine has weight zero. Pair links from both engines contribute to the same neighborhood edge by adding their weights. Pair scores are read from the run. The hub does not recalculate them.

## Neighborhoods

Start with one label per record that appears in a visible pair. Visit records in sorted ID order and sum the weights to each neighboring label. Keep the current label when it ties for the largest total. Otherwise choose the smallest tied label. Repeat until a pass makes no change or 100 passes have run. Number groups by size, largest first, then by the smallest record ID. Assign the 21 book tints in order and repeat from the first tint after number 21. A record with no visible pair has no neighborhood.

## Cut-offs and weak pairs

Read each engine's `min_percentile` from its manifest settings. A positive value is the floor and is printed to two decimals. Zero or a missing floor means that engine has no floor. A pair is weak only when it has a percentile below a positive floor. Keep such a pair in the payload with zero weight and minimum width, but exclude it from neighborhoods, bridges, widths, and visible record counts. The weaker-pairs control is useful only when the run includes at least one such pair.

Both engines apply `min_percentile` before ranking, so normal run output can contain no pairs below its own floor. The hub still checks the run data in case a below-floor pair is present.

## Bridges

A Potential eureka is a record with visible pairs into at least two distinct partner neighborhoods. The record's own neighborhood may count as one of those neighborhoods. Within one engine at a time, keep the best pair weight to each partner neighborhood and add the two largest weights. Choose the engine with the larger score for that record. A tie goes to the unusual-pairs engine. Sort records by score, largest first, then by record ID. Mark only the first 16 as bridges. Their label remains `candidate, not verified` and their meaning is a place to look, not a result.

## Data check

Group records with matching non-empty `text_sha256` values. Each member lists the other IDs in sorted order. Count all members of groups with two or more records. Empty text is counted separately and is not an identical-text group. Pair flags mark any pair that touches an identical-text or empty-text record. Copy the dropped-record reasons from the run, grouped by reason and sorted by reason. Shared boilerplate is `not_checked`; no detector runs here. Do not recalculate a score.

## Line widths

For each engine, scale visible same-neighborhood pairs linearly from `0.15` at that engine's lowest visible rank score to `0.5` at its highest. If all scores are equal, use `0.5`. A pair whose ends are in different neighborhoods has width `1.6`. A weak pair has zero weight and width `0.15`.

## Graph earned

The graph is earned when at least 15 distinct records appear in visible pairs. Count only visible pairs. `not_drawn` is the total record count minus the visible record count.

## Source links

By default, each record links to its catalogue fragment through `deep_link`. A writer may pass a relative file link for a record. Each pair side copies the source link of its record. The hub does not create an absolute path or an external link.

## Copy fragments

The model supports these fixed fragments added around B05 and related UI copy:

- `B05.one.unusual_pairs`: `Cut-off: {floor} for the unusual-pairs engine.`
- `B05.one.wording_and_meaning`: `Cut-off: {floor} for the wording engine.`
- `P06.hidden`: `Hidden by default`
- `G03.lockup_alt`: `MindrianOS`
- `C06.one_pair`: `1 pair`

## Run reading band

Phase 2.3.1, D-04 (HUB-07). `describe_run` in `pattern.py` reads the payload and returns a state and a list of lines. Each line is a deck key (family G17, plus Gr09 and G16) and the values of its slots. The same payload gives the same lines. The function reads no clock, no random source and no network.

State rules, in this order:

1. Add the pair counts of both engines. If the total is 0, the state is `none` and the lines are G17.none and G16.
2. Else, if no record is in a pair that is shown (`records_in_visible_pairs` is 0), the state is `hidden` and the lines are G17.hidden and G16.
3. Else build G17.read, then G17.both (only when at least one pair id is in both engine lists), then G17.spread. When there are 2 or more neighborhoods or at least 1 bridge, the state is `grouped`: the next line is G17.hoods, followed by G17.bridges when there is at least 1 bridge, or by Gr09 when there is none. Otherwise the state is `single` and the next line is G17.single.
4. Then, only when true: G17.weak (weak pairs above 0), G17.copies (identical records above 0), G17.classes (the run has pair classes), one G17.top_k line for each engine, in engine order, whose list reached its limit.
5. The last line is always G16.

In the states `none`, `hidden` and `single` the band says in words that the run shows no grouping to read.

Where each number comes from:

| Value | Payload field | Run file behind it |
|-------|---------------|--------------------|
| records (G17.read) | counts.records | corpus file and manifest corpus section |
| a, b (G17.read) | counts.pairs.unusual_pairs, counts.pairs.wording_and_meaning | the two pair files |
| n (G17.both) | count of distinct pair ids with an entry in each engine list | the two pair files (same pair id in both) |
| a, b (G17.spread) | counts.records_in_visible_pairs, counts.records_in_no_pair | the rules "Neighborhoods" and "Cut-offs and weak pairs" over the pair files |
| n, a (G17.hoods) | number of hoods, size of the first hood (hoods are sorted by size, largest first) | the rule "Neighborhoods" |
| n (G17.bridges) | number of bridges | the rule "Bridges" |
| n (G17.weak) | counts.weak_pairs | pair percentile below the manifest floor |
| n (G17.copies) | data_check.identical_records | text_sha256 groups of the corpus file |
| a, b, n (G17.classes) | count of non-weak pair entries by class: cross, open_open, licensed_licensed | the outcome rule of the run (Phase 2.2) |
| engine, n (G17.top_k) | engines[key].short_name, engines[key].top_k | manifest settings top_k, pair file counts.top_k_reached |

The band holds no threshold constant. The code of `pattern.py` uses no numeric literal other than 0, 1 and 2, and a test checks this. The state rules compare counts with 0, 1 and 2 only.

Label wording (owner ruling O-04): "What this run shows", not the target's "The pattern", because the data may show no pattern.

Honesty limits: a value is an int from the payload or one of the two engine short names. No record id, title or text reaches a value. The band makes no claim of novelty, evidence, demand or value; a test bans the claim words in every line except G16, and G16 ends every band. The locked page holds an empty hidden band, so the band text exists only inside the encrypted payload.

Book silent on a generated reading of a run: proposed segment.

## Distinctive words

Phase 2.3.1 plan 02 (HUB-06). The payload key `terms` holds, for every record id, its 5 most distinctive words, and for every pair id the words both records share, at most 6. One rule: `score = tf * log((N + 1) / (df + 0.5))` over the title and the text of each record, scores rounded to 9 decimals, ties broken by the word. The words are a screening aid for a person who decides where to read first. They are never evidence. The full rule, the stop list and the limits are in `hub-terms-rules.md`. `verify_payload` checks that every id is an id of the payload, that a list has at most 5 or 6 words, and that every word is lower-case letters and hyphens of 4 characters or more.

## Figures

Phase 2.3.1 plan 04 (D-07, HUB-06, HUB-04). The payload key `figures` holds `pairs` (for every pair key a `card` and a `detail`, each one SVG string), `legend` (`summary`, `card`, `detail`, `caption`) and `labels` (the 7 fixed words drawn inside a detail). `build_figures` in `figures.py` draws every picture from the payload and the words of `terms`, with the standard library only. The same payload gives the same bytes. The code reads no clock, no random source and no network. The only seed is the pair id and it places decoration only. The encoding is written in `hub-figure-rules.md`.

The two variants (plan 10 rewrote the card on 2026-11-08): the card carries the core in a few words (two record markers at the top joined by a dashed proposed link, the 3 most distinctive words of each record as small mono labels under its marker, a chip on the link with the words both records share, a meaning bar and a wording bar, one ink square for each shared word, a cobalt block for agreement, a yellow block for a Potential eureka; no fan, the only seeded element is the position of the vertical rule). The detail has text (each record's title and its 5 distinctive words as chips, the two scores with bars and numerals, a black band with the shared words or the sentence that no distinctive word is shared). Every word in both variants is the display form of hub-terms-rules.md step 7, never a cut stem.

Agreement rule: a pair gets the cobalt block when its pair id has an entry in both engine lists and a wording-engine entry has `confirmed` true. `confirmed` is the `scores.second_signal.confirmed` flag of the wording engine's pair file; the reader keeps it only when it is a boolean, and the payload writes it only then. The unusual-pairs engine writes no second signal.

Potential eureka rule: a pair gets the yellow block when `bridge` is true for either of its records (the rule "Bridges" above). Yellow has no other use in a figure (book `foundations/color`: yellow is a possibility; owner default O-03).

Every pair entry also carries `reading_kind` (`meaning`, `wording` or `agree`), the kind of its fixed reading sentence, so a page picks its guidance line from the kind and not from the sentence text.

Size caps, measured on 2026-11-08 over the public fixture, the hostile synthetic run and the 2000-record scale run: plan 04 cards 2432 to 3123 bytes, details 4762 to 6880 bytes; plan 10 cards (with the words, without the fan) 2279 to 3220 bytes, details 4762 to 6884 bytes. `CARD_MAX_BYTES` is 4096 and `DETAIL_MAX_BYTES` is 7168 (the largest measured value rounded up to the next 1024 bytes); neither moved in plan 10. 5054 bytes, the size of the one hand-built SVG of the target site, is a hard ceiling for a card and never a goal. `verify_payload` refuses a payload with a figure above its cap, a figure that fails `figure_problems` (7 tags, 21 attributes, no id, no href, no style, no script, no image, no handler), a pair key that is not in the payload, a missing card or detail, or a legend or label string with a dash or an internal name.

Locked privacy (HUB-04): the words and the figures live in the payload only. A locked hub holds them inside the encrypted envelope; `hub.html` and `hub-data.js` of a locked build hold no svg text, no legend string, no distinctive word and no record title. A test proves it on the public fixture.

Measured cost on 2026-11-08 (`tests/test_hub_figures_payload.py::test_scale_cost_is_measured` and `tests/test_hub_writer.py::test_scale_3000`, this machine, 12 logical CPUs):

- 2000 records, 100 pairs for each engine (200 pair keys): figures 1783526 bytes raw; `hub-data.js` 4543244 bytes with figures and terms, 2033013 bytes without; hub build 0.55 seconds.
- 3000 records, 200 pairs for each engine (400 pair keys): `hub-data.js` 9946779 bytes (5021056 bytes on 2026-10-24, before the words and the figures); `hub.html` 212941 bytes; hub build 1.12 seconds (0.31 seconds on 2026-10-24). Two builds were byte-identical.

The data file grows by about 5 to 6 KB of SVG for each pair key, plus the 6-character escapes that `js_assignment` writes for `<`, `>` and `&` inside strings. The scale test fails above pairs times the sum of the two caps.

Storage decision (plan 10, 2026-11-08): the figures stay inline in `hub-data.js`, because the page opens from `file://` under `connect-src 'none'`, an `img` cannot follow the theme toggle, a locked hub must hold no word in clear, and every view reads the figures synchronously. The escaped cost of one pair key is budgeted at `PAYLOAD_COST_PER_KEY_MAX` 16896 bytes (measured 12669 on the 2000-record run), the 3000-record `hub-data.js` is bounded at 12000000 bytes (measured 9993906), and `test_scale_hub_load_time_is_measured` prints the Chromium load time of the 2000-record hub under a 5000 ms bound. The reasons, the budget and the shard alternative are in `hub-figure-rules.md`, section Storage.

Book silent, proposed segment: lead figure (see hub-figure-rules.md).

## Tested size

Measured on 2026-10-24 with `PYTHONPATH=src python3 -m pytest tests/test_hub_writer.py::test_scale_3000 -s -q -p no:cacheprovider`.

- Synthetic input: 3000 records; 200 unusual-pairs engine pairs and 200 wording engine pairs.
- Hub build: 0.3087 seconds, measured with time.perf_counter around build_hub.
- hub-data.js: 5021056 bytes. hub.html: 211006 bytes.
- Machine: local Linux host, 12 logical CPUs (os.cpu_count), 18819248128 bytes physical memory (os.sysconf).
- Two builds into different output folders were byte-identical; the file set matched a small run.

No record cap is set for the page. This is the largest run tested. Browser load time is recorded below.

Measured browser load on 2026-10-25 with required Chromium and the one-thread numeric environment: the 3000-record synthetic run has 200 pairs per engine, 630 drawn nodes and 400 links. The first settled graph-ready event arrived in 1.0397 seconds, measured from opening the graph view by tests/test_hub_browser_stage.py::test_scale_3000_graph_ready with performance.now. This is one local observation, below the 20-second test bound; it is not a guarantee on another device.

## Deviations from the book guide

Deviation from the book graph guide (GUIDE lines 17 to 27): the guide draws bridge links thick yellow with red particles. The hub draws every pair in cobalt, width 1.6 for pairs that cross neighborhoods, and draws no particles. Reason: D-21 no ambient motion (rule 19), and yellow alone is 1.54:1 on paper. Status: deviation, not book-derived; proposed segment.

The stage built by plan 18 follows the same rule: every link cobalt, no particles.

The measured stage has no particle and every link is cobalt.
