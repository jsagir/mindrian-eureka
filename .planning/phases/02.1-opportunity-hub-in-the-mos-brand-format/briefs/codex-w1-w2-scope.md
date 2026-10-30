# W1 and W2 implementation scope

## ANSWER
W1 is a wording cleanup in the captured engine note path, with a regression for lowercase library paths.
W2 is a README quick-start gap: document the existing doctor and run commands, then add a narrow README check.
No implementation or tests were changed or run during this research.

## EVIDENCE
- `.planning/phases/02.1-opportunity-hub-in-the-mos-brand-format/02-VERIFICATION.md:115-116` records the recurring import warning, affected outputs, and proposed plain-language note.
- `src/mindrian_eureka/run/pipeline.py:65-66` defines `_OLD_GATE_PREFIX` and `_SHORT_CODE`; the code matcher misses lowercase `rs_corpus_exclude` because underscores count as word characters.
- `src/mindrian_eureka/run/pipeline.py:310-311` sends common and unusual-engine notes through `_unique`, but wording notes are sourced directly from `wording.engine_notes`.
- `src/mindrian_eureka/run/engines.py:317-325` normalizes captured stderr in `_plain_lines`; `:328-338` captures import stderr; `:470-475` attaches reference notes to the wording outcome; `:482-518` carries notes into the manifest.
- `tests/test_run_engines.py:483-497` already checks captured import-time notes, providing a focused location for the lowercase-path regression.
- `README.md:67-79` quick start covers installation and capability/schema inspection, with no `eureka run` or `eureka doctor` command.
- `docs/offline-install.md:44-46` documents `eureka doctor`, `eureka run <folder> --dry-run`, and `eureka run <folder>`.
- `src/mindrian_eureka/run/command.py:106-118` defines the run folder and `--out` options; `:180-192` defines doctor.
- `tests/test_rs_fidelity_statement.py:31-43` checks another README section; no quick-start coverage was found.

## UNVERIFIED
- Exact pair-document and Markdown note field names were not confirmed end-to-end in the pipeline; the manifest and engine-note path are visible in source.
- The proposed README test shape has not been implemented or executed.

## RISK
- Broad regex stripping could hide unrelated engine warnings. Rewrite only the known import warning at capture time and retain its fallback meaning.
- README examples must use the supported `--out` syntax where output placement is shown.

## NEXT
Implement W1 by translating the exact known import warning in `_plain_lines` to a plain fallback note, and extend `test_import_time_note_is_captured_not_printed` to assert the lowercase module path is absent and fallback meaning remains. Implement W2 with a short quick-start subsection using `uv run eureka doctor`, `uv run eureka run <folder> --dry-run`, and `uv run eureka run <folder> --out <folder>`, plus a focused README quick-start regression test.
