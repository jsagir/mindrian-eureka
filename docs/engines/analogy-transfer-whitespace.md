# Analogy transfer whitespace

`analogy.discover_transfer_whitespace` checks a selected source/target analogy against embeddings for the supplied room artifacts and baseline frameworks. It looks for a transfer midpoint that is close to a baseline mechanism but poorly represented by other room artifacts. If explicit analogy edges are absent, the stage can select cross-section HSI pairs with high semantic similarity and low lexical similarity.

The LATEST method has two modes:

- `percentile` excludes the pair endpoints from articulation checks and ranks gap strength against the supplied pair corpus. If fewer than `min_corpus` pairs are scored, it falls back to fixed thresholds.
- `fixed` uses the source method's absolute thresholds and includes endpoints in the original articulation behavior.

All embeddings must use the same model and preprocessing. MindrianOS supplies the authorized vectors, analogy edges, and section labels. The engine does not read `.mindrian/room.db`, fetch evidence, check external novelty, or write graph state. A whitespace zone is a research lead that needs source checks and human review.

## Source parity

The source-ledger-pinned LATEST script was compared with this adapter on deterministic synthetic bundles for fixed mode, percentile mode, small-corpus fallback, and HSI fallback. Zone counts and the common algorithm fields matched exactly at the source's four-decimal output precision. `tests/test_analogy_source_parity.py` preserves these source-derived golden outputs without depending on the Windows research-folder path. This checks implementation fidelity on fixtures; it does not establish ranking quality on a real room or remove the source-rights restriction.

Run through either surface:

```bash
eureka schema analogy.discover_transfer_whitespace
eureka-workflow analogy.discover_transfer_whitespace request.json --output result.json
```

MCP callers use `scout_capability_contract` and `scout_run_workflow`. The full contract and limits are in the machine-readable capability catalog. Source attribution and redistribution rights remain unresolved; local evaluation only.

## Structural fitness handoff

`analogy.assess_structural_fitness` compares each host-supplied, seven-layer SAPPhIRE candidate with a target. It returns both structural fitness and a text/structure fused fitness, assigns a correspondence band, and orders candidates by band and fused score. In corpus-relative mode, the restatement warning uses the candidate pool's text percentile; a flagged restatement is moved below the best unflagged candidate when one exists. Pools smaller than five use fixed layer and restatement thresholds. The local implementation uses the operator's sentence-transformer, so numeric parity with the LATEST embedding spine is not claimed.

```bash
export MINDRIAN_EUREKA_ANALOGY_MODEL_PATH=/path/to/local/model
eureka-workflow analogy.assess_structural_fitness request.json --output result.json
```

Optional scoring settings follow the LATEST defaults: `MINDRIAN_ANALOGY_LAYER_THRESHOLD=0.5`, `MINDRIAN_ANALOGY_TEXT_WEIGHT=0.5`, `MINDRIAN_ANALOGY_RESTATEMENT_FLOOR=0.8`, and `MINDRIAN_ANALOGY_ABS_FLOOR=0.3`. Each is clamped to `[0, 1]`; invalid values fall back to the default. Supply the model path in the MCP server process environment as well.

The output is a shortlist for SME mapping and evidence review. It is not evidence that a mechanism transfers, nor an accepted MindrianOS graph relationship.
