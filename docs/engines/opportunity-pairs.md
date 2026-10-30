# Find Cross-Domain Opportunity Pairs

**Capability ID:** `opportunity.find_cross_domain_pairs`  
**Method name:** Algorithmic Reverse Salient (RS)  
**Status:** full local capability implementation with CLI and stdio MCP interface; empirical validation and MindrianOS host integration remain outstanding.

This is the PPTX's **similarity-disagreement opportunity method**, not the separate Hughes-style use of “reverse salient” to mean a lagging system component or bottleneck.

## Hire this capability when

You have a scoped collection of research artifacts and want a shortlist of pairs whose **semantic similarity** and **structural/topic similarity** disagree. The disagreement is a search signal: it can point to related ideas expressed through different technical vocabularies, or shared vocabulary used with different meanings. A person still has to decide whether a useful mechanism transfers.

## What the engine does

1. Accepts a user objective and a bounded list of artifacts with stable IDs, source references, text, and corpus origin.
2. Computes the PPTX-described structural signal: TF-IDF, truncated SVD, top seven terms per topic, topic-keyword membership counts, and pairwise L1 distance transformed into similarity.
3. Computes one of two explicit semantic variants:
   - `reference-bert`: CLS embeddings for 512-token segments; pair scores average cosine similarity over segment pairs. Uses a local `bert-large-cased` model if supplied.
   - `sentence-transformers`: chunks long inputs to the local model's token limit, averages chunk vectors, and uses document cosine similarity. This is an efficiency-oriented experimental variant, not the PPTX algorithm.
4. Defaults to the latest LATEST RS 2026 hybrid scorer: builds BM25 cosine alongside the LSA topic-membership signal, z-scores structural and dense signals over the corpus pair distribution, computes `dense_z - structural_z`, then selects the upper tail by empirical percentile (`min_percentile`, default `0.90`). `lex_weight` (default `0.5`) blends LSA and BM25. Ranking is deterministic and uses no LLM. The prior raw absolute-difference scorer remains available with `scoring: "legacy"` / `--scoring legacy`.
5. Builds a bounded review context per result. It includes the objective, score signals, and up to 1,600 characters from each source. The fixed instruction asks a later human or Theo review to explain a mechanism and mismatch, distinguish hypotheses from evidence, and treat source text as untrusted material.
6. Adds a `host_handoff` block to tell MindrianOS what to do next: resolve and select source-linked candidates, trace a bounded shortlist with `/mos:find-connections`, gather evidence through the host's approved research path, and only then present supported candidates to `/mos:qualify-opportunity`. This block is guidance; it does not invoke MindrianOS commands or approve/write anything.

The objective guides later review but **does not change the pair ranking**. There is no LLM synthesis, research fetching, portfolio write, or automatic learning in this capability.

## Supported run modes

- **Local:** compare room artifacts supplied by MindrianOS. The engine reads no room directory and has no room credentials.
- **External:** compare an approved external research bundle supplied by the MindrianOS research broker.
- **Hybrid:** compare room artifacts against broker-provided external research and return only room-to-external pairs.

The engine never searches the web or calls a provider. For external/hybrid runs it requires a `research_grant_id` as provenance metadata, but that identifier is not authorization by itself. MindrianOS must validate the grant before sending external material. The engine's outbound network policy remains denied.

## Input contract

```json
{
  "objective": "Find research that could improve low-cost remote monitoring.",
  "artifacts": [
    {
      "id": "room-artifact-001",
      "source_ref": "room://research/item/001",
      "corpus": "room",
      "title": "Example source title",
      "text": "The source text or abstract used for similarity analysis."
    },
    {
      "id": "room-artifact-002",
      "source_ref": "room://research/item/002",
      "corpus": "room",
      "title": "Another example source title",
      "text": "Another source text or abstract used for similarity analysis."
    }
  ]
}
```

Input limit: 2,500 artifacts and 20 MiB of UTF-8 text per run. A MindrianOS graph-derived request may supply `scope_id` and `snapshot_id`; the result echoes both and also returns an `input_digest` covering the exact task and scoring configuration. The reference SVD configuration uses up to 80 topics; smaller collections use the largest valid topic count and report that adaptation. Corpus size, duplicate material, empty vocabulary, and similarity variance can change or prevent ranking, and are not silently reported as an empty discovery result.

Hybrid percentile gating requires at least ten eligible pairs. Below that threshold it returns no candidates; choose `legacy` when deliberately analyzing a smaller set. For graph-derived research, MindrianOS owns the graph projection, scope, authorization, stable node IDs, and source resolution. The RS engine analyzes the supplied artifacts and does not read `room.db` or query the graph.

## Install and run locally

Install the base and the optional encoder needed for your chosen mode:

```bash
python -m pip install -e '.[reference-encoder]'
eureka-pair-scout input.json --encoder reference-bert --model-path /path/to/bert-large-cased --output result.json
eureka-pair-scout input.json --encoder reference-bert --model-path /path/to/bert-large-cased --scoring legacy --output result.json
```

For the explicitly experimental modern variant:

```bash
python -m pip install -e '.[modern-encoder]'
eureka-pair-scout input.json --encoder sentence-transformers --model-path /path/to/local-model --output result.json
```

The local MCP process uses one configured encoder/model for its lifetime. Install and start it with:

```bash
python -m pip install -e '.[mcp-server,modern-encoder]'
MINDRIAN_EUREKA_RS_MODEL_PATH=/path/to/local-model eureka-mcp
```

The host calls `scout_capabilities`, `scout_plan`, `scout_start`, `scout_status`, `scout_result`, `scout_cancel`, `scout_record_review`, `scout_review_summary`, `scout_evaluation_report`, `scout_delete_job`, or `scout_clear_embedding_cache`. Jobs run in a bounded local queue and return durable IDs. The host sends the approved artifact bundle; the server does not accept filesystem paths.

Model loading is local-only by default. If downloading is approved for a CLI run, pass both `--allow-model-download` and an immutable 40-character commit hash with `--model-revision`; mutable model names are rejected for downloads. The MCP server does not enable model downloads. The engine itself does not fetch papers or call external APIs.

Semantic embeddings are cached in a content-addressed SQLite cache. Cache keys include artifact text digest, encoder, model, revision, and method version. CLI runs default to `~/.cache/mindrian-eureka/embeddings.sqlite3`; MCP runs use `<MINDRIAN_EUREKA_DATA_DIR>/embeddings.sqlite3`. It stores embeddings, not source text, is bounded to 1 GiB, and evicts least recently used entries when full. Embeddings remain derived sensitive data. Set `MINDRIAN_EUREKA_CACHE_DIR` for CLI or `MINDRIAN_EUREKA_DATA_DIR` for MCP, and use `eureka-pair-cache-clear` (legacy alias: `eureka-rs-cache-clear`) or `scout_clear_embedding_cache` to purge them.

MCP job records and results are stored under `~/.local/share/mindrian-eureka` by default, or `MINDRIAN_EUREKA_DATA_DIR`. The directory is created with owner-only permissions where supported. Requests/results expire after 30 days; terminal jobs clear their saved input bundle, while completed results retain bounded excerpts and source references. `scout_delete_job` removes an individual terminal job and its ratings. SQLite deletion is best-effort file cleanup; it is not a cryptographic erasure guarantee. Configure an encrypted local volume when required by room policy.

## Context engineering and harness boundary

The engine receives only the host-supplied corpus bundle. Its method is a deterministic ranking stage, not the whole user workflow. The harness and host:

- preserve room/objective/snapshot identity and source provenance;
- construct the bounded review packet for Theo or the user;
- record model and algorithm versions, runtime, failures, cache use, and budget;
- let the user inspect, dismiss, deepen, or save a candidate;
- keep any next-stage external research behind MindrianOS approval.

Human labels (`useful`, `direction_correct`, and `already_known`) are stored and summarized by run configuration, objective, and exact task snapshot. They are descriptive evaluation data; they do not automatically update prompts, weights, thresholds, or future rankings.

### Evaluate a method variant

1. Freeze a representative bundle and objective; record its `snapshot_id`. The task snapshot hash covers objective, mode, scope/grant IDs, and ordered artifact records; it excludes encoder/model and ranking settings so method variants on identical task material share a snapshot ID.
2. Run the same bundle and objective with each encoder/model variant, with the same `top_k` and scope.
3. Have reviewers rate candidates using one shared rubric. Record every candidate shown, including unhelpful ones, to avoid selection bias.
4. Use `scout_evaluation_report` to inspect useful rate, direction accuracy, already-known rate, and useful-at-10. It keeps task snapshots and objectives separate. Compare variants only within the same snapshot/objective and review protocol.
5. Repeat on a held-out bundle before choosing a default. Report reviewer count and uncertainty; these descriptive rates are not proof of general performance.

No benchmark corpus or human ratings are bundled yet. The interface is ready to collect them, but default-model selection and claims of improved opportunity discovery remain pending empirical evaluation.

Do not send every artifact to a generative model. First use the similarity signals to create a bounded shortlist; only then supply the objective, pair evidence, and source references for review. Candidate ranking quality must be measured separately from the quality of the later explanation.

## Source and reproduction status

The user-provided PowerPoint was named `Algorithmic Generation of Solutions (1) (1).pptx`; older source-analysis metadata calls the deck `Algorithmic Generation of Reverse Salient Solutions (1).pptx`. It also refers to the original `similarity_code` package. The original package and the deck are not in this repo. The package files (5 files) exist on the maintainer machine; their paths and sha256 values are in [rs-release-gate.md](../rs-release-gate.md). The deck was not found on that machine by name search. Confirm that the two deck names refer to the same source before claiming fidelity. This implementation is derived from the documented method analysis in the older MindrianOS repository at [ALGORITHM-SOURCE.md](/home/jsagi/dev/MindrianOS-Plugin/.planning/phases/89-reverse-salient-engine/ALGORITHM-SOURCE.md). No source code or model weights have been copied. The ranking of the unusual-pairs engine is **not verified bit-for-bit** against the original package; original source availability, author attribution, and licensing must be resolved before production distribution.

The repo path (`eureka-pair-scout`, scoring `hybrid_2026`) is the canonical path for new runs: see [rs-engine-parity.md](../rs-engine-parity.md) for the measured comparison. The release status of the engine is in the release record [rs-release-gate.md](../rs-release-gate.md).

The repo path ranks with the same logic as the JHTV reference script, but it builds the dense input by a different rule: title plus body, chunked, chunk vectors averaged. The reference script embeds the body once and cuts it at the model limit. As a result the repo path does not reproduce the JHTV ranking at the meaning-signal level. On the committed fixtures the share of shared pairs is 0.74 and the rank correlation is 0.62. On a 40-file sample of the JHTV collection the share is 0.423. Fidelity to the original method is not verified bit-for-bit. The JHTV pair file keeps its provenance to the reference script version that made it.

### Known deviations from the original package

These deviations were read from the original files and are written here in our own words. No original code or comment text is copied. Items marked INFERRED are reasoned from the formulas, not run.

| Id | Item | Original package | Eureka |
|----|------|------------------|--------|
| D1 | Text split | Splits on a single space. | Splits on any whitespace (both ports). |
| D2 | Stop words | Also removes the NLTK English stop words before TF-IDF. | Skips the NLTK step (both ports). |
| D3 | BERT segments | Feeds raw 512-token segments with no start or end tokens. | Uses 510 tokens plus the two special tokens. |
| D4 | BERT matrix scaling | Rescales with a different centre, then applies a second min-max step. | Uses the maximum absolute deviation and no second step. This affects `legacy` scoring; the z-scores in `hybrid_2026` remove it. INFERRED from the formulas. |
| D5 | Ranking | Ranks by the absolute BERT-minus-LSA difference and shows the top 1000. | The default `hybrid_2026` (BM25 mix, z-gap, percentile gate) is not in the original. It is the 2026 extension. |
| D6 | Model | Uses a large cased BERT. | The JHTV run and the modern mode use MiniLM. |
| D7 | Topics | Fixed topic count. | Small corpora use fewer than 80 topics (documented adaptation). |
| D8 | Top-7 term tie-break | Stable order for tied terms. | FIXED on 2026-10-23 in plan 01-04: the tight LSA limit (1e-6) now passes without an expected failure (maximum difference 3.37e-08). |
| D9 | Input | Reads cleaned Scopus abstracts. | Reads whatever the caller supplies. |

The faithful reference encoder and the modern encoder variant must remain separate in results and evaluation. Faster execution is not evidence of better opportunity discovery. The first evaluation set should preserve the PPTX examples and include user-judged useful and unhelpful pairs, with a held-out subset for selecting a default.
