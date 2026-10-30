# Reverse Salient Pair-Set Quality Gate

`research.assess_rs_pair_set_quality` checks whether a batch of RS scores is usable for ranking.

## When to use it

Run it after generating a same-scope cohort of scores and before sorting or selecting candidates:

```bash
eureka-workflow research.assess_rs_pair_set_quality rs-pair-set.json --output rs-pair-quality.json
```

The gate detects the fixed SEED-018 semantic-floor/LSA-ceiling collapse, score dimensions with no spread, non-finite records, and cohorts too small to rank. It returns source/node lineage for every pair.

When starting with `research.score_rs_differential_pair`, map each output's `scored_pair.lsa` and `scored_pair.bert` into the gate's `lsa` and `bert` properties. The adapter derives `signed_diff = bert - lsa`, matching the scorer's semantic-minus-lexical convention.

## Interpretation and limits

`quality_gate_passed` means only that these fixed diagnostics did not flag the cohort. It does not validate any pair, establish novelty, or prove rank quality. The source provides no tuning options by design; do not override its thresholds to force a pass. All measurements and lineage come from MindrianOS, which retains graph ownership and authorization.

The source is Mindrian BSL 1.1; distribution and attribution review remains pending. See the [engine source ledger](../engine-source-ledger.md).
