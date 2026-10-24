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

## Tested size
