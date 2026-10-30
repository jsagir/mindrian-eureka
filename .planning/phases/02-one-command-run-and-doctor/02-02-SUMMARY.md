---
phase: 02-one-command-run-and-doctor
plan: 02
subsystem: clean-corpus-builder
tags: [corpus, csv-mapping, markdown, stable-ids, digests, caps]

requires:
  - phase: 02-one-command-run-and-doctor
    provides: limits.py and run/contracts.py (plan 02-01), test scaffold
provides:
  - run/mapping.py (CsvMapping, MappingConfig, MAPPING_JSON_SCHEMA, load_mapping_file, mapping_from_flags, skeleton_mapping)
  - run/textclean.py (looks_like_html, html_to_text, stdlib only)
  - run/corpus.py (Corpus, InputFile, Dropped, CapHit, build_corpus with manifest_inputs and manifest_corpus)
affects: [02-06]

tech-stack:
  added: []
  patterns:
    - "Limits are module globals imported by name, so tests can monkeypatch them"
    - "Messages carry ids, file names and counts, never record text"
    - "New modules: mypy --strict clean, ruff clean, no numpy import"

key-files:
  created:
    - src/mindrian_eureka/run/mapping.py
    - src/mindrian_eureka/run/textclean.py
    - src/mindrian_eureka/run/corpus.py
    - tests/test_run_mapping.py
    - tests/test_run_corpus.py
  modified: []

key-decisions:
  - "Root-level Markdown files get their stem as id (the reference engine skips them). Documented in the corpus.py module docstring."
  - "A CSV row with every cell empty is skipped with one warning per file. It is not a record."
  - "The unmapped-CSV error guesses the delimiter (comma, semicolon, tab, pipe) and adds it to the skeleton when it is not a comma."
  - "Duplicate-id fix text depends on the source: CSV points to an id column, Markdown points to renaming a file."
  - "Record size is checked on model_text (title + body), after the cap, so it matches what both engines score."

patterns-established:
  - "build_corpus is read-only on the input folder (files opened with rb, tree hash test)."
  - "caps_hit and dropped are always in the manifest dicts and in warnings."

requirements-completed: [RUN-02]

duration: 40min
completed: 2026-10-24
---

# Phase 2 Plan 02: Clean corpus builder Summary

**Markdown and CSV folders become one sorted, normalized, hashed record list with stable ids, listed drops, a reported artifact cap, and a CSV mapping that takes partner headers from a JSON file or flags with no code change.**

## Performance

- **Tasks:** 3 of 3
- **Files:** 5 created, 0 modified
- **Tests:** 118 pass in the two new test files (30 mapping, 88 corpus and textclean). Full suite: 352 passed, 25 skipped (02-01 baseline: 234 passed).

## Accomplishments

- mapping.py: JSON Schema (draft 2020-12, `additionalProperties` false at both levels), file loader (1 MiB cap, BOM safe, errors sorted by JSON path, at most 5 shown), flag route with canonical-JSON hash, `for_file` (exact key, then `*`), skeleton generator that validates against the schema.
- corpus.py Markdown: ids from relative paths, front matter / first heading / file stem title order, heading line removed when it starts the body, CRLF and NFC normalization, hidden and `node_modules` skipped, outside symlinks skipped with a warning, directory symlinks never followed.
- corpus.py CSV: sanitized ids `<file stem>/<value>`, `h<12 hex>` ids without an id column, labels, extra fields, value maps with a capped warning, HTML cleanup (auto, always, never), BOM, any single-character delimiter, quoted line breaks, field size limit raised to MAX_RECORD_CHARS and restored in `finally`.
- Stops: duplicate ids (both sources named), empty or dot-only id, oversize file, record or collection, fewer than 2 usable records (exit 1). Unmapped CSV, missing mapped column, duplicate header (exit 2).
- Reports: short bodies in `dropped`, artifact cap in one `caps_hit` entry with the hash of the cut ids, `corpus_digest`, `folder_digest`, per-file sha256 and `mapping_sha256`.

## Task Commits

1. **Task 1: CSV mapping module** - `e98c016` (feat)
2. **Task 2: corpus builder for Markdown** - `d18ebbb` (feat)
3. **Task 3: CSV reading, HTML cleanup, value maps, skeleton message** - `f630fc0` (feat)

No separate RED commits. New files must be staged before `git commit --only`, and tests and code for one module were committed together (same reason as 02-01).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Skeleton did not guess "Case ID" as the id column**
- **Found during:** Task 1
- **Issue:** The plan example `["Case ID", "Title", "Description"]` has a space. Lowercasing alone gives `case id`, which is not in the guess set.
- **Fix:** Header guesses compare a key where spaces and hyphens become underscores.
- **Files modified:** src/mindrian_eureka/run/mapping.py
- **Commit:** `e98c016`

**2. [Rule 1 - Bug] Block tags gave blank lines between paragraphs**
- **Found during:** Task 3 (design of the cleaner)
- **Issue:** The plan expects `<p>Fish &amp; chips</p><p>Pie</p>` to give two lines. A newline at every start and end tag would give a blank line between them.
- **Fix:** The cleaner adds a line break only when the output does not already end with one.
- **Files modified:** src/mindrian_eureka/run/textclean.py
- **Commit:** `f630fc0`

**3. [Rule 2 - Missing critical] Blank CSV rows**
- **Issue:** A row with all cells empty would raise the empty-id error, or collide on the hash id of empty text.
- **Fix:** Such rows are skipped with a warning that gives the count.
- **Files modified:** src/mindrian_eureka/run/corpus.py
- **Commit:** `f630fc0`

**4. Test interpretation: mapping file route vs flags route**
- The conftest mapping file also sets `value_maps` and `extra_fields`. The flags cannot carry them, so the two routes cannot give equal records for that file. The equality test writes its own mapping file with only id, title and text columns. A separate test covers the conftest mapping file (value map decode).

Total deviations: 4, none changes scope.

## Known Stubs

None. No NotImplementedError remains (`grep -c NotImplementedError` prints 0).

## Threat Model Coverage

T-02-11 (symlinks) test: outside file link and folder link skipped with warnings. T-02-12 (ids) sanitizer, dot-only refusal and duplicate stop tested. T-02-13 (size) file, record, collection and csv cell limits tested with monkeypatched limits. T-02-14 (message leaks) tests assert a distinctive sentence never appears in error text. T-02-15 (read-only) tree hash before and after, Markdown and CSV. T-02-16 (silent drops) `dropped` and `caps_hit` in the manifest dicts and in warnings. T-02-17 (mapping file) schema with no extra keys; file sha256 recorded.

## Threat Flags

None.

## Issues Encountered

- A CSV id made only of non-ASCII letters (for example Hebrew) sanitizes to underscores, so two such ids collide and the run stops with the duplicate-id message. This follows the plan sanitizer rule. A partner file with non-ASCII ids needs a different id column, or a hash id by leaving the id column out. Noted for plan 02-06 help text.

## Next Phase Readiness

- Plan 02-06 imports `build_corpus`, `load_mapping_file`, `mapping_from_flags` and uses `Corpus.manifest_inputs()` and `Corpus.manifest_corpus()`.
- `UsageError` from an unmapped CSV carries the headers and a JSON skeleton in `message`. The CLI should print `message`, then `fix`.
- `Corpus.warnings` is a tuple of plain strings for the run summary.

## Self-Check: PASSED

- Files exist: mapping.py, textclean.py, corpus.py, test_run_mapping.py, test_run_corpus.py (all under their paths above).
- Commits found: e98c016, d18ebbb, f630fc0.
- Plan verify command passes: pytest 118 passed; ruff clean; mypy --strict clean on the three new modules and on both test files.
- No story/ file, STATE.md, ROADMAP.md, pyproject.toml or uv.lock touched.
