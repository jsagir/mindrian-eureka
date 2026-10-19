# Reverse Salient Differential Scoring

`research.score_rs_differential_pair` scores one source-linked problem/method concept pair before innovation classification.

## When to use it

Use this stage when MindrianOS has selected the two concepts and generated embeddings for both with the same approved local encoder. The output can be passed directly to `research.classify_rs_pair`.

```bash
eureka-workflow research.score_rs_differential_pair rs-differential-request.json --output rs-differential-score.json
```

The request contract is [`rs-differential-scoring-input.v1.json`](../../src/mindrian_eureka/data/schemas/rs-differential-scoring-input.v1.json). Provide stable `scope_id`, `snapshot_id`, graph node IDs, and source IDs when those concepts come from the local graph. The vectors must have the same non-zero dimension. MindrianOS controls the model, computes the vectors, and remains responsible for their authorization and provenance.

## Method and boundaries

The local worker runs the LATEST `score()` path with its deterministic pair-wise TF-IDF leg and host-supplied vectors for the semantic cosine. It returns `diff`, `lsa`, `bert`, the strict dual-floor `passes` signal, and typed source lineage. No model is loaded, and Eureka does not read a room, query a vector cache, contact Pinecone, or access a network service.

This uses the source's fixed legacy thresholds and pair-wise LSA; neither is calibrated. A passing pair is a screening lead, not proof of novelty, causality, innovation, or commercial value. Apply the existing classifier next; retain the original sources for human inspection.

The adapted LATEST source is under Mindrian BSL 1.1. Distribution and attribution review is still pending; see the [engine source ledger](../engine-source-ledger.md).
