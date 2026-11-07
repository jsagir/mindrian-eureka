# Phase 3: Host Integration and Replay Rebuild - Context

**Gathered:** 2026-11-07
**Status:** Decisions set by the planner from the roadmap and from facts checked on 2026-11-07. The owner may overrule any D-NN before execution.
**Source:** `.planning/ROADMAP.md` (Phase 3), `.planning/REQUIREMENTS.md` (HOST-01, HOST-02), the Phase 2 and 2.3 summaries, the MCP server code, and read-only checks of the plugin checkout and of the partner room (see Verified facts).

<domain>
## Phase Boundary

HOST-01: a MindrianOS user can start the one-command run from `/mos:eureka`, through the Eureka MCP server, with room scope and approval rules respected, and gets the ranked output with the host hand-off block back.

HOST-02: the graph-derive replay behind JHTV OPP-027 to OPP-031 either has a recorded repeatable script, or the five candidates carry an honest "provenance gap" mark.

In scope (Eureka repo only): the MCP tool surface for the run, the catalog entry and JSON schemas, the approval gate on the Eureka side, the result envelope, the limits parity of the MCP pair tools, a hand-off contract document for the plugin team, the provenance-gap record, the script that emits the provenance-gap list, and the doc updates.

Out of scope: any edit in the MindrianOS plugin checkout (it is owned by another session under a GSD-only rule: this phase reads it and never edits it); any write to a room, a registry or a room database; any model call; the room-side "provenance gap" mark (a host-owned write that needs approval, handed off); a replay script (see D-10); a push.
</domain>

<decisions>
## Implementation Decisions (planner decisions)

### D-01 Scope split
Eureka side = the tools, the contracts, the gate, the envelope and the hand-off document. Plugin side = the command wiring and the approval card. The plugin side is only described, in `docs/mos-eureka-engine-run-contract.md`, so the plugin phase can plan it. No plan edits the plugin checkout. Every plan that reads it records `git status --short | wc -l` of the plugin checkout before and after and requires equal values.

### D-02 Tool surface and capability
Two new MCP tools: `scout_plan_pair_screen` (no execution) and `scout_start_pair_screen` (starts a durable job). The existing `scout_status`, `scout_result`, `scout_cancel`, `scout_delete_job` and `scout_record_review` serve the new job without change. Capability id `opportunity.run_pair_screen`, catalog status `experimental`. The names follow the `scout_` prefix and the "plan, start, status, result" order of the existing pair tools, so the plugin bridge (which allows a fixed list of routes) needs two list entries and no new job tools.

### D-03 Input is a host-supplied bundle, never a path
The request holds `objective`, `scope_id` (required), `snapshot_id` (required), `artifacts` (2 to 3,000 items, the existing artifact shape, corpus `room` only), `top_k` (1 to 200, default 200) and, for the start call, `approval`. No filesystem path crosses the MCP boundary. External corpus is refused. A bundle above 3,000 artifacts is refused with a plain message to split the room into snapshots; it is never truncated (unlike `eureka run`, which records a cap).

### D-04 The run is the Phase 2 run
The job stages the bundle as one private CSV file in a private folder under the Eureka data directory, then calls `run_pipeline` (the same code as `eureka run`) with `use_cache=False`. The output files are the same files, with the same manifest. The staged input folder and the output folder are deleted when the result envelope is built or when the job fails or is cancelled. No derived vector is kept. Progress and cancel go through a console object that calls the job stage callback and raises the existing cancel exception between stages.

### D-05 The approval step on the Eureka side
`scout_plan_pair_screen` validates the bundle, checks the corpus and the model without loading it, returns a `plan_digest` (sha256 of the canonical request basis) and records a receipt (digest and times only, no text, kept 24 hours). `scout_start_pair_screen` refuses unless the request carries `approval` with the matching `plan_digest` and a non-empty `approval_ref`, and a live unconsumed receipt exists. A receipt is single use and safe to retry with the same idempotency key. A refusal is a structured answer with `status: refused` and a `reason` code. Eureka cannot verify that a person approved: `approval_ref` is audit metadata, and the result says `verified_by_engine: false`. The real approval card is a host duty.

### D-06 Result envelope
Schema `eureka.pair-screen.v1`. It holds the exact text of the four deterministic output files (`unusual-pairs.json`, `wording-and-meaning-pairs.json`, `ranked-pairs.md`, `manifest.json`) with their sha256, the digest of `corpus/records.jsonl` without its text, the id map (record id to host artifact id and source ref), a de-duplicated `outputs` list of pairs (so `scout_record_review` and the host hand-off work), `scope`, `approval`, `counts`, `caps_hit`, `warnings`, `host_handoff`, `room_write: not_performed`, `portfolio_write: not_performed` and the label. `run-info.json` is not returned (it holds times).

### D-07 Determinism
No job id, approval reference, clock value or path enters a hashed output file. Two jobs on the same bundle give equal file hashes. A test proves it.

### D-08 Limits parity
The new tools use `limits.MAX_ARTIFACTS` (3,000) and `limits.MAX_TOP_K` (200). The carry-over from STATE ("MCP schemas still cap at 2,500 artifacts and 100 pairs") closes for the three pair-engine routes only: `scout_start` (`ScoutRunInput`, `cross-domain-pairs-input.v1.json`), `scout_start_opportunity_signal_scout` (`OpportunityScoutInput`, `discovery-signals-input.v1.json`, the check in `opportunity_discovery.py`) and the wording-and-meaning route (`hsi-pairs-input.v1.json`). Every other 2,500 cap (graph, whitespace and other families) stays and is pinned by a test.

### D-09 Hand-off contract document
`docs/mos-eureka-engine-run-contract.md`, 14 headings pinned by a test, in the style of `docs/room-seed-contract.md`. Plugin facts are labelled PROVEN (read, with the plugin commit, never a machine path) or ASSUMED. It lists open questions for the plugin phase. It also carries the HOST-02 hand-off (the list to mark and the write boundary).

### D-10 HOST-02 outcome
The replay data is not in the Eureka repo (PROVEN by search). So no replay script is planned. The deliverables are: ONE record file for the reader, `docs/jhtv-replay-record.md` (front matter `outcome: provenance_gap`, `room_mark: pending_approval`; see D-12), and its machine twin (a partial replay from the stored vectors needs a host-approved read-only vector export; deferred as Phase 3.1; F14 proves the counts only; outcome stays `provenance_gap`) `evaluations/graph-derive-replay/record.v1.json` plus the emitted list `evaluations/graph-derive-replay/gap-list.v1.json` (renamed from `provenance-gap.v1.json` by plan 03-06; accepted 2026-11-07 after the plan check), a script `scripts/emit-provenance-gap-list` that emits the list for the host (JSON and plain text, byte-stable, with a committed golden file), and a hand-off item for the room-side mark. The record states what exists outside the repo (the partner room store holds 2,130 stored vectors today; the plugin derive code scores all pairs as n*(n-1)/2 and calls a pair CONVERGES at cosine 0.55 or more) as input for a possible later plan. HOST-02 closes on the Eureka side with the record, the list and the script. The room mark stays pending a host-approved write.

### D-12 The one record file for Phase 4 (coordinator contract of 2026-11-07)
Phase 3 writes exactly one record file that Phase 4 plans 04-03 and 04-04 read: `docs/jhtv-replay-record.md`. Its front matter holds the key `outcome` with the value `provenance_gap` or `replayed`. If `replayed`, it also holds `claims`, `pairs` and `two_run_hashes_equal`. If `provenance_gap`, it also holds `room_mark` with the value `done` or `pending_approval`. This phase ends with `outcome: provenance_gap` and `room_mark: pending_approval` (D-10: the data is not in the repo, and the room mark is a host-owned write that needs approval). An executor never sets `room_mark: done`. Only a later Eureka quick task sets it, after the host session reports an approved room write. Other files may carry the detail, but the front matter of this file is the contract. No Phase 3 plan edits `src/mindrian_eureka/cli.py` (Phase 4 plan 04-01 adds 3 lines there for `check-example`); Phase 3 runs first, and the new script of this phase is reached by `scripts/emit-provenance-gap-list` and `python -m`, not by a `eureka` subcommand.

### D-11 House rules (all plans)
Offline, deterministic, no model call in any new code path except the engines `run_pipeline` already uses. Every result keeps `candidate, not verified`. No person's name in any repo file, test or fixture. Plain English in docs: no em dash, no en dash, no short engine codes, no institution word, the partner named as JHTV only when needed. Explicit-path commits (`git commit --only <paths>`), never stage `story/`, never push, the Co-Authored-By trailer from the session reminder on the last line of each commit message. The agent protocol applies to executors: short English, report fields STATUS, CHANGED, VERIFIED, UNVERIFIED, RISKS, NEXT.
</decisions>

<verified_facts>
## Verified facts (checked 2026-11-07 by the planner)

| # | Fact | Label | How |
|---|------|-------|-----|
| F1 | The repo holds no graph-derive script, no claim table, no vector table and no `derive_results.json`. The words appear only in planning files and in generic "graph-derived" docs text. | PROVEN | `grep -rIl` over the repo excluding `.git`, `.venv`, `story`; `find` for derive, replay and claims names |
| F2 | 2,267,385 equals 2,130 times 2,129 divided by 2. 2,239,786 (the stored wording-and-meaning pair count) equals 2,117 times 2,116 divided by 2. | PROVEN | arithmetic |
| F3 | The partner room cites the replay in OPP-027 to OPP-031 (`discovered_from`, `citation`): "Graph-derive replay over the room's stored eureka_vec embeddings (MongoDB/mdbr-leaf-ir, 2,130 claims, 2,267,385 pairs, CONVERGES floor 0.55), 2026-10-21, then a title scan of the full catalog" and "(derive_results.json, 2026-10-21)". | PROVEN | read the room files (read only) |
| F4 | The room store holds 2,130 rows in `eureka_vec_rowids` and in `eureka_vec_metadatatext00`. Content was not read. | PROVEN | read-only immutable open, row count only |
| F5 | `derive_results.json` was not found in the repo, the partner room, the plugin checkouts, or the dev, rooms, work, output and research folders (depth 8). | PROVEN for the folders searched | `find -iname` |
| F6 | The plugin file `lib/core/graph-derive-classifier.cjs` classifies a pair as CONVERGES at a topical cosine of 0.55 or more (`DERIVE_CONVERGES_FLOOR_DEFAULT`), counts all pairs as n*(n-1)/2 (`countAllPairs`), and since commit e2e819d43 (2026-10-21, Phase 379.1) prunes pairs by top-k cosine. | PROVEN (code read) | read only |
| F7 | That the 2026-10-21 replay ran this plugin code, and which code state, is not recorded in the room. | INFERRED / UNVERIFIED | the figures match F6; no run record found |
| F8 | The plugin bridge allows a fixed list of MCP routes (`ALLOWED_MCP_ROUTES`: `scout_run_workflow`, `scout_start`, `scout_sme_map`, `decision_compare_sequence_patterns`, `decision_fit_sequence_patterns`, `scout_start_opportunity_signal_scout`) and a fixed async list (`ASYNC_ROUTES`: `scout_start`, `scout_start_opportunity_signal_scout`). It calls `scout_capabilities`, then `scout_capability_contract` (needs input and output schemas), then the route with one `request` argument, then polls `scout_status`, then `scout_result`, and requires `result.capability_id` to equal the requested id. | PROVEN (code read) | plugin `lib/mcp/tools/eureka-capability-run.cjs` and `eureka-capability-jobs.cjs`, read only |
| F9 | The plugin adapter `eureka_graph_opportunity_scout` caps `node_ids` at 2,500 and `top_k` at 100 on its side, and builds the request from `eureka_graph_prepare_artifacts` (objective, scope_id, snapshot_id, artifacts, top_k). | PROVEN (code read) | plugin `lib/mcp/tools/eureka-graph-opportunity-scout.cjs` |
| F10 | `/mos:eureka` in the plugin runs the research-planner perspective by default (subcommands `run`, `enable`, `enable engine`); the engine tools sit behind `enable engine`. | PROVEN (code read) | plugin `commands/eureka.md` |
| F11 | `run_pipeline(request, console)` is a plain function that prints nothing and catches no error; its docstring names the MCP server of a later phase as a caller. `RunRequest.use_cache=False` uses a throwaway cache. | PROVEN (code read) | `src/mindrian_eureka/run/pipeline.py` |
| F12 | The engine code already accepts 3,000 artifacts and top_k 200 (`limits.py`); only the MCP models, three input schemas, one engine check and one catalog sentence still say 2,500 and 100. | PROVEN (code read) | `mcp_server.py`, `cross-domain-pairs-input.v1.json`, `discovery-signals-input.v1.json`, `hsi-pairs-input.v1.json`, `opportunity_discovery.py`, catalog line "2..2500 source-linked local artifacts" |
| F13 | Baselines on 2026-11-07: `ruff check src tests` reports 1465 errors; `mypy src` reports 88 errors in 17 files; the full suite on 2026-11-07 reported 1482 passed, 28 skipped, 0 failed (feasibility run; the 1493 figure of the plan 02.3-04 summary is stale). | PROVEN | commands run |
| F14 | Feasibility check 2026-11-07, read-only: the partner room store table `eureka_vec` holds 2,130 vectors of 384 dimensions; 2,130*2,129/2 = 2,267,385 equals the cited pair count; 2,165 pairs reach cosine 0.55 on the stored vectors. The model `mdbr-leaf-ir` is NOT in the Hugging Face cache, so the run cannot be repeated. The store file is dated 2026-10-29 and the cited replay 2026-10-21. `derive_results.json` exists nowhere on this machine. | PROVEN (counts), INFERRED (same set) | read-only immutable open, in-memory arithmetic, no write |
| F15 | Plugin Phase 387 (checkout `~/dev/MindrianOS-Plugin-release`, commits 173a5b1e9 and 25838bb02) owns adoption, doctor and typed refusals; it does not add or call the pair-screen tools. The two new routes need entries in `ALLOWED_MCP_ROUTES`, `ASYNC_ROUTES` and the `routeGate` table of `lib/mcp/eureka-tool-contract.cjs`; the plugin adapter caps `top_k` at 100 and `node_ids` at 2,500 (F9) and must lift them to 200 and 3,000. | PROVEN | grep of the plugin checkout, read-only |
| F14 | Phase 2.3 plan 05 is executed (commits 3ce6b25, edf98a0, c84c83c): `docs/room-seed-contract.md` and the `## The reverse leg: a room seed` section of `docs/integrations/mindrianos.md` exist. | PROVEN | `git log` |
</verified_facts>

<canonical_refs>
- `src/mindrian_eureka/opportunity_pairs/mcp_server.py`, `opportunity_pairs/jobs.py`, `opportunity_pairs/host_handoff.py`
- `src/mindrian_eureka/run/pipeline.py`, `run/corpus.py`, `run/mapping.py`, `run/output.py`, `run/console.py`, `run/contracts.py`
- `src/mindrian_eureka/hub/reader.py` (`load_run`: hash-checked reader of a run folder)
- `src/mindrian_eureka/limits.py`, `src/mindrian_eureka/models.py`, `src/mindrian_eureka/contracts.py`
- `src/mindrian_eureka/data/capability-catalog.v1.json`, `data/mos-opportunity-discovery.v1.json`
- `docs/integrations/mindrianos.md`, `docs/room-seed-contract.md` (style model), `docs/rs-release-gate.md`, `docs/hsi-rs-jhtv-reproduction.md`
- `.planning/phases/02-one-command-run-and-doctor/02-06-SUMMARY.md`, `.planning/phases/02.3-room-seed-hand-off-to-mindrianos/02.3-05-PLAN.md`
- `tests/conftest.py` (fixtures `isolated_env`, `fake_model_dir`, `stub_encoders`, `no_network`), `tests/fixtures/hub_public/run` (a frozen run folder; never regenerate), `tests/fixtures/rs_parity/corpus.json` (32 synthetic artifacts)
</canonical_refs>

<deferred>
- A replay script over a host-approved read-only export of the room vectors (a possible Phase 3.1; needs an owner decision, see the report question).
- The room-side provenance-gap mark (host-owned write, needs approval; handed off).
- Lifting the 2,500 caps of the graph and whitespace families.
- A hub action for the MCP result.
</deferred>
