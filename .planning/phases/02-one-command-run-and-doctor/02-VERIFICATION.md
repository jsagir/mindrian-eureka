---
phase: 02-one-command-run-and-doctor
verified: 2026-10-24T08:10:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification: false
gaps: []
human_verification:
  - test: "Run `eureka run` on a collection of about 2,117 records (the size of the JHTV corpus) and watch time and memory."
    expected: "The run finishes, caps hit is none, and memory stays near the 1.7 GB estimate in src/mindrian_eureka/limits.py."
    why_human: "Phase 2 lifted the caps for this size, but no test or run here reached it. The verifier machine was saturated (load average 50 on 12 cores) and no 2,117-record input exists in the repo."
  - test: "On the real secure-enclave machine (or a Windows machine), run `eureka doctor`, then `eureka run` on a CSV with the partner headers and a mapping file."
    expected: "Doctor prints a correct fix for each failure on that system. The run finishes offline."
    why_human: "Windows and macOS fix lines (uv install, icacls) were never run. docs/offline-install.md says so. The partner CSV headers have not arrived."
---

# Phase 2: One-Command Run and Doctor Verification Report

**Phase Goal:** A non-author can check their setup, run one command on a folder of their own sources, and get the same ranked pairs every time, with a manifest that proves it.
**Verified:** 2026-10-24
**Status:** human_needed (all 5 success criteria verified in code and by direct runs; 2 items need a human or a real target machine)
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `eureka run` on a folder of CSV or Markdown gives ranked pair files from both engines, on a clean corpus with stable record IDs | VERIFIED | `uv run eureka run in_md --out out1` exit 0: 8 records, 3 unusual pairs, 28 wording-and-meaning pairs. Files: unusual-pairs.json, wording-and-meaning-pairs.json, ranked-pairs.md, corpus/records.jsonl. IDs are file stems (doc00..doc07). CSV run with a mapping file exit 0 and with column flags exit 0. Output of both CSV forms is byte-equal except the mapping hash and run-info.json. Unmapped CSV exits 2 and prints a ready mapping to copy. |
| 2 | Each run writes a manifest with input hashes, record counts, settings, seeds, library and model versions, output hashes | VERIFIED | `manifest.json` read in full: `inputs.files[].sha256`, `folder_digest`, `corpus.records_read/used/dropped/caps_hit`, `settings` (run, unusual_pairs, wording_and_meaning), `seeds` (256 and 42), `environment.libraries` (numpy, torch, sentence-transformers and more), `model.files` (sha256 of every model file, snapshot id), `outputs[]` with sha256, bytes and pair counts. `run-info.json` holds the manifest sha256 and the times. |
| 3 | Two runs on the same input give identical ranked output, and a test in the suite proves it | VERIFIED | Real model: `diff -r out1 out2` differs only in run-info.json (paths and times). A third run with `--threads 1`, system Python 3.12.3, numpy 2.2.6 and a different hash seed gave byte-equal unusual-pairs.json, wording-and-meaning-pairs.json, ranked-pairs.md and records.jsonl. Suite: `tests/test_run_determinism.py::test_two_runs_give_byte_equal_files` and 12 more determinism tests pass (13 passed, 1 skipped when run alone). |
| 4 | Every output file carries the "candidate, not verified" label and a score-meaning note | VERIFIED | Label found in unusual-pairs.json (top and per pair), wording-and-meaning-pairs.json (top and per pair), ranked-pairs.md (3 times), corpus/records.jsonl header, manifest.json, run-info.json. `score_meaning` text in the manifest and per engine in the JSON and Markdown. Last stdout line is the label sentence. Test: `tests/test_run_labels.py`. |
| 5 | `eureka doctor` checks Python, uv, local model, cache and data permissions, prints the exact fix; a missing model is a clear message, never silent | VERIFIED | Real machine: D1 to D7, exit 0 (one WARN for offline variables). With an empty HOME: D4 FAIL with Searched list and a 3 step fix, exit 1, and nothing was created in HOME. `eureka run --model-path <missing>` exit 1 with problem and fix and no output folder. `eureka run` with no model anywhere exit 1 with the same fix. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/mindrian_eureka/run/command.py` | flags, exit codes | VERIFIED | 317 lines, wired from `cli.py` (`register_commands`, `run_command`, `doctor_cli`) |
| `src/mindrian_eureka/run/pipeline.py` | staged pipeline | VERIFIED | calls corpus, both engines, projection, manifest, `StagedRun.publish()` |
| `src/mindrian_eureka/run/corpus.py`, `mapping.py`, `textclean.py` | clean corpus, mapping | VERIFIED | used by pipeline; duplicates, short bodies and caps are reported |
| `src/mindrian_eureka/run/engines.py` | facade for both engines | VERIFIED | unusual pairs through `opportunity_pairs.runner.run_document` (canonical path from Phase 1); wording-and-meaning through `hsi_reference` in the recorded call order, tier 1, top-k 200 |
| `src/mindrian_eureka/run/manifest.py`, `output.py`, `project.py`, `console.py` | manifest, writer, projection | VERIFIED | outputs real data (seen in the files above) |
| `src/mindrian_eureka/doctor.py`, `models.py` | doctor, model discovery | VERIFIED | doctor paths match the real cache path (`opportunity_pairs/cache.py`) and data path (`jobs.py`) |
| `src/mindrian_eureka/limits.py` | caps 200 and 3,000 | VERIFIED | one module, imported by runner and CLI; MCP pydantic schemas keep 2,500 (recorded as Phase 3 item in 02-01 SUMMARY) |
| `docs/offline-install.md` | offline install note | VERIFIED | exists, names `eureka doctor` and `eureka run` steps |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cli.py` | `run/command.py` | `register_commands`, `run_command`, `doctor_cli` | WIRED | `eureka run`, `eureka doctor`, `--version`, old subcommands unchanged (tests) |
| `command.py` | `pipeline.run_pipeline` | lazy import inside function | WIRED | `eureka --help` loads no heavy library (test) |
| `pipeline.py` | `opportunity_pairs.runner` | `engines.run_unusual_pairs` | WIRED | real run produced unusual-pairs.json |
| `pipeline.py` | `hsi_reference` | `engines.run_wording_and_meaning` | WIRED | real run produced wording-and-meaning-pairs.json |
| `pipeline.py` | manifest and files | `StagedRun` write then publish | WIRED | interrupted run leaves no staging folder (checked) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| ranked-pairs.md | pair tables | engine results projected from the real model | Yes (28 and 3 rows of real scores) | FLOWING |
| manifest.json | input and output hashes | file bytes, model files | Yes (matches `sha256sum` of the input set) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite | `PYTHONPATH=src python3 -m pytest tests -q -p no:cacheprovider` | 668 passed, 27 skipped, 45 subtests passed in 55 s | PASS |
| ruff | `uv run ruff check src/mindrian_eureka/run doctor.py models.py limits.py` | All checks passed | PASS |
| mypy | `uv run mypy --strict` on the same 15 files | no issues found | PASS |
| Version and help | `eureka --version`, `eureka run --help`, `eureka doctor --help` | `eureka 0.1.0`; help lists flags and exit codes | PASS |
| Run twice | two real-model runs, `diff -r` | only run-info.json differs | PASS |
| Thread, library and hash-seed independence | `--threads 1`, system Python, other hash seed vs default | ranked files byte-equal | PASS (one input, 8 records) |
| Input never written | sha256 of all input files before and after four runs | identical | PASS |
| No short engine code in help and outputs | grep for `RS`, `HSI` (word match) in help, stdout, stderr, all output files | none | PASS |
| Exit 0 | successful runs, dry run, doctor with no FAIL | 0 | PASS |
| Exit 1 | missing model, explicit missing model | 1 | PASS |
| Exit 2 | no folder argument, `--top-k 0`, missing input folder, empty folder, `--out` inside input, foreign non-empty `--out`, unmapped CSV, bad mapping file | 2 for each | PASS |
| Exit 130 | SIGINT sent after the "Ranking with" stage | 130, stdout empty, no output folder, no staging folder | PASS |
| Caps reported, not silent | `--dry-run --max-artifacts 5` on 8 records | caps_hit record with limit, counts and id hash, warning on stderr | PASS |
| Dry run | `--dry-run` | no model load, nothing written | PASS |
| No network | static: no `socket`, `requests` or `urlopen` in `run/`, `doctor.py`, `models.py`; offline variables set before engine import; `no_network` fixture tests pass in the suite | no call | PASS (no live packet capture was run) |

### Probe Execution

Step 7c skipped: Phase 2 declares no probe scripts, and no `scripts/*/tests/probe-*.sh` exists.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| RUN-01 | 02-06 | one command, folder of CSV or Markdown, ranked pairs from both engines | SATISFIED | truth 1 |
| RUN-02 | 02-02 | clean corpus with stable IDs | SATISFIED | corpus.py, records.jsonl, IDs stable across runs |
| RUN-03 | 02-04 | run manifest | SATISFIED | truth 2 |
| RUN-04 | 02-06 | identical output on repeat, test proves it | SATISFIED | truth 3 |
| RUN-05 | 02-06 | labels and score-meaning notes in every output | SATISFIED | truth 4 |
| DOC-01 | 02-05 | doctor checks and exact fixes | SATISFIED | truth 5 |
| DOC-02 | 02-05 | missing model is a clear message | SATISFIED | truth 5 |

No orphaned requirements: REQUIREMENTS.md maps exactly RUN-01..05, DOC-01, DOC-02 to Phase 2, and all appear in plan frontmatter.

### Anti-Patterns Found

Debt-marker scan (TBD, FIXME, XXX, TODO, HACK, PLACEHOLDER, NotImplemented) over the 29 source, test and doc files changed in Phase 2: no real marker. The only grep hits are the word "JTBDs" in `cli.py` help text (a false match, line 38 and 42, old code). No stubs, no empty handlers, no hardcoded empty data flowing to output.

### Warnings (not blockers)

| # | Severity | Finding | Evidence | Suggested fix |
|---|----------|---------|----------|---------------|
| W1 | WARNING | Every clean run writes an engine note that shows an internal file name: `Wording-and-meaning engine: warning: lib/core/rs_corpus_exclude.py not importable, using the built-in fallback exclude-list`. It reaches wording-and-meaning-pairs.json, ranked-pairs.md and manifest.json. The notes of this engine bypass `_plain_engine_text`, and the code regex `\b(?:RS\|HSI)\b` does not match `rs_corpus_exclude` (the underscore is a word character). The note is also noise: it appears on every checkout because the plugin library is never present. | `out1/manifest.json` line 10; `pipeline.py` lines 65-67 and 310-311 | Drop this one known note, or rewrite it to "The wording-and-meaning engine used its built-in exclude list." Extend the code test to `rs_` and `hsi_` fragments. |
| W2 | WARNING | README.md "Quick start" does not mention `eureka run` or `eureka doctor`. Only docs/offline-install.md and `--help` do. A non-author reading the README will not find the one-command path. | `grep "eureka run" README.md` returns nothing | Add a short run and doctor section (Phase 4 guide may cover it; do it earlier if the 2026-10-27 partner session needs it). |
| W3 | INFO | When a cap cuts the collection, two near-identical warnings print ("The collection has 8 usable records. The cap is 5 ..." and "The limit of 5 records was reached ..."). | dry-run output | Keep one. |
| W4 | INFO | The default suite skips the only real-model hash-seed test (needs `EUREKA_TEST_MODEL_PATH`). All other RUN-04 tests use the hashing stub. This verifier replaced it with manual real-model runs (truth 3). The gated test timed out at 600 s here only because the machine load was about 50. | `tests/test_run_determinism.py` line 222 | None required. Optionally run the gated test in the release checklist. |
| W5 | INFO | SIGTERM (not in the exit-code contract) leaves a hidden `.<out>.staging-<pid>` folder next to `--out`. SIGINT before the pipeline starts (during imports) is not caught by the `run_command` handler. Both were seen only by killing runs by hand. | scratch dir listing after `pkill` | Optional: handle SIGTERM like SIGINT. |
| W6 | INFO | Doctor and missing-model text name the env variables `MINDRIAN_EUREKA_RS_MODEL_PATH` and `MINDRIAN_EUREKA_HSI_MODEL_PATH`. These are existing variable names, so they contain the short codes. Not renaming them is a reasonable choice. | missing-model output | Document the choice or add an alias with a plain name. |
| W7 | INFO | ROADMAP.md Progress table still says "Phase 2: 1/6 In progress" while the plan list shows 6 checked and REQUIREMENTS.md shows all 7 Phase 2 IDs Complete. This verifier must not edit ROADMAP.md. | ROADMAP.md line 104 | The orchestrator updates the row after the phase closes. |
| W8 | INFO | The unusual-pairs engine progress names (`structural-scoring`, `semantic-scoring`, `pair-ranking`) and the engine line `computing spectral OM-HMM profiles` show on stderr. Not engine short codes, but they are stack words. | run1.stderr | Optional rename. |

### Human Verification Required

#### 1. Scale run at the cap lift size

**Test:** Run `eureka run` on a collection of about 2,117 records.
**Expected:** It finishes; caps hit is none; memory near the 1.7 GB estimate (3,000 records ASSUMED near 3.4 GB).
**Why human:** The cap lift (top-k 200, 3,000 records) is a Phase 2 change made for this size. No run at that size exists. The verifier machine was saturated (load average about 50), so a timing or memory result would not be valid.

#### 2. Target machine check

**Test:** On the enclave machine or any Windows machine, run `eureka doctor`, then a CSV run with the partner headers.
**Expected:** Fix lines are correct for that system. The run finishes offline.
**Why human:** Windows `icacls` and uv install lines were never executed. The partner CSV headers are not yet received.

### Gaps Summary

No must-have failed. The five success criteria and the seven requirement IDs are met by working code and by direct runs. Status is `human_needed` only because two items need a real scale input or a real target machine. W1 and W2 are the two worth a quick fix before the 2026-10-27 shared-screen session.

### Environment note

During verification the machine load average was 37 to 60 on 12 cores (another session; 88% system time). A real-model run that took 7 s early on took 7 to 14 minutes later. This is not a defect of the phase, but it shows that default BLAS threads (12) degrade badly under contention; `--threads` exists for that case.

---

_Verified: 2026-10-24_
_Verifier: Claude (gsd-verifier)_
