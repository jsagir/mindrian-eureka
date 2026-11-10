# Phase 6: Job store hardening for the MindrianOS plugin - Context

**Gathered:** 2026-11-10
**Status:** Ready for planning
**Source:** `.planning/ROADMAP.md` Phase 6 (goal and six success criteria), the 2026-11-08 cross-session review with the plugin session, a read of `src/mindrian_eureka/opportunity_pairs/jobs.py` and `mcp_server.py` at HEAD `0e30aa8` (last change to `jobs.py`: commit `4617c7c`, Phase 03-04), the plugin files `lib/mcp/tools/eureka-capability-jobs.cjs`, `lib/mcp/tools/eureka-capability-run.cjs` and `tests/test-392-eureka-deadline.cjs` (read only), and two experiments run on 2026-11-10 (facts F5 and F6 below).

<domain>
## Phase Boundary

Eureka runs each asynchronous capability as a job. The job record lives in `jobs.sqlite3` under the data directory (`MINDRIAN_EUREKA_DATA_DIR`, default `~/.local/share/mindrian-eureka`). The MindrianOS plugin starts one engine process (`uv run --no-sync --offline --locked --no-python-downloads --project <root> eureka-mcp`) for each job session, keeps that process open across `scout_start`, `scout_status`, `scout_result` and `scout_cancel`, and closes it at the terminal result, at the 30 minute session expiry, or when the transport dies. At most 8 sessions are active at once. Several engine processes therefore share one `jobs.sqlite3` at the same time.

Today the store was written for one process. A second process that opens the store rewrites the rows of the first. A status read can delete a row. A finished job can change state again. A cancel is a request that the worker can miss. The engine process keeps running after its host is gone.

In scope: the five behaviours below, as failing tests against the current store first, then the fix; a close-out that drives the plugin's own expectations through the real MCP route; the README refresh; a short contract note for the plugin session.

Out of scope: a change to the plugin repository (hand-offs only); a new network path; a change to the ranking code or to any result schema of a completed job; a job that resumes after a host restart; a memory guard (LIM-01, v2); the 30 day retention value; the 8 active job limit value.

## What the plugin expects (the contract lines this phase serves)

| Id | Plugin expectation | Plugin anchor | What the store does today |
|----|--------------------|---------------|---------------------------|
| P1 | One session owns one `job_id`; "No active Eureka MCP session owns this job_id" is the only not-found answer. | `eureka-capability-jobs.cjs:132-146` (`getSession`), `:17-19` (session map, 30 min, 8 max) | Any process may drive any job (D-01). |
| P2 | `scout_status` is a pure read, polled every 250 ms by `waitForJob` and by `jobStatus`. | `eureka-capability-run.cjs:115-135`, `eureka-capability-jobs.cjs:148-166` | A read can delete an expired row; opening the store rewrites running rows (D-02). |
| P3 | A terminal state (`completed`, `completed_empty`, `failed`, `blocked`, `cancelled`, `expired`) is final; the plugin closes the session on it. | `eureka-capability-jobs.cjs:16`, `:183-200` | No guard; a late write moves a terminal row back to `running` (D-03). |
| P4 | Cancel is cooperative; after `scout_cancel` the plugin polls up to 10 s for a terminal state, then closes the child. | `eureka-capability-jobs.cjs:222-239`, `:250-263`; `eureka-capability-run.cjs:137` | The persisted flag is never read and is wiped at the first step (D-04). |
| P5 | A dead engine child leaves the session map within 1 s; the plugin never resumes a job after a restart. | `eureka-capability-jobs.cjs:117-126`, `:241-248`; `tests/test-392-eureka-deadline.cjs:161-181` | The engine process survives its host while a job runs; the job runs on with no reader (D-05). |
| P6 | Every `callTool` carries a deadline; a `RequestTimeout` maps to `engine_timeout`. | `eureka-tool-contract.cjs:236-239`, `:254-257` | No change needed in the store; the close-out script passes the same options. |
</domain>

<decisions>
## Behaviour decisions (from the ROADMAP criteria; the owner may overrule any before execution)

### D-01 Owner lock: one owner per job record (criterion 1)

Anchors in `src/mindrian_eureka/opportunity_pairs/jobs.py`:
- `:53-68` the `jobs` table has no owner column.
- `:345-353` `JobManager.__init__` resubmits every `queued` row it finds, in any process.
- `:135-137` the active count in `create()` counts every `queued` or `running` row, including rows of a dead process.
- `:185-193` `request_cancel` writes `cancel_requested=1` for any caller.
- `:425-446` `status`, `result` and `cancel` check no owner.
- `src/mindrian_eureka/opportunity_pairs/mcp_server.py:171` builds one `JobManager()` per engine process; `:392-406` the three job tools pass straight through.

Decision:
- The store that creates a job is its owner. Each `JobStore` gets an `owner_token` (16 hex characters) and records `owner_pid` and `owner_token` on the row (new columns, added by `ALTER TABLE` when missing).
- The owner holds an OS lock on `data_dir/job-locks/<job_id>.lock` (directory mode `0o700`, file mode `0o600`) for the life of the job: `fcntl.flock(LOCK_EX | LOCK_NB)` on POSIX, `msvcrt.locking(LK_NBLCK, 1)` on Windows. The OS releases the lock when the owner process dies. The owner releases it on the terminal transition.
- `job_id` is checked against `^eureka-[0-9a-f]{32}$` before any lock path is built. No other string reaches `Path` (Windows path safety, see constraints).
- A second opener (any store that does not hold the lock while another holder does) gets the typed refusal `{"job_id": ..., "status": "refused", "reason": "owner_locked", "recorded_status": "<row status>", "changed": false}` from `status`, `result`, `cancel` and `delete`, and nothing is written.
- Lock states: `held` (this store holds it), `locked` (another live process holds it), `free`. A `free` lock on a non-terminal row means the owner is dead; `status` then reports `"owner": {"pid": ..., "token": ..., "lock": "lost"}`; `cancel` and `result` return the refusal reason `owner_lost`; only `recover` (D-02) changes such a row.
- `JobManager.__init__` starts nothing. A queued row of another owner is never resubmitted.
- The active count in `create()` counts only rows whose lock is `held` or `locked`. Orphan rows do not consume the 8 slots.
- `status` gains two keys: `owner` (`pid`, `token`, `lock` in `held`, `locked`, `released`, `lost`) and `cancel_requested` (bool). Existing keys do not move.

### D-02 Read-only status; recovery only on an explicit call (criterion 2)

Anchors in `jobs.py`:
- `:94-95` `_init_db` calls `expire_old()` and `_recover_interrupted()` on every open of the store.
- `:101-108` `_recover_interrupted` updates every `running` row to `failed`, `server_restarted`, and clears `request_json`.
- `:148-154` `get()` deletes an expired row during a read; `status()` (`:425-429`) and `result()` (`:199-205`) call `get()`.
- `:42-47` `_connect` opens read-write for every call.

Decision:
- Opening a store creates the tables and adds missing columns. It expires nothing, recovers nothing, starts nothing.
- `get()` filters an expired row in memory and returns `None`. It deletes nothing. `status` and `result` on an expired or unknown id still raise `KeyError` (unchanged tool error for the plugin).
- Read methods (`get`, `queued`, `events`, `result`, `status`, `review_summary`, `evaluation_report`) use a connection with `PRAGMA query_only=1`. A write on that connection raises.
- `expire_old()` runs in `create()` (a start is a write path) and in `recover()`.
- New `JobStore.recover(job_id=None)` and MCP tool `scout_recover(job_id: str | None = None)`. It marks every orphan (non-terminal row whose lock is `free` and whose owner is not this store): `cancelled` when `cancel_requested=1`, else `failed` with `failure_code="owner_lost"`. It never touches a `held` or `locked` row and never touches a terminal row (it lists them under `skipped` with the reason). It returns `{"recovered": [...], "skipped": [...]}`.
- The failure code `server_restarted` is replaced by `owner_lost`. No test or plugin code reads `server_restarted` (grep of `tests/` and the plugin files: no match).

### D-03 Terminal-state guard (criterion 3)

Anchors in `jobs.py`:
- `:166-183` `transition()` reads the current status at `:171` only to return when the row is missing; it then writes any new status over any current status.
- `:190-191` `request_cancel` returns the bare string `already_terminal`; `cancel()` (`:434-446`) passes it on as `status`.

Decision:
- `transition()` returns a dict. On a terminal row it writes nothing, adds no event, and returns `{"job_id": ..., "status": "refused", "reason": "terminal_state", "recorded_status": "<row status>", "changed": false}`. On success it returns `{"job_id": ..., "status": "<new>", "changed": true}`.
- `request_cancel`, `cancel` and `recover` return the same refusal shape on a terminal row. The string `already_terminal` disappears.
- `TERMINAL` (`jobs.py:20`) stays the same six states. The plugin's `TERMINAL` set (`eureka-capability-jobs.cjs:16`) is identical.
- The refusal shape is one module-level helper `_refusal(job_id, reason, recorded_status)`; D-01 and D-02 reuse it.

### D-04 Cooperative cancel through a persisted flag (criterion 4)

Anchors in `jobs.py`:
- `:67` the column `cancel_requested` exists; nothing reads it.
- `:373` `_execute` calls `clear_cancel(job_id)` at the first step and wipes a persisted request.
- `:380`, `:387`, `:397` the worker's `cancel_check` is `cancel_event.is_set`, a process-local `threading.Event` only.
- `:405-406` the cancelled transition records no stage; `:199-205` `result()` of a cancelled row says only `status`, `progress`, `failure_code`.
- Cancel checks between steps already exist in the engines: `opportunity_discovery.py:29,43,52`, `host_run/execute.py:106,175,197`, `opportunity_pairs/runner.py:265-267`, `encoders.py:103,112,182,191`, `algorithm.py:91,107`, `cache.py:210`.

Decision:
- The persisted flag is authoritative. The worker's `cancel_check` is `cancel_event.is_set() or store.cancel_requested(job_id)` (one indexed read per check). `clear_cancel` is removed.
- `request_cancel(job_id, reason="host_request")` stores `cancel_reason` (new column). `close()` (D-05) stores `host_closed`.
- The worker tracks the last stage name. On `RunCancelled` it writes `cancelled` with `cancel_stage=<last stage>` (new column) and an event `Cancel flag observed after stage <stage>`.
- `result()` of a cancelled row returns `{"job_id", "status": "cancelled", "progress", "failure_code": "cancelled", "cancelled_after_stage", "cancel_reason"}`. The result says so.
- "Within one step" means: the fake engine runs at most one more slice after the flag is set. Real step lengths (a model load, one encoder batch) are unchanged and documented.

### D-05 Child lifetime bound to the job (criterion 5)

Anchors:
- `jobs.py:348` the job runs in a `ThreadPoolExecutor` thread (`thread_name_prefix="eureka-rs"`) of the engine process. No job starts a child process: `subprocess` appears only in `doctor.py:17` and `workflow_handlers.py:10`, both synchronous `subprocess.run` with a timeout, on routes that are not jobs.
- `mcp_server.py:648-650` `main()` returns after `server.run(transport="stdio")` and shuts nothing down. Interpreter exit then joins the pool thread (`concurrent.futures.thread` registers `_python_exit`), so the process lives until the job ends.
- Plugin side: `closeSession` (`eureka-capability-jobs.cjs:241-248`) calls `client.close()`, which makes the Node SDK abort the child (SIGTERM); the Phase 392 test kills the child with SIGKILL and expects eviction within 1 s.

Finding (F6, PROVEN 2026-11-10): with a sleeping fake engine inside the real `eureka-mcp` process, closing stdin did not end the process within 12 s; the row stayed `running` with `cancel_requested=0`. Without a job the process ends 4 s after stdin closes.

Decision (the mapping of criterion 5 onto Eureka; see the contract points for the owner):
- "The job record names the child" is served by D-01: the row names the owner process (`owner_pid`, `owner_token`), which is the engine child the plugin started.
- New `JobManager.close(reason="host_closed")`: sets every cancel event, persists `cancel_requested=1` with `cancel_reason=<reason>`, cancels queued futures and marks them `cancelled` (`progress="cancelled-before-start"`), then `executor.shutdown(wait=True, cancel_futures=True)`. The running worker ends within one step and writes `cancelled`.
- `main()` wraps `server.run()` in `try/finally: manager.close()`. Stdin EOF (the host is gone) ends every job of the process and the process exits within one step.
- SIGTERM and SIGKILL from the plugin end the process at once (no handler is added). The row then stays non-terminal with a dead owner; `status` from any later process shows `lock: lost`; `scout_recover` closes it. This is the plugin's "no resume after a restart" case and needs no engine-side handler.
- Proof: a pytest that starts the real `eureka-mcp` through `uv run --no-sync --offline --locked --no-python-downloads` with a sleeping fake engine injected by `PYTHONPATH=tests/fixtures/sleeping_engine` (a `sitecustomize.py` that replaces `jobs.run_document`; F5 proves the mechanism), starts a job, confirms `running`, closes stdin, and asserts exit within 5 s and a `cancelled` row with `cancel_reason="host_closed"`.

## Supporting decisions

- D-06 Test seams. `tests/job_support.py` holds: the minimal start payload (4 artifacts with `id`, `source_ref`, `text`; plus `encoder`, `model_path`, `top_k`, which `_execute` reads at `jobs.py:391`), `install_sleeping_engine(monkeypatch, slices, slice_seconds, calls)` which replaces `jobs.run_document` and `mindrian_eureka.contracts.validate_result` (the result of the fake is not a schema-valid envelope), `wait_for(manager, job_id, states, timeout)`, `row(store, job_id)`, `store_digest(store)` (sha256 of `jobs.sqlite3` and `jobs.sqlite3-wal`), and `shutdown(manager)`. No production code gets a test-only hook.
- D-07 RED first, for every behaviour. Each RED test fails for the stated reason against the current store, in one commit `test(06-NN): ...`; the GREEN commit `feat(06-NN): ...` follows in the same plan. The stated reason is in the test docstring and in the plan.
- D-08 Stable for the plugin: the `eureka-mcp` script, every existing tool name, the `status` keys that exist today, `KeyError` for an unknown or expired id, the six terminal states, `retention_days: 30`, `MAX_ACTIVE_JOBS = 8`. `scout_recover` is the only new tool; `tests/test_host_run_mcp.py:126-130` checks a subset of names, so the addition passes.
- D-09 No new dependency. `fcntl` and `msvcrt` are standard library; the import is chosen by `sys.platform` so `mypy` sees one branch per platform.
- D-10 Close-out through the real route. A Node script under `tests/plugin_contract/` uses the plugin's own `@modelcontextprotocol/client` (version 2.1.0 at `/home/jsagi/dev/MindrianOS-Plugin/node_modules`, resolved with `require.resolve(name, {paths: [PLUGIN_ROOT]})`), the same `callTool(params, {timeout, maxTotalTimeout})` options as `eureka-tool-contract.cjs:236-239`, and the engine start the plugin uses (`uv run --no-sync --offline --locked --no-python-downloads --project <root> eureka-mcp`, `eureka-engine-requirements.cjs:155-171`, entry `eureka-mcp` at `:64`). A pytest wrapper runs it and skips with a reason when `node` or the plugin checkout is absent. The system Python (mcp 1.25.0) is never used.
- D-11 Docs. `docs/mos-eureka-engine-run-contract.md` gains the new codes and a `###` subsection under existing `##` sections only (`tests/test_host_handoff_docs.py:98-102` pins the exact `#` and `##` headings). A new short `docs/job-store-contract.md` is the note for the plugin session. `docs/integrations/mindrianos.md:109` and `docs/architecture.md:192-194` gain the `scout_recover` line. READMEs: `README.md` (the data dir paragraph near line 303 and the pair discovery row near line 334), `src/README.md:8`; `examples/public-example/README.md` has no job text and is left as is, with that fact recorded.
- D-12 Honest labels and voice. No em dash anywhere; hyphens only. Every number in a plan or doc has a source. Windows behaviour stays UNVERIFIED until a run.
</decisions>

<constraints>
## Constraints

- Offline. No network call anywhere in the store, the tests or the close-out script. The engine starts with `--offline`; the Node script sets `UV_OFFLINE=1`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` in the child environment, as the plugin does (`eureka-capability-run.cjs:72-86`).
- Deterministic. Tests use a fake engine with fixed slices, no real model, no clock-dependent assertion other than bounded timeouts. The store writes no random value except `owner_token` and `job_id`.
- Owner-only permissions on job data. The data directory, `jobs.sqlite3`, the lock directory and every lock file are mode `0o700` or `0o600` on POSIX (existing pattern `jobs.py:33-37,90-93`). On Windows these calls are no-ops and privacy depends on the ACL of the data directory (contract doc, "Known limits and risks"; UNVERIFIED on Windows).
- No host restart resume. A queued or running row of a dead owner is never run again. It is closed by `scout_recover` only.
- Windows path safety (Phase 04.1 rule: arguments as arrays, no string split on a path, `pathlib` joins only). The lock path is built from a validated `job_id` with `Path` operators; no `os.sep` string work; no `file:` URI.
- Lint baselines (PROVEN 2026-11-10 in the locked environment): `ruff check src tests` 1452 errors; `mypy src` 87 errors in 16 files. New and changed files add no finding; `mypy src` stays at 87 or fewer.
- Test command: `cd /home/jsagi/dev/mindrian-eureka && PYTHONPATH=src:tests uv run --no-sync --offline --locked --no-python-downloads --with pytest pytest <files> -q -p no:cacheprovider` (PROVEN: `tests/test_host_run_job.py` gives 17 passed in 15 s).
- Lint command: `uv run --no-sync --offline --locked --no-python-downloads ruff check <files>` and `uv run --no-sync --offline --locked --no-python-downloads mypy src 2>&1 | tail -1`.
- Shared tree. Another executor runs hub plan 02.3.1-09 in this tree. Do not stage or edit `README.md`, `src/README.md`, `examples/public-example/README.md`, `docs/brand/hub-design-decisions.md`, the hub capture script, `build/hub-look` or the `02.3.1` phase directory while that plan is open. Plan 06-06 checks `git status --short` on the three READMEs before it edits them and stops with `NEEDS_HUMAN` when they are dirty. Peer edits under `story/` are never staged. Every commit uses `git add <exact paths>` and `git commit --only <paths>`.
- Commit trailer: `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. No push.
</constraints>

<verified_facts>
## Facts checked on 2026-11-10

| Id | Fact | Status |
|----|------|--------|
| F1 | Locked environment: Python 3.12.12 at `.venv`, `mcp` 2.3.0. `ruff check src tests`: 1452 errors. `mypy src`: 87 errors in 16 files. | PROVEN (run) |
| F2 | `tests/test_host_run_job.py` with the exact test command: 17 passed in 15.23 s. | PROVEN (run) |
| F3 | No test reads `already_terminal`, `server_restarted`, `cancel_requested`, `clear_cancel` or `request_cancel` (grep of `tests/*.py`). The only `JobStore` or `JobManager` users are `scout_cli.py:12`, `mcp_server.py:20`, `host_run/api.py:100-110` (via `manager.store.get` and `manager.start`) and the tests listed in the plans. | PROVEN (grep) |
| F4 | `tests/test_host_run_mcp.py:126-130` checks the tool names as a subset; `tests/test_host_handoff_docs.py:98-102` pins the exact `#` and `##` headings of the contract doc. | PROVEN (read) |
| F5 | A `sitecustomize.py` on `PYTHONPATH` loads under `uv run --no-sync --offline --locked --no-python-downloads python`. | PROVEN (run) |
| F6 | Real `eureka-mcp` with a sleeping fake `run_document` installed by F5, driven by raw JSON-RPC (`initialize`, `notifications/initialized`, `tools/call scout_start` with 4 artifacts holding `id`, `source_ref`, `text`): the start returns `queued`; `scout_status` after 1 s returns `running`, progress `sleeping`; after stdin closes the process does not exit within 12 s; the row stays `running`, `cancel_requested` 0. Without a job the process exits 4 s after stdin closes. | PROVEN (run) |
| F7 | The plugin's Node client is `@modelcontextprotocol/client` 2.1.0 under `/home/jsagi/dev/MindrianOS-Plugin/node_modules`; the plugin calls `client.callTool({name, arguments}, {signal, timeout, maxTotalTimeout})`. | PROVEN (read) |
| F8 | Catalog routes: `opportunity.find_cross_domain_pairs` -> `scout_start`; `opportunity.synthesize_discovery_signals` -> `scout_start_opportunity_signal_scout`; `opportunity.run_pair_screen` -> `scout_start_pair_screen` (not in the plugin's `ASYNC_ROUTES`). | PROVEN (read) |
| F9 | `_execute` looks up `run_document` as a module global of `jobs` at call time, so a replacement of `jobs.run_document` reaches the worker (F6 used this path). | PROVEN (run) |
</verified_facts>

<unverified>
## UNVERIFIED

- Windows: `msvcrt.locking` release on process death, the no-op `chmod`, and the whole lock path. No Windows run exists. Every Windows statement in this phase is UNVERIFIED and labeled.
- Whether `uv run` forks a Python child or replaces itself: `owner_pid` is asserted as a live process id while the job runs, not as `proc.pid` of the `uv` command.
- The length of a real step (a model load, one encoder batch of a large corpus) against the plugin's 10 s wait in `expireSession`. The contract says "within one step"; the real step length is not measured in this phase.
- Whether the plugin session will call `scout_recover` after an eviction. It is offered as a hand-off in the contract note; the plugin does not call it today.
</unverified>

<contract_points>
## Contract points that need the owner (reported, not decided here)

- C1 Criterion 5 says "the job record names the child, and job end ends the child". In Eureka a job starts no child process (F6, `jobs.py:348`). The planner maps the criterion onto the engine process: the row names the owner process, the engine ends its jobs and exits when its host closes, and a kill by the plugin leaves an orphan that `scout_recover` closes. Confirm or amend the mapping.
- C2 A `scout_status` read by a non-owner returns `owner_locked` (the strict reading of criterion 1). The looser reading (reads allowed, writes refused) is one line to change in plan 06-03. Confirm.
- C3 The plugin waits 10 s after `scout_cancel` and then kills the child. A step longer than 10 s leaves a `running` row with a dead owner. The store no longer counts such rows against the 8 slots, and `scout_recover` closes them; the plugin session decides whether to call it after an eviction.
</contract_points>
