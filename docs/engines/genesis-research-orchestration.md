# Genesis: research orchestration inside Discovery

**Proposed role:** coordinate a bounded, evidence-linked investigation by selecting disciplinary lenses, assigning research questions, collecting source-backed findings, and preserving disagreement for Theo/SME review.

**Architecture decision:** Genesis belongs inside MindrianOS Discovery under native Theo. It is a workflow capability, not a peer assistant with its own user relationship or a source of authoritative expertise. It can be exposed to the user as a named “hire” when a question spans multiple disciplines.

## Responsibility boundaries

| Component | Owns | Must hand off |
|---|---|---|
| DataRooms + ICM | Persistent room context, provenance, claims, relationships, decisions, versions | A scoped evidence bundle and source identifiers for each inquiry |
| Theo | User intent, problem frame, method choice, scope/consent checkpoints, whether to continue | Approved research brief and acceptance criteria |
| OM-HMM | Experimental model of coded investigator step sequences, if/when validated | Exploratory sequence observations only; no opportunity score or user classification |
| Genesis | Decompose the approved brief, propose relevant domains, request domain correction, create analytical lenses, plan parallel research, gather/organize findings, expose disagreement | Evidence-linked claims, source gaps, dissent, and unresolved questions |
| SME / evidence adjudication | Test candidate structural mappings, inferences, competing explanations, and claim strength | Accepted, rejected, or unresolved assessments with reasons |
| Builder | Turn an accepted opportunity or unresolved question into a test, prototype, instrument, or implementation plan | Experiment results, artifacts, and revisions back to ICM |

Genesis provides breadth. SME tests whether a proposed mapping is structurally sound. Theo controls the inquiry and method. ICM preserves the evolving evidence record. Builder acts only after the user or Theo chooses an appropriate next step.

## Observed source behavior

The inspected implementation under `/home/jsagi/dev/Mindrian/mindrian-deploy/intelligence/pipelines/genesis/` is a **six-stage linear LangGraph flow**, not the five-stage handoff flow in the architecture note:

1. Context decomposition.
2. Domain identification.
3. Persona generation, with optional BONO Six Hats.
4. Research-plan and collaboration-matrix generation.
5. Search and model-generated panel discussion.
6. Breakthrough synthesis and ranking.

Observed implementation limits that matter before integration:

- Decomposition and domain identification use regular-expression/keyword patterns. Domain confidence is therefore a pattern-match signal, not evidence-grounded probability.
- Personas are generated from templates and competencies. They are analytical prompts, not real experts and not evidence of expertise.
- The research orchestrator creates a plan; the pipeline separately attempts Tavily searches. The code limits collection to five personas and two queries each, takes up to three results per query, and suppresses individual search exceptions.
- If the Tavily import is missing, the pipeline inserts synthetic “Simulated finding” records. Such fallback output must never be presented as completed research.
- Panel responses use a Gemini client and API key. Therefore the current execution path is remote-model-dependent and needs an explicit data-transfer/approval boundary before confidential room material is sent.
- Synthesis extracts scores from generated text, supplies default scores when parsing fails, uses fixed weights and a time-to-value lookup, and treats a nonempty evidence label as satisfying an evidence gate. Those are heuristics, not validated opportunity evaluation.
- The inspected graph is linear, lacks a user-review checkpoint, and has no checkpointer configured in `create_genesis_graph()`; its `session_id` is metadata, not demonstrated persistence/recovery.
- The inspected pipeline returns reports but does not itself persist claim-level evidence, dissent, user decisions, or versioned findings into ICM.

The R&D package at `/home/jsagi/dev/Mindrian/mindrian-deploy/R&D/21_genesis_expert_breakdown/` documents a somewhat different six-stage design and an agent-conducted panel. Treat differences between those artifacts as version drift until a canonical source is selected. No claim is made here that either code path ran successfully in this review.

## Proposed user-facing workflow

1. **Theo frames the job.** Confirm the decision, constraints, room scope, allowed sources, confidentiality class, and what a useful result would look like. Ask the user to approve remote transfer when required by the selected providers.
2. **Genesis decomposes the brief.** Return a concise problem map: function, actors, bottlenecks, constraints, unknowns, and possible domains. Each item links back to the user's input or a room source.
3. **Theo confirms domains and effort.** Show suggested domains and a short rationale/evidence snippet. Let the user add, remove, or correct them. Allocate research budget based on the question, not a fixed persona count.
4. **Genesis creates research lenses.** Generate named perspectives as question sets (e.g., “surface EMG signal reliability reviewer”), each with scope, likely blind spots, evidence needs, search plan, and stop condition. Do not impersonate real people or present synthetic experts as authorities.
5. **Research executes with provenance.** Search approved local/remote sources. Store each result with URL/file ID, publisher/author when available, retrieval date, relevant excerpt, claim supported, and confidence/limitations. Failed or empty searches remain explicit failures; never substitute simulated findings.
6. **Genesis compares, not erases, disagreement.** Keep convergent claims, conflicting claims, independent interpretations, and missing evidence distinct. Use a second perspective to challenge high-impact claims. Do not require consensus or a minimum number of “breakthroughs.”
7. **Theo and the user choose a handoff.** Present opportunities as hypotheses with evidence and counterevidence, assumptions, risk, and next falsifying experiment. The user may ask Genesis to deepen a path, hand a candidate to SME, ask for a countercase, or park/reject it.
8. **ICM records the reviewed outcome.** Persist only with provenance and status: proposed, supported, disputed, rejected, or stale. Record who/what assessed it, the decision date, and the next review trigger. Preserve superseded claims rather than silently overwriting them.

## Minimum output contract

Every Genesis run should return:

- Approved question, scope, and source-transfer status.
- Decomposition with links to originating user statements or room artifacts.
- Proposed domains and the user's edits/approval.
- Research lenses with questions, not claims of real-world expertise.
- Search plan and actual execution log, including unavailable providers and failures.
- Claim-level source records and counterevidence.
- A disagreement register with unresolved differences and what evidence could resolve them.
- Candidate opportunities as hypotheses, each with mechanism, assumptions, mismatch, and a falsifying test.
- Explicit handoff recommendation: more Genesis research, SME adjudication, Builder experiment, or stop/park.
- Reproducibility metadata: run ID, engine/version, provider/model/version where available, source snapshot, timestamps, and artifact hashes.

## Integration judgment

Genesis is useful if it reduces the user's burden of choosing disciplinary lenses and conducting parallel research while preserving source traceability and dissent. It should not be wired directly as “generate personas → run all → rank breakthroughs.” The implementation's keyword domains, synthetic fallback, roleplay panel, score parser, and absent ICM persistence would otherwise inflate apparent confidence and make errors hard to audit.

First integration should be a **research planning and evidence collection workflow** with user-approved domain selection, deterministic source/provenance capture, explicit remote-provider controls, and a reviewed handoff to Theo/SME. Keep panel debate and numerical synthesis behind feature flags until their quality is evaluated against human-reviewed cases. Measure whether users reach a defensible next decision with less manual coordination—not how many personas or breakthroughs Genesis emits.

## First validation experiment

Take three completed MindrianOS room investigations with known source artifacts. Have an independent reviewer define the necessary disciplines and a source-backed brief. Run Genesis in shadow mode on the same material, with remote transfer allowed only for approved material. Compare domain coverage, source support, missed counterevidence, disagreement preservation, and reviewer time. Continue if Genesis reduces coordination effort without increasing unsupported claims or losing any material reviewer-identified domain; otherwise revise the domain-selection or research/handoff stage before enabling synthesis.

This experiment validates workflow usefulness. It does not validate simulated expertise, the HMM, opportunity scores, or the novelty of any candidate.

## Current repo implementation

The repo exposes `research.prepare_multidomain_plan` and `research.group_multidomain_findings` as supporting stages. The first requires Theo/user-confirmed domains and produces bounded research questions; the host must execute approved queries and return sources. The second groups only exact normalized claim strings while preserving supplied positions and source references.

## LATEST Genesis planning capability

`research.run_genesis_local_plan` is now available through the shared `eureka-workflow` CLI and `scout_run_workflow` MCP tool. It runs the five audited LATEST local modules (context decomposer, domain identifier, persona generator, research orchestrator, and handoff protocol) over a **MindrianOS-authorized graph projection**. The projection carries stable artifact IDs and host-resolvable source references; output includes the scope/snapshot and included IDs, references, hashes, and truncation/omission information. Eureka does not read `room.db`, use the visualization export, or write graph state.

This capability creates a research plan and generic broker-ready query handoff. It performs no search or remote model call, ingests no findings, claims no expert review, and does not complete the deployed six-stage Genesis workflow. Domain signals and simulated personas remain heuristic. If no domain produces a persona, the result is `insufficient_domain_signal` and contains no fabricated plan. The bundled source is for local evaluation; reuse rights remain unresolved. The full `research.orchestrate_multidomain` job remains planned pending approved research execution, claim-level synthesis, persistent ICM handoff, and comparative evaluation.
