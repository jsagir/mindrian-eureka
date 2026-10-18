# MindrianOS host integration contract

This describes the host workflow expected by the local Eureka MCP server. It is an integration contract, not a shipped MindrianOS adapter.

For a container launch, configure MindrianOS to invoke the repository's `scripts/run-mcp-container` executable over stdio. Set `MINDRIAN_EUREKA_RS_MODEL_PATH` to a local model directory and `MINDRIAN_EUREKA_DATA_DIR` to the writable job/cache directory in the server process environment. Build the `mindrian-eureka:local` image first. The container has no network, so the model must already exist on the host.

## User journey

1. Ask what the user wants to discover and which room materials are in scope. Preserve exclusions and the objective. Theo/framework guidance may refine the question and review rubric; Theo is not called by the RS capability itself.
2. Resolve the authorized room scope inside MindrianOS. Prepare a bounded artifact bundle containing stable artifact IDs, source references resolvable by MindrianOS, titles, extracted text, and corpus labels. Do not send paths or credentials.
3. Call `scout_plan` with the objective, scope ID, and bundle. Show the proposed analysis and bundle size; request approval when room policy requires it.
4. Call `scout_start`, retain the returned `job_id`, and poll `scout_status`. The user can cancel through `scout_cancel`.
5. Call `scout_result` when complete. Present pair scores as retrieval leads, link each source through MindrianOS, and use the review context with Theo or the user to discuss mechanism, mismatch, and evidence.
6. Let the user accept, deepen, park, or reject each candidate. MindrianOS alone writes accepted opportunities to its portfolio and retains rejection reasons.

## Tool contract

- `scout_capabilities` and `scout://capabilities`: capability name, JTBD, prerequisites, limits, and maturity.
- `scout_plan(request)`: validates a supplied bundle and returns analysis stages, model identity, and counts. It does not execute or fetch research.
- `scout_start(request, idempotency_key?)`: starts a durable job and returns `job_id`, state, scope ID, and retention duration.
- `scout_status(job_id)` / `scout_result(job_id)` / `scout_cancel(job_id)`: job lifecycle and output retrieval.
- `scout_record_review(review)`: records `useful`, `direction_correct`, and `already_known` judgments for a result candidate.
- `scout_evaluation_report()`: descriptive judgment aggregates separated by method and task snapshot/objective.
- `scout_delete_job(job_id)` / `scout_clear_embedding_cache()`: user/host requested data cleanup.

Input is bounded at 2,500 artifacts and 20 MiB of UTF-8 artifact text. Each artifact needs a unique ID, source reference, non-empty text, and `room` or `external` corpus. A host should split exceptionally large rooms into explicit snapshots rather than silently truncate them.

## External research and confidentiality

`external` and `hybrid` requests require a `research_grant_id` and appropriately labeled external artifacts. The ID is audit metadata only; this server does not verify the grant. MindrianOS must validate the grant, user approval, source terms, room scope, and allowed model path before sending the bundle. Research discovery/fetching remains a separate host service. The RS server performs no network research calls and does not write to room or portfolio state.

The job database temporarily holds the submitted request while it runs. Terminal jobs clear their saved request; completed results retain bounded excerpts and source references for up to 30 days. Embeddings are cached separately as derived sensitive data. Align the data-directory placement, encryption, retention, and deletion with room policy.

## Theo and ICM

Theo selects or applies a framework at the host workflow layer, reviews candidate mechanisms, and identifies evidence gaps or next questions. The MCP result is an input to that review, not a Theo conclusion. ICM can record the plan, stage artifacts, and decisions. The current repo does not ship those host integrations.
