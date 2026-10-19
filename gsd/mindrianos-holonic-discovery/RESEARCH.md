# Research and source assessment

## Repository and source evidence

- **Verified, current repository:** ADR 0001 establishes standalone Eureka, with MindrianOS owning room permissions, approvals, canonical portfolio state, and graph writes. ADR 0002 proposes one local MCP facade and modular capabilities.
- **Verified, current repository:** `docs/integrations/mindrianos.md` describes a host-supplied scoped bundle and says Eureka does not resolve room paths, fetch research, call Theo, or write room/portfolio state.
- **Verified, latest source ledger:** `research/LATEST` is the consolidated research source available as of 2026-10-18; its own review says research prototypes are not production-ready.
- **Verified, graph-relations source:** modules implement open triads/Adamic-Adar and hypergeometric z, induced 4-cycles and degree-preserving nulls, community bridging, Uzzi-style atypicality, TF-IDF semantic gaps/BTM-lite, Bayesian KL surprise, proposal merge/ranking, traversal, and temporal backtesting. Optional persistent homology uses ripser.
- **Verified, implementation in this repo:** CLI jobs expose the integrated pipeline, temporal backtest, Bayesian surprise over supplied probability arrays, BTM over two supplied corpora, path ranking over host-supplied traversal rows, and bounded graph-neighborhood mapping through the bundled SME core. The graph SME capability remains experimental and local-evaluation-only while source rights and mapping quality remain unresolved.
- **Verified, reported evaluation in source:** the live graph backtest found zero of 30 later edges in the top 200 for every method and baseline. The dated sample was small and clustered. Treat as failed validation, not evidence of performance.
- **Verified, source review caveats:** BONO's 11-file LATEST package and command flow are now inventoried, but full execution remains blocked on absent MindrianOS host services and three human gates; no BONO code has been copied. HSI UMAP/PCA/abort concerns remain; SME live retrieval is untested; source ownership/license questions remain for multiple imported packages. LATEST Genesis's 30-test suite passes in an isolated CommonJS fixture with the matching package-2026 baseline; direct invocation from the Downloads tree currently hits an ancestor `type: module` conflict. Passing upstream tests does not make those modules integrated or license-cleared.

## External prior art and relevance

These sources are cited by the supplied architecture brief. Their applicability is a research rationale, not proof that the proposed architecture will work in MindrianOS.

- RAPTOR (Sarthi et al., ICLR 2024), [arXiv:2401.18059](https://arxiv.org/abs/2401.18059): hierarchical summaries and recursive retrieval motivate multi-resolution projections with evidence links.
- GraphRAG (Edge et al., 2024), [arXiv:2404.16130](https://arxiv.org/abs/2404.16130): local graph retrieval and community-level synthesis motivate both focal and cross-domain analysis.
- Zep / Graphiti (Rasmussen et al., 2025), [arXiv:2501.13956](https://arxiv.org/abs/2501.13956): temporal graph memory motivates explicit history and incremental updates; it does not establish that Eureka or Mindrian currently has temporal integrity.
- W3C [PROV-O](https://www.w3.org/TR/prov-o/): a standard provenance vocabulary to assess for interoperability rather than replace with an incompatible bespoke lineage model.
- Liu et al., *Lost in the Middle*, TACL 2024, [ACL Anthology](https://aclanthology.org/2024.tacl-1.9/): supports evaluating context selection and completeness; it does not imply that shorter projections are always superior.
- [Model Context Protocol specification](https://modelcontextprotocol.io/specification): relevant to tool/resource contracts. MCP is not a substitute for MindrianOS authorization, audit, or review.
- Holons and Focus essay, [Inference Engineer](https://inferenceengineer.substack.com/p/on-holons-and-focus): the supplied brief reports this as an initial conceptual source and says it was not directly retrievable in its research pass. Verify its text and terminology before attributing requirements to the author.

## Relevant comparisons

- Hierarchical retrieval can reduce irrelevant context but risks projection loss; retain direct source references and disclose omissions.
- Graph traversal can find only relationships represented by edges; semantic and structural discovery must also search beyond existing portals.
- Similarity, bridge scores, novelty, evidence strength, confidence, and validity are distinct dimensions and must not be collapsed into an opportunity score without evaluation.
- Read-only graph analysis is feasible as an engine slice. Authorized scope, source resolution, evidence retrieval, and accepted state remain host functions.

## Latest research engine coverage map

| LATEST family | Current Eureka coverage verified in this repository | Readiness/action |
|---|---|---|
| `algorithms` (Genesis, Jason, OM-HMM) | Jason CLI/MCP and OM-HMM CLI/MCP exist. `research.run_genesis_local_plan` now exposes LATEST's five local planning modules over a MindrianOS-authorized artifact projection; the earlier confirmed-domain planner/grouping stages remain. LATEST's 30 upstream tests pass under the documented compatibility fixture. | Keep all methods experimental. Genesis still needs shadow evaluation against completed investigations; only MindrianOS may retrieve outside research, call its model services, persist ICM, or write graph state. This local planner does not complete the separately deployed Genesis researcher workflow. |
| `analogies` | Mechanism recall, SAPPhIRE fitness, SME structural mapping/evidence workflow, and the LATEST analogy-seeded transfer-whitespace method now have CLI/MCP stages. | Experimental; source/license, real transfer cases, vector provenance, external novelty checks, and host research remain gates. |
| `bono` | Six-hat review preparation only | LATEST source flow inventoried; shared graph, egress, HITL, run-state, and close-loop dependencies are MindrianOS-owned and absent from this engine package; full debate remains blocked |
| `eureka` | Local opportunity signals, selected workflow steps, Genesis planning, the LATEST weak-signal tail classifier, deterministic critic Stage A, host-brokered Stage B prompt evaluation, and experimental LATEST graph-event harvesting are available. Calibration and qualification are not ported. | Harvest requires a complete authorized host snapshot and bank dedup state; other stages consume host-computed signals or local-judge responses. These outputs are not qualified opportunities. Keep the full Eureka job blocked; preserve host evidence, qualification, and review. |
| `graph-relations` | Packaged read-only local graph runner and local Neo4j CLI; MCP accepts host snapshots, and graph neighborhoods can be mapped through the bundled SME core | Experimental; see current suite result in VALIDATION.md; ranking backtest remains failed/unvalidated |
| `eureka` / Jason | Existing local text-difference engine plus claim/evidence completeness stage | `analysis.critique_pitch` is now a clearly scoped local composition; full generative critique, graph/research access, and truth adjudication remain outside the engine |
| `hsi` | HSI pair scoring, HSI-seeded room whitespace, baseline-gap detection, and host-brokered external-whitespace analysis are callable | Baseline-gap method uses deterministic PCA fallback; external literature analysis uses host-supplied grant-linked papers and vectors. UMAP path, source fidelity/rights, and human-rated corpus validity remain open |
| `rs` | Local RS pair discovery with CLI/MCP and job lifecycle | Experimental; source fidelity, model evaluation, real caller and network integration remain |
| `sme-agent` | Local mapping plus host-brokered planning, validation and finalization stages | Host-brokered/experimental; live retrieval not implemented in engine and attribution/license unresolved |

“Coverage verified” means a capability or source file is present, not that it is validated for production. This table is bounded to `research/LATEST`; it does not claim every prototype in parent archives has been incorporated.

At the time of the origin audit, the catalog had 61 entries and 53 runnable services. Its per-capability [algorithm origins and rationale register](../../docs/algorithm-origins-and-rationale.md) records source lineage and user-facing JTBD while distinguishing established theoretical antecedents from user-provided packages and repository adaptations. It marks unknown authorship/rationale explicitly and separates the two different “RS” meanings: similarity-disagreement pair scoring is not Hughes's reverse-salient bottleneck concept. Eureka portfolio dimension/AHP scoring consumes a MindrianOS-authorized cohort and source-linked RS signal; it remains a heuristic portfolio signal, not opportunity qualification. The opportunity-statement stage emits an explicitly critic-pending, unbanked draft from host-supplied data. RS domain analysis, differential scoring, pair-set quality gating, query-matrix generation, document preprocessing, innovation classification, breakthrough scoring, deterministic commercial hypothesis generation, thesis generation, and paper-to-author extraction are separate local CLI/MCP stages; they neither read room data, perform evidence retrieval, nor resolve the host expert directory. Critic Stage A consumes vectors and graph neighbors supplied by MindrianOS; Stage B consumes responses from the MindrianOS local judge. Opportunity graph harvest consumes an authorized snapshot and host-computed bank-dedup state, returning pending signals. HSI pair-seeded, baseline-gap, external-literature, problem-type interpretation, and RS-seeded downstream whitespace analyses consume host-authorized artifact and graph-derived inputs; external-literature analysis requires host-approved research lineage and inspects only the retrieved set. The HSI interpretation stage uses MindrianOS framework mappings to route Un-Defined, Ill-Defined, Well-Defined, and Wicked gap types to different question/framework paths; it does not infer type from raw text. None of these stages accesses `room.db` or performs external retrieval. The MindrianOS navigation-owned authorization/projection adapter remains a host integration task. Calibration, qualification, BONO debate/fan-out, and the complete Genesis researcher workflow are not production-ready Eureka jobs.

**Current catalog update (2026-10-19):** the catalog now has 66 entries, with 58 runnable services and 8 still blocked or planned. Five graph signals formerly available only inside a composite are independent CLI/MCP services. All 66 entries remain in the origins register.

## Remaining research questions

- Which current MindrianOS nodes represent knowledge boundaries, and which are ordinary claims, evidence, sources, or entities?
- Which graph properties are authoritative, and what are the exact temporal and provenance conventions?
- Can the host export a bounded, stable-ID snapshot that applies row-level authorization before Eureka receives it?
- Which latest algorithms have source code, repeatable tests, licenses, and meaningful baselines?
- How should wicked-problem exploration and opportunity generation be evaluated without rewarding speculative links?
