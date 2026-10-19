# Using MindrianOS Eureka capabilities

MindrianOS is the user-facing host. It resolves the active room, scope, permissions, Theo guidance, and research approvals, then sends a bounded JSON bundle. Eureka never accepts a room directory path and never writes the MindrianOS portfolio.

## Pick a job by user need

Start with the user's wicked challenge and uncertainty: what is changing, interconnected, contested, or not yet understood—and where might that uncertainty contain opportunity? Do not force the situation into a single clean problem statement. Theo can guide method choice; MindrianOS preserves the different frames and confirms objective and scope with the user. Then select only the supporting capability whose inputs are ready. Undefined-future exploration, ill-defined opportunity search, and well-defined testing are inquiry modes that can recur as evidence and new possibilities reshape the challenge. See [the engine jobs guide](engine-jobs.md) for the full process and readiness.

| User-facing job | Capability | Use it when |
|---|---|---|
| Find technical bottlenecks and unusual connections | `opportunity.find_cross_domain_pairs` | A scoped, source-linked collection is ready and you want cross-field leads to explore. |
| Screen one collection for opportunity leads | `opportunity.synthesize_discovery_signals` | You want RS and HSI shortlists over the same local snapshot before choosing candidates for review. |
| Surface under-watched growth signals | `portfolio.classify_weak_signal_tail` | MindrianOS supplies comparable `[0,1]` attention and growth proxy values with their explicit meanings and stable node IDs. |
| Check a candidate with Eureka grounding gates | `portfolio.prepare_candidate_critic` then `portfolio.inspect_candidate_grounding` | MindrianOS embeds the exact prepared variants locally and returns nearest neighbors from the same authorized graph snapshot. A pass clears deterministic Stage A only; it is not opportunity qualification. |
| Challenge a Stage A candidate | `portfolio.prepare_critic_rubric` then `portfolio.evaluate_critic_rubric` | Only after Stage A passes: MindrianOS sends the two source-authored prompts to its approved local judge, then returns both responses. Eureka parses them and derives the rubric verdict by code; confidence is not calibrated. |
| Find similarities and surprising differences | `portfolio.find_hybrid_similarity_pairs` | A scoped collection is ready for a portfolio-relative pair scan. |
| Find mechanisms from other fields | `analogy.retrieve_mechanism_candidates` | You have a target problem and a source-linked mechanism corpus supplied by the host. |
| Compare a mechanism with the target problem | `analogy.assess_structural_fitness` | Both are represented in sourced relational layers and a local model is configured; use results as hypotheses to review. |
| Map a mechanism to a problem | `analogy.map_structure` | A source mechanism is selected and you want possible relational transfers made explicit for testing. |
| Turn confirmed fields into research tasks | `research.prepare_multidomain_plan` | The user or Theo has confirmed relevant fields and the host will run approved research. |
| Build a Genesis plan from local graph context | `research.run_genesis_local_plan` | MindrianOS supplies the authorized graph projection; Theo reviews domains and the host approves any external research. |
| Draft an evidence-linked innovation hypothesis | `research.generate_rs_thesis` | The host supplies the classified concepts, breakthrough dimension, and linked evidence; the output is a hypothesis record, not prior-room retrieval or validation. |
| `research.analyze_rs_domain_projection` | Find relevant fields in the local knowledge graph | Use before RS preprocessing with an authorized graph snapshot; Eureka ranks caller-supplied framework records and returns node/source lineage without reading the graph. |
| `research.score_rs_differential_pair` | Compare a problem and method across wording and meaning | Supply concepts and two same-model vectors from MindrianOS; the route computes the lexical/semantic differential and retains source references. |
| `research.assess_rs_pair_set_quality` | Check candidate pair data before ranking | Run before ranking; the fixed gate reports degenerate or constant score columns and flags cohorts too small to rank. |
| `research.generate_rs_query_matrix` | Explore a research domain from multiple angles | Use after domain analysis to build 60 structured questions; MindrianOS reviews and authorizes any external provider request. |
| `research.preprocess_rs_documents` | Extract research signals from approved documents | Use after MindrianOS has fetched source-linked documents and prepared a domain-analysis context; results are lexical evidence leads and must pass the host egress policy before external use. |
| `research.assess_rs_commercial_case` | Draft a commercial hypothesis for an innovation lead | Use after an RS pair is classified and scored to produce a fixed value-proposition template, a signal bucket, and source-linked host-supplied partnership leads. These are hypotheses for review, not market sizing or a validated business case. |
| `research.classify_rs_pair` | Classify how a method relates to a problem | Use before breakthrough scoring to distinguish structural transfer, semantic implementation, hybrid signal, or no signal. This is a fixed rule-based label, not a transfer-value judgment. |
| `research.score_rs_breakthrough` | Score an innovation lead for further review | After differential scoring and classification, compare source-defined feasibility, market, magnitude, advantage, and impact heuristics before deciding what to investigate further. | Experimental; consumes host-supplied signals and does not qualify an opportunity. |
| `decision.fit_sequence_patterns` | Fit exploratory decision-sequence models | Use only with at least two independently coded traces, a specified seed HMM, and 32 or more total coded steps; treat fitted parameters as unvalidated research hypotheses. |
| Extract expert candidates from research results | `research.extract_experts_from_papers` | MindrianOS supplies papers from an approved research provider; results preserve evidence and identity uncertainty, without querying or writing the local expert directory. |
| Check claims for restatement or overlap | `analysis.compare_text_differences` | Descriptions may repeat existing claims and you need comparison leads for human inspection. |
| Explore the local graph for relationship signals | `graph.explore_local_relationships` | MindrianOS prepared an authorized, typed graph snapshot and wants bounded, unevidenced link candidates. |
| Evaluate relationship methods against historical edges | `graph.backtest_relationship_methods` | The authorized snapshot includes dated relationships; treat a failed or underpowered run as inconclusive. |
| Prioritize belief changes for review | `graph.score_bayesian_surprise` | The host supplied prior and evidence-informed posterior judgments; the output is triage, not truth. |
| Compare themes across two corpora | `graph.compare_bidirectional_topics` | Both text corpora are ready and topic outliers would help direct further inquiry. |
| Rank graph paths already retrieved by MindrianOS | `graph.rank_evidence_paths` | The host has already retrieved authorized paths and wants their length, evidence coverage, and unknown confidence summarized. |
| Challenge claims against evidence | `analysis.audit_claim_traceability` | A candidate needs its evidence, counterevidence, assumptions, and falsifiers checked for completeness. |
| Prepare a review of competing views | `deliberation.prepare_six_hat_review` | Source-linked arguments exist and the human needs open questions organized before deciding. |
| Validate and package proposed portfolio links | `graph.package_relationship_proposals` | Another process has proposed links and they need reference checks before human review. |

The packaged catalog (`eureka capabilities` or MCP `scout_capabilities`) is authoritative about prerequisites and maturity. `experimental`, `blocked`, and `planned` are materially different states.

## CLI

Install the package in the repo's locked environment, then pass a JSON file to the named stage:

```bash
eureka capabilities
eureka capability graph.explore_local_relationships
eureka schema graph.explore_local_relationships
eureka-signal-scout input.json --output result.json
eureka-workflow portfolio.find_hybrid_similarity_pairs input.json --output result.json
eureka-workflow portfolio.classify_weak_signal_tail input.json --output result.json
eureka-workflow portfolio.prepare_candidate_critic candidate.json --output variants.json
eureka-workflow portfolio.inspect_candidate_grounding critic-input.json --output critic-result.json
eureka-workflow portfolio.prepare_critic_rubric rubric-request.json --output rubric-prompts.json
eureka-workflow portfolio.evaluate_critic_rubric rubric-evaluation.json --output rubric-result.json
eureka-workflow analysis.compare_text_differences input.json --output result.json
eureka-workflow analogy.assess_structural_fitness input.json --output result.json
eureka-workflow research.prepare_multidomain_plan input.json --output result.json
eureka-workflow research.run_genesis_local_plan graph-projection.json --output genesis-plan.json
eureka-workflow research.analyze_rs_domain_projection rs-domain-projection.json --output rs-domain-analysis.json
eureka-workflow research.score_rs_differential_pair rs-differential-request.json --output rs-differential-score.json
eureka-workflow research.assess_rs_pair_set_quality rs-pair-set.json --output rs-pair-quality.json
eureka-workflow research.generate_rs_query_matrix rs-query-context.json --output rs-query-matrix.json
eureka-workflow research.generate_rs_thesis rs-thesis-request.json --output rs-thesis.json
eureka-workflow research.classify_rs_pair rs-classifier-request.json --output rs-classification.json
eureka-workflow research.preprocess_rs_documents rs-preprocessing-request.json --output rs-preprocessed.json
eureka-workflow research.assess_rs_commercial_case rs-commercial-request.json --output rs-commercial-hypothesis.json
eureka-workflow research.score_rs_breakthrough rs-breakthrough-request.json --output rs-breakthrough.json
eureka-workflow research.extract_experts_from_papers approved-papers.json --output expert-candidates.json
eureka-workflow graph.backtest_relationship_methods graph-snapshot.json --output evaluation.json
eureka-workflow graph.score_bayesian_surprise surprise-input.json --output triage.json
eureka-workflow graph.compare_bidirectional_topics corpus-pair.json --output topics.json
eureka-workflow graph.rank_evidence_paths paths.json --output ranked-paths.json
```

The CLI reads only the explicit input file and writes only the requested result path. For HSI, supply `dense_vectors` in the request or set `MINDRIAN_EUREKA_HSI_MODEL_PATH` to a local model. Jason accepts `MINDRIAN_EUREKA_JASON_MODEL_PATH`; without one, its text similarity field is explicitly a character n-gram proxy.

## MCP

- `scout_capabilities` lists maturity, JTBD, and requirements.
- `scout_capability(capability_id)` returns one job contract.
- `scout_capability_contract(capability_id)` returns that contract plus its packaged JSON input/output schemas; a schema marked `not_published` is a visible contract gap, not permission to guess.
- `scout_start_opportunity_signal_scout(request)` runs the durable local RS+HSI signal job, with status/result/cancel via its returned `job_id`.
- `scout_run_workflow(capability_id, request)` runs one named local stage synchronously.
- `scout_find_hybrid_similarity_pairs(request)` and `scout_compare_text_differences(request)` are direct, typed MCP entry points.
- `scout_assess_analogy_fitness(request)` compares sourced SAPPhIRE-layer structures with the configured local encoder.
- `scout_run_workflow` also exposes graph backtesting, Bayesian-surprise triage, bidirectional topic comparison, and supplied-path ranking under the same capability IDs and JSON schemas as the CLI.
- `scout_start/status/result/cancel` provide durable job lifecycle for RS pair discovery and the RS+HSI signal scout; other supporting stages are synchronous.

External sources must be retrieved by MindrianOS's approved broker and returned with their source IDs/URLs, retrieval date, and claim locators. Research plans are not search results. None of the local stages approves a transfer, validates market demand, resolves licensing, or files a graph relationship.

## Example MindrianOS user journey

1. **Frame with Theo.** MindrianOS asks Theo for method guidance using the generic problem class, then confirms the user's decision, scope, and exclusions.
2. **Prepare a local snapshot.** The host exports only authorized records with stable IDs, text, titles, source references, and hashes. It does not send room paths.
3. **Scout selectively.** Start `scout_start_opportunity_signal_scout` for the local RS+HSI pair shortlist. If only one method is needed, call its specific capability instead. The shortlist preserves the original engine ranks; it does not merge them into an opportunity score.
4. **Choose a candidate for deeper work.** The user selects a pair. MindrianOS runs `/mos:find-connections` for prior-art and room-graph context and records any match or conflict.
5. **Broaden only when needed.** For a graph-backed Genesis planning pass, MindrianOS supplies an authorized projection to `research.run_genesis_local_plan`; Theo reviews the heuristic domain signals and research plan. The host approves exact outside queries, then its broker performs them and returns source-linked claims. `research.prepare_multidomain_plan` remains available when domains are already confirmed.
6. **Test the transfer.** Retrieve source mechanisms with `analogy.retrieve_mechanism_candidates`, encode the selected source and target with claim provenance, then use `scout_sme_map` and `scout_sme_finalize` to test inferences against support, counterevidence, novelty, and boundary evidence.
7. **Challenge and decide.** Use Jason's text-difference diagnostic when restatement/overlap is a concern, or the Six-Hat review-preparation stage when evidence-backed positions disagree. Ask Theo to review only through an operation that accepts the authorized case context. The human decides whether to qualify, park, reject, or continue research.
8. **Accumulate the portfolio.** MindrianOS writes an approved candidate with its sources, unresolved questions, status, and relationships to the room opportunity bank. Eureka returns proposals and never writes to that bank itself.

The host skips irrelevant stages, stops on missing evidence or approval, and can keep multiple candidates in the portfolio. It should not force every pair through all methods.
