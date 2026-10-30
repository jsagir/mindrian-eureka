# Jason text-difference analysis

**User-facing capability:** Compare Text Claims and Detect Restatements  
**Hire when:** descriptions or claims may overlap or restate one another, and a reviewer needs lexical, semantic-proxy, and sentence-pair evidence to inspect.  
**Interface:** `scout_compare_text_differences` MCP tool or `eureka-workflow analysis.compare_text_differences input.json`.

This ports the package's Jason v3.1 descriptive analysis. It reports lexical Jaccard overlap, character n-gram similarity when no local dense model is configured, BM25-style weighted term similarity, sentence-level comparisons, corpus-relative ranks where there are enough pairs, buzzword-heuristic hits, and provenance. The optional dense sentence-transformer model must be provided locally using `MINDRIAN_EUREKA_JASON_MODEL_PATH`; the tool does not download it.

The gap between semantic and lexical similarity is described by the source package as a paraphrase/restatement diagnostic. It is not an innovation score, novelty test, opportunity rank, or factual verdict. The actual dense model path and package behavior remain unevaluated in this repo. Source/reuse rights are unresolved; local evaluation only.

Input contract: [`jason-text-difference-input.v1.schema.json`](../../schemas/jason-text-difference-input.v1.schema.json).
