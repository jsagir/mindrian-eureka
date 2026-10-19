# MindrianOS host integration contract

This contract defines how MindrianOS should use the `mindrian-eureka` repo through its existing `/mos:eureka` workflow and through MCP. The repo provides the engine runtime and a host workflow specification; an adapter from the existing research-planner route to this capability MCP is still to be wired. The two surfaces must use the same capability definitions, schemas, runtime settings, and result interpretation; they are not two separate discovery systems.

## The two surfaces and their authority

| Surface | What it means in MindrianOS | Owns | Must not do |
|---|---|---|---|
| `/mos:eureka` in the MindrianOS plugin | The existing user-facing conversation and workflow. MindrianOS resolves the active room, clarifies the discovery objective, calls Theo/framework guidance when useful, and decides which capability to hire. | Room binding, user intent, scope, approval cards, Theo, `/mos:status`, `/mos:find-connections`, `/mos:qualify-opportunity`, ICM, graph and portfolio writes. | Treat a similarity-ranked pair as an opportunity; bypass room gates; silently run every engine. |
| `eureka-mcp` | The MindrianOS host's callable capability service. The host sends an authorized, bounded artifact bundle and calls the job/capability tools. | Capability discovery, input validation, bounded computation, job state, engine/runtime metadata, and source-linked candidate results. | Resolve a room path, expand scope, fetch outside research, call Theo, or write to MindrianOS graph/portfolio. |
| `eureka-rs` / `eureka-sme` / `eureka-omm` CLI programs | Direct, operator-facing engine interfaces for local development, reproducible runs, and environments where a prepared bundle is already available. | Their named computation over explicit input files. | Claim to be the complete `/mos:eureka` workflow or substitute for MindrianOS room authorization and review. |

The host workflow and the MCP tools are complementary: a user starts with `/mos:eureka`; MindrianOS then invokes this repo's MCP when configured. The standalone engine CLIs are useful for direct, auditable capability runs, but a raw CLI invocation does not acquire MindrianOS room context by itself. If MCP is unavailable, MindrianOS may call an engine CLI only after it has prepared the same scoped bundle and must preserve the same approval and filing steps. If it cannot do that, it reports the integration as unavailable instead of silently changing behavior.

MCP gives MindrianOS a stable tool boundary. It does not provide room access, Theo's judgment, user approval, external research, or graph persistence. No capability may infer permission from `scope_id` or `research_grant_id`; MindrianOS validates those before sending data.

The repo's workflow specification is [the MindrianOS opportunity-discovery workflow](../../src/mindrian_eureka/data/mos-opportunity-discovery.v1.json). It is published as `scout://workflows/mos-opportunity-discovery` and through the `scout_host_workflow` MCP tool for a connected host to inspect. The `/mos:eureka` research-planner adapter should treat it as the handoff contract: Eureka performs the selected computation and returns the next host action; MindrianOS executes its own native command and approval workflow. Eureka does not issue slash commands on the host's behalf.

The SME cross-domain discovery + verification workflow is described separately in [cross-domain research](../engines/cross-domain-research.md). The beta 70 integration still needs a host adapter to translate `research_run` output to the Scout's claim-level bundle contract and to retain mapping and portfolio lineage.

For a container launch, configure MindrianOS to invoke the repository's `scripts/run-mcp-container` executable over stdio. Set `MINDRIAN_EUREKA_RS_MODEL_PATH` to a local model directory and `MINDRIAN_EUREKA_DATA_DIR` to the writable job/cache directory in the server process environment. Build the `mindrian-eureka:local` image first. The container has no network, so the model must already exist on the host.

## `/mos:eureka` user journey

1. **Read room state.** Resolve the active room once through MindrianOS's room resolver. Read `/mos:status` and relevant room material so the scout starts from current, room-bound context. A status summary is a navigation aid, not proof that a section is empty; include explicitly selected source files such as the JHTV catalog when they are outside the status index.
2. **Frame the wicked challenge.** Preserve the user's desired decision, constraints, exclusions, and evidence standard while keeping uncertainty, connected system parts, and competing problem frames visible. Treat uncertainty as territory to explore for opportunity, not merely noise to remove. Theo may guide method choice. Ask a focused question only when a missing answer changes scope, data handling, or method choice.
3. **Select capabilities.** Read `scout_capabilities`; choose only capabilities that fit the job and whose maturity/prerequisites are acceptable. Do not run every engine by default. Explain the job in user language and show which sources it will inspect.
4. **Prepare the scoped bundle.** MindrianOS supplies stable artifact IDs, resolvable source references, titles, content hashes, text, and corpus labels. It records the exact input snapshot and excludes unrelated files. It never passes room paths, credentials, or the entire room directory to a worker.
5. **Plan and approve.** Call `scout_plan`. Present the objective, room/snapshot, input counts, selected capability, model/runtime, expected outputs, limits, and any data-transfer implications. Obtain whatever room-policy approval applies before starting. For a local-only run, explicitly state that content stays on the local execution boundary; model download is a separate choice.
6. **Run and monitor.** Call `scout_start`, keep the returned `job_id`, and use `scout_status` while it runs. Offer `scout_cancel` if the user stops or changes scope. A failed, blocked, or partial result must remain distinct from “no opportunities found.”
7. **Inspect candidates.** Call `scout_result`. MindrianOS resolves the returned `source_ref`s into room links and presents the actual source evidence, method/version, limitations, and uncertainty. Retrieval/similarity signals are leads, not opportunity evidence.
8. **Connect and challenge.** For selected candidate pairs, MindrianOS can use `/mos:find-connections` to trace relationships and evidence in its graph. If outside evidence is needed, Theo/MindrianOS frames the questions and the host's research workflow obtains the relevant approval and sources; Eureka does not fetch them. SME mapping or verification is a distinct next capability, not an automatic truth check.
9. **Qualify and preserve.** Present a candidate to `/mos:qualify-opportunity` only after its source trail and counterevidence are available. The user makes the qualification/disposition decision. MindrianOS writes an approved proposal with lineage and retains rejected/parked reasons; Eureka never writes to the room graph or portfolio.
10. **Accumulate.** Preserve each run's snapshot and proposal identifiers so MindrianOS can deduplicate, relate, revisit, and deepen candidates across rooms. A run may add to a portfolio; it does not replace the portfolio with only the room currently open.

For a catalog-scale run such as JHTV, the host first normalizes each catalog item to one stable artifact record and preserves its source URL, category path, extraction date, and input hash. Eureka processes the complete authorized snapshot, returns a bounded candidate set with both source IDs, and reports coverage and skipped/uncertain records. MindrianOS then uses its connection, research, and qualification flows on selected candidates. The whole-catalog pair ranking is only the discovery pass; the researched portfolio is the decision product.

If the user asks for `/mos:status`, `/mos:find-connections`, or `/mos:qualify-opportunity`, MindrianOS performs those host workflows itself. Eureka may recommend the next one, but must not simulate its result or claim to have invoked it unless the host actually did so.

## Tool contract

- `scout_capabilities` and `scout://capabilities`: capability name, JTBD, prerequisites, limits, and maturity.
- `scout_host_workflow` and `scout://workflows/mos-opportunity-discovery`: the host-owned `/mos:eureka` stages, boundaries, and approvals.
- `scout_plan(request)`: validates a supplied bundle and returns analysis stages, model identity, and counts. It does not execute or fetch research.
- `scout_start(request, idempotency_key?)`: starts a durable job and returns `job_id`, state, scope ID, and retention duration.
- `scout_status(job_id)` / `scout_result(job_id)` / `scout_cancel(job_id)`: job lifecycle and output retrieval.
- `scout_record_review(review)`: records `useful`, `direction_correct`, and `already_known` judgments for a result candidate.
- `scout_evaluation_report()`: descriptive judgment aggregates separated by method and task snapshot/objective.
- `scout_delete_job(job_id)` / `scout_clear_embedding_cache()`: user/host requested data cleanup.
- `scout_sme_prepare_research(request)`: freeze exact mechanism-discovery or per-inference verification queries for the host approval UI.
- `scout_sme_validate_research_bundle(request)`: check exact query/source/claim lineage in the host-returned bundle, not the truth of approval.
- `scout_sme_map(request)`: run local deterministic structural mapping on source-claim-linked inputs.
- `scout_sme_finalize(request)`: validate reviewer assessments and return cited inference records; it does not file them.
- `decision_compare_sequence_patterns(request)`: compare a human- or Theo-coded decision sequence under caller-supplied HMM models. The host must obtain consent, retain the feature-coding provenance, and present the result as unvalidated relative model fit rather than a person score.

For cross-domain pair finding, the CLI and MCP call the same method implementation and result contract, but their execution lifecycles differ: `eureka-rs` is a direct bounded run that reads an explicit JSON bundle; MCP provides the durable `plan → start → status/result/cancel` job lifecycle. Both return the same `host_handoff` guidance. The other engine CLIs execute their named method and are not yet unified under the RS job lifecycle. Handoff guidance recommends a next host action; it does not execute a `/mos:*` command, grant approval, or write graph state. The MindrianOS host must preserve the same scope manifest, model identity, source references, approval rules, and result caveats whichever execution surface it uses. Never pass an arbitrary filesystem path through an MCP request; never use a direct CLI call to avoid a MindrianOS gate.

Input is bounded at 2,500 artifacts and 20 MiB of UTF-8 artifact text. Each artifact needs a unique ID, source reference, non-empty text, and `room` or `external` corpus. A host should split exceptionally large rooms into explicit snapshots rather than silently truncate them.

## External research and confidentiality

`external` and `hybrid` requests require a `research_grant_id` and appropriately labeled external artifacts. The ID is audit metadata only; this server does not verify the grant. MindrianOS must validate the grant, user approval, source terms, room scope, and allowed model path before sending the bundle. Research discovery/fetching remains a separate host service. The RS server performs no network research calls and does not write to room or portfolio state.

The job database temporarily holds the submitted request while it runs. Terminal jobs clear their saved request; completed results retain bounded excerpts and source references for up to 30 days. Embeddings are cached separately as derived sensitive data. Align the data-directory placement, encryption, retention, and deletion with room policy.

## Theo and ICM

Theo is the MindrianOS reasoning and framework service used by the host workflow. The host may consult Theo's framework, concept, and review guidance while framing the work and challenging candidate mechanisms. In the current available Theo MCP surface, these calls provide general method guidance; they do not accept the arbitrary JHTV case bundle, run `/mos:find-connections`, evaluate a specific opportunity, or write to the room graph. Therefore the host must not label a candidate “Theo-reviewed” unless Theo has actually been given and reviewed that case through an available case-capable interface. A generic Theo review guide is a rubric, not case evidence.

The engine MCP does not call Theo directly. MindrianOS owns Theo calls, room context, ICM run records, and graph/portfolio state. ICM can record the plan, stage artifacts, and decisions. This repository publishes the contract, but the adapter from the existing `/mos:eureka` research planner to these capabilities is still not shipped here.
