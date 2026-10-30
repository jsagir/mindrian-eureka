# Eureka grounding critic: Stage A and Stage B

`portfolio.prepare_candidate_critic` and `portfolio.inspect_candidate_grounding` expose the deterministic Stage A gates from the LATEST Eureka critic. `portfolio.prepare_critic_rubric` and `portfolio.evaluate_critic_rubric` expose a host-brokered Stage B rubric over MindrianOS local judge responses. These are source-backed triage stages, not the full Eureka lifecycle or opportunity qualification.

## MindrianOS graph handoff

The MindrianOS room graph remains the source of candidate identity and nearest-neighbor evidence. MindrianOS owns the room connection, local embedding model, graph query, authorization, source resolution, review, and any filing. Eureka receives no room path or database handle.

Run `portfolio.prepare_candidate_critic` with a candidate containing `mechanismText`. It returns the source-generated mechanism perturbations and a SHA-256 for each exact string. MindrianOS embeds those strings with its configured local encoder, queries the authorized graph for nearest neighbors of the original mechanism, and then calls `portfolio.inspect_candidate_grounding` with:

- the original candidate text and mechanism;
- candidate, graph-node, scope, and snapshot IDs;
- the embedding model ID, ordered vectors, and returned text hashes;
- nearest-neighbor graph node IDs and cosine similarities;
- resolvable source references for source-backed quantities.

The worker verifies the vector row shape and that the hashes match the source-generated strings. It cannot independently prove which encoder generated the vectors or whether the host's neighbor query was authorized; MindrianOS binds those facts to its ICM run and snapshot. A retrieval with no neighbors is passed as an empty array, which is distinct from omitting the graph query (the latter is rejected).

## Interpretation

Stage A applies four ordered gates: unsourced quantity, domain-swap invariance, nearest-neighbor novelty delta, and entity specificity. The first failing gate is returned. A pass means only that these deterministic gates passed. It does not mean that an opportunity is real, that the cross-domain transfer is valid, or that a candidate is novel in external literature. This stage performs no model call, calibration ruling, or graph write.

## Stage B: local judging and code-derived verdict

After Stage A passes, MindrianOS calls `portfolio.prepare_critic_rubric` with the same candidate/scope/snapshot and the Stage A result. The capability verifies that the mechanism text has the same source-generated variant hashes, then returns the source neutral and adversarial prompts plus hashes. Those prompts contain candidate content. MindrianOS must run them only through its approved local judge and preserve the model identity and prompt hashes.

MindrianOS returns both responses to `portfolio.evaluate_critic_rubric`, along with the same Stage A result. The capability validates candidate, source node, scope, snapshot, and prompt hash continuity, runs the source parser, and computes the verdict from the two rubric patterns. The judge does not choose the verdict. Disagreement routes to `general_shallow`; confidence is always `not_calibrated` because the relevant baseline is not packaged or evaluated here.

Eureka makes no model call in this flow. The compatibility audit stubs reject attempts to use the source's egress/payload helpers, and the public worker exposes only source prompt builders, Stage A, and the parser/rubric operation. The response does not preserve raw judge responses. MindrianOS owns those responses, the local model boundary, evidence resolution, and final human decision.

The source header identifies BSL 1.1. This port is local evaluation only while redistribution and production-use rights are reviewed. See the [source and license ledger](../engine-source-ledger.md).
