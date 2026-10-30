# Phase 2: One-Command Run and Doctor - Context

**Gathered:** 2026-10-24
**Status:** Ready for planning
**Source:** Phase 1 results + owner request to apply fullstack-dev skills (python-pro, cli-developer, mcp-developer, ml-pipeline)

<domain>
## Phase Boundary

A non-author checks setup with `eureka doctor`, runs `eureka run <folder>` on CSV or Markdown sources, and gets ranked pairs from both engines plus a manifest, identical on every repeat run. Requirements: RUN-01..05, DOC-01, DOC-02.

Engines are called by real name in prose and help text:
- "Find Unusual Pairs Across a Research Collection" (capability opportunity.find_cross_domain_pairs, canonical repo path eureka-pair-scout, hybrid_2026)
- "Rank Unusual Pairs by Wording and Meaning" (capability portfolio.find_hybrid_similarity_pairs)
Never bare "RS" or "HSI" in user-facing text.

Out of scope here: the hub page (Phase 2.1), MindrianOS wiring (Phase 3), public example (Phase 4).
</domain>

<decisions>
## Implementation Decisions (locked)

### Engine calls (from Phase 1)
- Unusual-pairs engine path = repo `eureka-pair-scout` (docs/rs-engine-parity.md section 3). Plugin script and r-and-d script are not called.
- Wording-and-meaning engine settings = the recorded rebuild: tier 1, top-k 200, on a scratch copy (docs/hsi-rs-jhtv-reproduction.md).
- Lift the top_k cap from 100 to 200 and the artifact cap from 2500 so a 2,117+ record collection is not silently truncated. Truncation must be reported in output and manifest, never silent. Update test_clip_and_cap_decisions_are_documented.
- Record engine version and the stable tie-break rule (stable descending top-7 term sort) in the manifest.

### Run behavior
- `eureka run` builds a clean corpus first with stable record IDs (what prepare_engine_corpus.py does for the JHTV run), then calls both engines.
- Run manifest fields: input file hashes, record counts, settings, seeds, library and model versions, output file hashes, caps hit.
- Two runs on the same input give byte-identical ranked output; a test proves it (RUN-04).
- Every output file carries "candidate, not verified" and a score-meaning note (RUN-05).
- Works on a scratch copy of the input; never writes into the source folder.

### Doctor behavior
- Checks Python version, uv, local model presence, cache dir and data dir permissions (owner-only). Each failure prints the exact fix command. A missing model is a clear message and a non-zero exit, never a silent skip (DOC-01, DOC-02).
- Offline: doctor and run make no network calls. No model downloads.

### Skill-derived constraints
- python-pro: full type hints, `mypy --strict` clean on new modules, ruff clean, dataclasses for manifest and settings, pathlib not os.path, `X | None`, no bare except, no mutable defaults, Google-style docstrings, pytest with fixtures and parametrize.
- cli-developer: `--help` and `--version` work; diagnostics and progress go to stderr, results to stdout or files; no color when not a TTY; non-interactive by default (enclave and CI safe); clean Ctrl+C exit; distinct exit codes (0 ok, 1 failure, 2 usage); consistent flag names; do not rename existing `eureka` subcommands; shell completion if the CLI framework in use supports it cheaply. Skip the 50ms startup target (model load cannot meet it) and say so.
- ml-pipeline (reproducibility parts only): pin and record seeds and library versions; validate input schema before ranking and stop with a clear message on bad input; hash inputs and outputs. No MLflow, Kubeflow or Feast.
- mcp-developer: if the run is exposed through the MCP server in this phase, validate inputs with a schema and return structured errors; wiring /mos:eureka is Phase 3.
- Install target: Oliver's secure-enclave machine, local, shared-screen guidance, no data leaves. Docker path must not regress (Dockerfile, scripts/run-mcp-container).

### Claude's Discretion
- Module layout under src/mindrian_eureka, CLI framework already used in cli.py, input column mapping for CSV (headers not yet received from the partner; make mapping configurable by flags or a small mapping file), fixture design.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` - scope and success criteria
- `docs/hsi-rs-jhtv-reproduction.md` - exact commands, hashes and caps for the JHTV rebuild
- `docs/rs-engine-parity.md` - canonical path decision and parity numbers
- `docs/rs-release-gate.md` - release gaps (do not claim fidelity beyond README fidelity section)
- `docs/engines/opportunity-pairs.md`, `README.md` (engine names table, fidelity section)
- `src/mindrian_eureka/cli.py`, `src/mindrian_eureka/opportunity_pairs/{algorithm,runner,cli,mcp_server}.py`, `src/mindrian_eureka/hsi_engine.py`
- `capabilities/opportunity.find_cross_domain_pairs/manifest.json`, `capabilities/` catalog
- `tests/` (test_rs_engine_parity*.py, test_release_gate_record.py), `tests/fixtures/rs_parity/`
- `.planning/phases/01-release-gate-and-engine-parity/01-CONTEXT.md` and SUMMARYs
- `CONTRIBUTING.md` (no private room exports, no personal names), `SECURITY.md`
</canonical_refs>

<specifics>
## Specific Ideas

- Meeting signal (market-signals record): partner will send CSV headers and coded state values; install must run inside a secure enclave; shared-screen session 2026-10-27. Design the CSV mapping so those headers can be dropped in without code changes.
- Candidate-not-verified wording must also appear in the CLI summary printed at the end of a run.
</specifics>

<deferred>
## Deferred Ideas

- Hub page (Phase 2.1), MCP /mos:eureka wiring and graph-derive replay rebuild (Phase 3), public example and reproduction guide (Phase 4), password gate (HUB-04).
- Domain-aware filtering, near-duplicate handling (v2).
</deferred>

---
*Phase: 02-one-command-run-and-doctor*
*Context gathered: 2026-10-24*
