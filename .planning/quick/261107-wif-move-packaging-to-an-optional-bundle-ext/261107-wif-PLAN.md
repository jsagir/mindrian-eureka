---
phase: quick
plan: 261107-wif
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - uv.lock
  - src/mindrian_eureka/partner_bundle/builder.py
  - tests/test_partner_bundle.py
autonomous: true
requirements: [PKG-07]
---

<objective>
Quick task 261107-w6v added `packaging>=26.3` to the core `[project] dependencies`. The full suite then failed one test, `tests/test_hub_assets.py::test_package_data_covers_assets_and_optional_gate`, which pins the core dependency list to exactly `jsonschema>=4.20,<5`, `numpy>=2.0,<3`, `scikit-learn>=1.6,<2`. The core install must stay small. Only the owner-run bundle builder (`src/mindrian_eureka/partner_bundle/builder.py`, function using `packaging.markers.Marker`, around line 487) needs `packaging`.

Fix: remove `packaging` from the core dependencies and add it to a new optional extra `bundle = ["packaging>=26.3"]` in `[project.optional-dependencies]` (keep the bound that is already locked). Do NOT change the pin test.
</objective>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: bundle extra, lock, error text</name>
  <files>pyproject.toml, uv.lock, src/mindrian_eureka/partner_bundle/builder.py, tests/test_partner_bundle.py</files>
  <read_first>
    - pyproject.toml (dependencies and optional-dependencies)
    - src/mindrian_eureka/partner_bundle/builder.py around line 480 to 495 (the BundleError text for a missing `packaging`)
    - tests/test_hub_assets.py lines 112 to 130 (the pin test; do not edit it)
    - tests/test_partner_bundle.py
  </read_first>
  <action>
    1. Edit pyproject.toml: delete `packaging>=26.3` from `dependencies`; add `bundle = ["packaging>=26.3"]` to `[project.optional-dependencies]`.
    2. Run `uv lock --offline`; if it cannot resolve offline, run `uv lock` once and report it. Show `git diff --stat uv.lock` and the changed lines; the diff must only move the `packaging` edge from the root dependencies to the `bundle` extra.
    3. Update the BundleError fix text in builder.py so it says to run the builder with `uv run --offline --extra bundle scripts/build-partner-bundle ...` (check how scripts/build-partner-bundle starts Python first; if it already runs through `uv run`, make the fix text match its real invocation). Add a test (no network) that the fix text names the `bundle` extra.
    4. Check `docs/partner-run-guide.md` for a build command; if it names the builder command, add `--extra bundle` where `uv run` is used. Check `scripts/build-partner-bundle` itself: if it calls `uv run` without the extra, add `--extra bundle` so the documented command keeps working with --offline.
    5. Prove: `uv lock --check` exits 0; `PYTHONPATH=src:tests /home/jsagi/.local/bin/pytest tests/test_hub_assets.py tests/test_partner_bundle.py tests/test_readme_commands.py -q` passes; `uv run --no-sync --offline --locked --no-python-downloads eureka --version` prints `eureka 0.1.0`; a dry run `scripts/build-partner-bundle --target host --out <scratch dir under /tmp/claude-1000/-home-jsagi/14832b10-ed3e-4b02-b77a-c3e107ee0136/scratchpad/> ` still works offline (report its exit code); ruff baseline 1465 and mypy baseline 88 errors in 17 files do not rise.
  </action>
  <verify>
    <automated>cd /home/jsagi/dev/mindrian-eureka && uv lock --check && PYTHONPATH=src:tests /home/jsagi/.local/bin/pytest tests/test_hub_assets.py tests/test_partner_bundle.py -q</automated>
  </verify>
  <done>The core dependency list is back to three entries, `packaging` sits in the `bundle` extra, the lock passes --check, and the builder still runs.</done>
</task>

</tasks>

<success_criteria>
- One commit for pyproject.toml and uv.lock together; other files in a second commit. `git add <exact paths>` then `git commit --only <exact paths>`; never `git add -A` (unrelated story/ changes and an untracked docs/research/ exist). Never push.
- No git or edit in /home/jsagi/dev/MindrianOS-Plugin-release or /home/jsagi/MindrianOS-Plugin. Do not edit src/mindrian_eureka/hsi_reference.py.
</success_criteria>
