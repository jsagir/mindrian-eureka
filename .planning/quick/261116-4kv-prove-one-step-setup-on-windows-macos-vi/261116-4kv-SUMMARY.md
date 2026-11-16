---
phase: quick
plan: 261116-4kv
status: complete
subsystem: release, ci, docs
tags: [setup, ci, windows, macos, license, release-record]
requirements: [REL-01]
requires: [7bb6020, 748f7cf, 6fdd6d8]
provides:
  - .github/workflows/setup-smoke.yml (3-OS smoke test of the one-step setup)
  - docs/rs-release-gate.md section 10 (public repository ruling, no gap closes)
  - accurate license sentences in README.md and docs/licensing-and-provenance.md
affects: [README.md, docs/rs-release-gate.md, docs/licensing-and-provenance.md]
tech-stack:
  added: [GitHub Actions workflow setup-smoke]
  patterns: [last-line gate on EUREKA_SETUP: OK, MINDRIAN_EUREKA_ROOT on the checkout]
key-files:
  created: [.github/workflows/setup-smoke.yml]
  modified: [docs/rs-release-gate.md, docs/licensing-and-provenance.md, README.md]
decisions:
  - "The README status line keeps the words internal only, no-go and rs-release-gate.md while the record is draft (test_status_follows_the_release_record)."
  - "The release record front matter is unchanged; section 10 records the public step and closes no gap."
  - "pyproject.toml is not changed; test_pyproject_metadata pins the absence of a license field (owner decision)."
metrics:
  completed: 2026-11-16
  duration: about 20 min
  tasks: 3
  files: 4
---

# Quick 261116-4kv: Prove one-step setup on Windows, macOS and Linux Summary

A GitHub Actions matrix now runs the one-step setup script on 3 operating systems and gates each job on exit 0 and a last line that starts with `EUREKA_SETUP: OK`; the README, the licensing note and the release record now state the public Apache-2.0 repository and keep the open gaps.

STATUS: DONE

CHANGED:
- 530e01d ci(261116-4kv): smoke-test the one-step setup on Linux, macOS and Windows (.github/workflows/setup-smoke.yml)
- 3f5f07c docs(261116-4kv): record the 2026-11-16 public repository ruling; no gap closes (docs/rs-release-gate.md, docs/licensing-and-provenance.md)
- a5f1d88 docs(261116-4kv): README states the public Apache-2.0 repository and the open release gaps (README.md)

VERIFIED (PROVEN):
- The workflow verify command of Task 1 printed `workflow ok`.
- The Task 2 verify chain passed: `tests/test_release_gate_record.py` 13 passed; `git diff --numstat 6fdd6d8 -- docs/rs-release-gate.md` = `6 0` (0 deleted lines, front matter byte-identical); the section 10 heading occurs 1 time; the licensing note has no "intentionally has no top-level" text.
- `git grep 'no blanket license' README.md` finds nothing.
- `uv run --no-sync --offline --with pytest pytest <11 README test files> tests/test_release_gate_record.py -q` = 154 passed, 1 skipped.
- `tests/test_reproduction_guide.py::test_status_follows_the_release_record` and `tests/test_rs_fidelity_statement.py` = 10 passed.
- The added lines of the 3 commits contain 0 long dash characters (U+2013, U+2014).
- `git status --short` is identical before and after the task (story/ and docs/research/ entries untouched).
- `git log origin/main..HEAD` shows only the 3 new commits. Nothing is pushed.

UNVERIFIED:
- The CI run on ubuntu-latest, macos-latest and windows-latest. It runs only after the main session pushes.
- The pwsh gate step (`setup-windows`). This machine has no pwsh.

RISKS: see the section "Risks to carry" below.

NEXT: The main session pushes main, watches the `setup-smoke` run on 3 OSes, and opens a follow-up quick task for any Windows or macOS failure.

## Backfill: ad-hoc commits on main on 2026-11-16 (outside GSD)

Each subject and file list was confirmed with `git show --stat <id>` (PROVEN).

| Commit | Time (+0200) | Subject | Files |
|--------|--------------|---------|-------|
| 7bb6020 | 03:05:07 | chore: add Apache-2.0 license before the repo goes public | LICENSE |
| 748f7cf | 03:13:07 | feat: one-step Eureka setup for MindrianOS (skill + setup scripts) | skills/mindrian-eureka-setup/SKILL.md, scripts/setup-mindrianos.sh, scripts/setup-mindrianos.ps1, README.md (setup section) |
| 6fdd6d8 | 03:13:57 | feat: make the repo a Claude Code plugin marketplace for the Eureka setup skill | .claude-plugin/plugin.json, .claude-plugin/marketplace.json, README.md (install section) |
| 2405015 | 03:21:39 | feat: eureka-opportunity-room skill - one step from a technology list to a worked MindrianOS room | skills/eureka-opportunity-room/SKILL.md |

Commit 2405015 was HEAD when this task started, not 6fdd6d8 as the plan states. It changes only `skills/eureka-opportunity-room/SKILL.md`. So the diff checks against 6fdd6d8 in the plan stay valid for README.md and docs/. The workflow path filter does not include `skills/eureka-opportunity-room/**`; that skill is not a setup script.

Earlier test results, reported by the main session; not rerun in this task:
- The Linux setup ran end to end in a clean HOME (doctor 7 pass, 0 fail; plugin check graph and pairs ready).
- The marketplace install ran in a clean CLAUDE_CONFIG_DIR.

## Local gate results

The `run` text of the step `setup-unix` was read from the workflow with PyYAML. The script path was replaced by a stub path. Each gate ran with `bash -eo pipefail` from the scratchpad directory.

| Stub | Stub exit | Last line | Gate exit | Gate output |
|------|-----------|-----------|-----------|-------------|
| stub-ok.sh | 0 | `EUREKA_SETUP: OK engine-only /x` | 0 | no annotation |
| stub-fail.sh | 1 | `EUREKA_SETUP: FAIL model download failed` | 1 | `::error::setup script exited with code 1` |
| stub-plugin.sh (extra) | 0 | `EUREKA_SETUP: OK plugin /y` | 0 | `::notice::` (not engine-only) |
| stub-badlast.sh (extra) | 0 | `trailing junk` | 1 | `::error::last line does not start with EUREKA_SETUP: OK` |

The pwsh gate (`setup-windows`) is UNVERIFIED. This machine has no pwsh.

## Scope sentence check

`git ls-files | grep -i -E 'opportunity_pairs|pair.scout'` returned `src/mindrian_eureka/opportunity_pairs/*.py` files. So the sentence "The public repository contains the unusual-pairs engine source" in section 10 is PROVEN and stays in the record.

## Deviations from Plan

**1. [Rule 3 - Blocking] Test command form**
- Found during: Task 3.
- Issue: `uv run --offline pytest` resolves to `/home/jsagi/.local/bin/pytest`, outside the project venv. The project venv has no pytest. 6 test files then failed collection with `ModuleNotFoundError: mindrian_eureka`. The record test passed in Task 2 because it does not import the package.
- Fix: run `uv run --no-sync --offline --with pytest pytest ... -p no:cacheprovider`, the form used by earlier quick summaries. The venv was not changed (its newest entry is dated 2026-11-08).
- Files modified: none.

**2. [Pre-existing, out of scope] tests/test_public_example.py::test_readme_structure_and_wording fails**
- The plan verify glob `grep -l 'README' tests/test_*.py` includes this file. It reads `examples/public-example/README.md`, not the root README.
- The test expects heading `## Where it was checked` at index 5. The file has `## Open it as one page` and an extra `## Notes for the maintainer`.
- PROVEN pre-existing: `git diff --quiet 6fdd6d8 -- examples/public-example/README.md tests/test_public_example.py` succeeds, so this task did not change either file. The last change to the example README is commit 5425604 (02.3.1-09).
- Not fixed. Logged here as a deferred issue.

**3. Orchestrator-approved planner additions:** README lines 407 and 444 and `docs/licensing-and-provenance.md` line 3 were corrected, because commit 7bb6020 made "no license file" false. These were in the plan; the orchestrator locked them.

## Deferred Issues

- `tests/test_public_example.py::test_readme_structure_and_wording` fails on `examples/public-example/README.md` headings (pre-existing since 5425604 or earlier). A follow-up quick task must reconcile the README headings and the test.

## Risks to carry

- The macOS and Windows runs are not proven until CI runs.
- A Hugging Face rate limit or a large torch download can make a job slow or flaky. The job timeout is 30 min.
- The release record front matter (decision no-go, status draft) conflicts with the public repository. Only the owner can reconcile it.
- pyproject.toml has no license field, and `tests/test_rs_fidelity_statement.py::test_pyproject_metadata` pins that absence. That is an owner decision.
- `actions/checkout@v6`, `actions/setup-node@v6` and `actions/upload-artifact@v6` are pinned by major tag, not by commit sha.

## Threat Flags

None. The workflow has `permissions: contents: read`, no secrets and no `pull_request_target` trigger (T-4kv-01 mitigated). T-4kv-05 and T-4kv-06 are mitigated as the plan states.

## Self-Check: PASSED

- FOUND: .github/workflows/setup-smoke.yml
- FOUND: commits 530e01d, 3f5f07c, a5f1d88 in `git log`
- FOUND: backfill commits 7bb6020, 748f7cf, 6fdd6d8, 2405015
