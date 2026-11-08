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
