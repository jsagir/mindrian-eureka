# HSI pair scoring

**User-facing capability:** Find Hybrid-Similarity Pair Leads  
**Hire when:** a user has a scoped, source-linked collection and wants unusual pairs ranked before deciding which to inspect.  
**Interface:** `scout_find_hybrid_similarity_pairs` MCP tool or `eureka-workflow portfolio.find_hybrid_similarity_pairs input.json`.

## What runs

The host supplies artifact IDs, text, and source references. The local adapter runs the reviewed 2026 HSI numerical routines: seeded LSA, BM25, a selectable lexical leg, an optional dense semantic leg, corpus-relative or legacy ranking, and the spectral thinking-mode proxy used by the package. It returns per-pair signals, source excerpts, content hashes, and method/degradation labels.

Dense vectors can be supplied in the request, or the operator can set `MINDRIAN_EUREKA_HSI_MODEL_PATH` to a local sentence-transformer directory. The engine never downloads a model. With neither available, it uses a clearly labeled lexical-only comparison (LSA versus BM25); this is degraded behavior, not dense HSI.

## Boundaries

- It reads only the supplied artifact bundle and does not access room paths, remote providers, or graph databases.
- It does not calculate external whitespace or market demand.
- An HSI score, surprise label, or spectral estimate is not probability, novelty, technical fit, commercial value, or a verified opportunity.
- It does not write candidates to the MindrianOS opportunity bank.
- HSI source redistribution rights remain unresolved. This port is for local evaluation pending rights review.

Input contract: [`hsi-pair-input.v1.schema.json`](../../schemas/hsi-pair-input.v1.schema.json).
