# Find Cross-Domain Opportunity Pairs

**Capability ID:** `opportunity.find_cross_domain_pairs`  
**Method name:** Algorithmic Reverse Salient (RS)  
**Status:** experimental local CLI prototype; not yet exposed through MCP or MindrianOS.

This is the PPTX's **similarity-disagreement opportunity method**, not the separate Hughes-style use of “reverse salient” to mean a lagging system component or bottleneck.

## Hire this capability when

You have a scoped collection of research artifacts and want a shortlist of pairs whose **semantic similarity** and **structural/topic similarity** disagree. The disagreement is a search signal: it can point to related ideas expressed through different technical vocabularies, or shared vocabulary used with different meanings. A person still has to decide whether a useful mechanism transfers.

## What the prototype does

1. Accepts a user objective and a bounded list of artifacts with stable IDs, source references, and text.
2. Computes the PPTX-described structural signal: TF-IDF, truncated SVD, top seven terms per topic, topic-keyword membership counts, and pairwise L1 distance transformed into similarity.
3. Computes one of two explicit semantic variants:
   - `reference-bert`: CLS embeddings for 512-token segments; pair scores average cosine similarity over segment pairs. Uses a local `bert-large-cased` model if supplied.
   - `sentence-transformers`: chunks long inputs to the local model's token limit, averages chunk vectors, and uses document cosine similarity. This is an efficiency-oriented experimental variant, not the PPTX algorithm.
4. Applies the source-described global centering/scaling to each similarity matrix, ranks unique unordered pairs by `abs(semantic - structural)`, and returns the signed difference and both source references.
5. Builds a bounded review context per result. It includes the objective, score signals, and up to 1,600 characters from each source. The fixed instruction asks a later human or Theo review to explain a mechanism and mismatch, distinguish hypotheses from evidence, and treat source text as untrusted material.

The objective guides later review but **does not change the pair ranking** in version 0.1.0. There is no LLM synthesis, remote research, portfolio write, or automatic learning in this capability.

## Input contract

```json
{
  "objective": "Find research that could improve low-cost remote monitoring.",
  "artifacts": [
    {
      "id": "room-artifact-001",
      "source_ref": "room://research/item/001",
      "title": "Example source title",
      "text": "The source text or abstract used for similarity analysis."
    },
    {
      "id": "room-artifact-002",
      "source_ref": "room://research/item/002",
      "title": "Another example source title",
      "text": "Another source text or abstract used for similarity analysis."
    }
  ]
}
```

Input limit: 2,000 artifacts and 20 MiB of UTF-8 text per run. The reference SVD configuration uses up to 80 topics; smaller collections use the largest valid topic count and report that adaptation. Corpus size, duplicate material, empty vocabulary, and similarity variance can change or prevent ranking, and are not silently reported as an empty discovery result.

## Install and run locally

Install the base and the optional encoder needed for your chosen mode:

```bash
python -m pip install -e '.[reference-encoder]'
eureka-rs input.json --encoder reference-bert --model-path /path/to/bert-large-cased --output result.json
```

For the explicitly experimental modern variant:

```bash
python -m pip install -e '.[modern-encoder]'
eureka-rs input.json --encoder sentence-transformers --model-path /path/to/local-model --output result.json
```

Model loading is local-only by default. If downloading is approved, pass both `--allow-model-download` and an immutable `--model-revision`; mutable model names are rejected for downloads. The engine itself does not fetch papers or call external APIs. Run it inside the host's intended worker sandbox before processing confidential room material; this CLI alone is not a filesystem/network sandbox.

## Context engineering and harness boundary

The engine receives only the approved corpus bundle. Its method is a deterministic ranking stage, not the whole user workflow. The harness around it should eventually:

- preserve room/objective/snapshot identity and source provenance;
- construct the bounded review packet for Theo or the user;
- record model and algorithm versions, runtime, failures, and budget;
- let the user inspect, dismiss, deepen, or save a candidate;
- keep any next-stage external research behind MindrianOS approval.

Do not send every artifact to a generative model. First use the similarity signals to create a bounded shortlist; only then supply the objective, pair evidence, and source references for review. Candidate ranking quality must be measured separately from the quality of the later explanation.

## Source and reproduction status

The user-provided PowerPoint was named `Algorithmic Generation of Solutions (1) (1).pptx`; older source-analysis metadata calls the deck `Algorithmic Generation of Reverse Salient Solutions (1).pptx`. It also refers to the original `similarity_code` package. Those files are not present in this checkout, so confirm that the two deck names refer to the same source before claiming fidelity. This implementation is derived from the documented method analysis in the older MindrianOS repository at [ALGORITHM-SOURCE.md](/home/jsagi/dev/MindrianOS-Plugin/.planning/phases/89-reverse-salient-engine/ALGORITHM-SOURCE.md). No source code or model weights have been copied. The implementation is **not yet verified bit-for-bit** against the PPTX package; original source availability, author attribution, and licensing must be resolved before production distribution.

The faithful reference encoder and the modern encoder variant must remain separate in results and evaluation. Faster execution is not evidence of better opportunity discovery. The first evaluation set should preserve the PPTX examples and include user-judged useful and unhelpful pairs, with a held-out subset for selecting a default.
