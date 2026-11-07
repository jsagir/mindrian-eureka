---
phase: quick
plan: 261107-wuy
type: execute
wave: 1
depends_on: []
files_modified:
  - src/mindrian_eureka/partner_bundle/launchers.py
  - tests/test_partner_bundle.py
autonomous: true
requirements: [PKG-07]
---

<objective>
Codex adversarial review (2026-11-07) found a high-severity defect in the Windows partner launcher. I confirmed it in the code.

`src/mindrian_eureka/partner_bundle/launchers.py` builds the `uv sync` command as ONE string (line 149: `$Sync = "sync --offline --no-index --find-links $Bundle\wheels --extra modern-encoder --extra hub-gate"`, with a second form near line 153 when the wheels folder is missing) and runs it with `& $Uv $Sync.Split(" ")` (line 177). Splitting on spaces also splits the bundle path. A normal Windows path such as `C:\Users\Jane Doe\eureka-partner-bundle` becomes several arguments, so `uv sync` cannot find the wheels and the partner workflow stops at step 1.

The bash launcher (`SYNC=(uv sync ... --find-links "$BUNDLE/wheels" ...)` near line 65) already uses a quoted array and is not affected. Line 310 splits a constant flag string (no paths) and is not affected.

Fix: build the sync command as a PowerShell argument array and call it with array splatting, so the wheel path stays one argument.
</objective>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Array arguments for the Windows uv sync</name>
  <files>src/mindrian_eureka/partner_bundle/launchers.py, tests/test_partner_bundle.py</files>
  <read_first>
    - src/mindrian_eureka/partner_bundle/launchers.py lines 120 to 200 (the PowerShell template) and the existing launcher tests in tests/test_partner_bundle.py (how they read the generated start.ps1 text)
  </read_first>
  <behavior>
    - The generated start.ps1 has no `.Split(" ")` on the sync command. It defines `$SyncArgs = @("sync", "--offline", "--no-index", "--find-links", "$Bundle\wheels", "--extra", "modern-encoder", "--extra", "hub-gate")` (and the no-wheels form without `--no-index` and `--find-links`) and calls `& $Uv @SyncArgs`.
    - The `step 1` echo line and the `-DryRun` "would run" line still print a readable command by joining the array with spaces: `($SyncArgs -join " ")`. The dry-run output of the current tests keeps the same visible text for a path without spaces.
    - A test reads the generated start.ps1 and asserts: no `Split(" ")` is applied to the sync command; `& $Uv @SyncArgs` is present; the `--find-links` element is its own array element followed by the quoted `"$Bundle\wheels"` element. Another test builds a bundle-like launcher text for a path with spaces and checks the array element is quoted as a whole.
    - The docker launcher line with constant flags (`$Flags = "...".Split(" ")`) is unchanged.
    - pwsh is not installed here, so the PowerShell is not executed. State this plainly in the summary: the fix is checked by text tests only and stays ASSUMED until a Windows machine runs it.
  </behavior>
  <action>
    RED: add the tests (they fail now). GREEN: edit the template. Keep the template valid PowerShell 5.1 syntax (no `??`, no ternary, no `&&`). Run `PYTHONPATH=src:tests /home/jsagi/.local/bin/pytest tests/test_partner_bundle.py tests/test_readme_commands.py -q`, ruff on the touched files, and check the repo ruff baseline 1465 and mypy baseline 88 errors in 17 files do not rise. Also run a bash check of the bash launcher with a bundle folder whose path contains a space: build a host bundle with `scripts/build-partner-bundle --target host --wheels skip --out "<scratch>/dir with space"` under /tmp/claude-1000/-home-jsagi/14832b10-ed3e-4b02-b77a-c3e107ee0136/scratchpad/ and run `bash "<bundle>/start.sh" --dry-run`; report that its printed commands keep the path whole. Do NOT run start.sh without --dry-run and do not install anything.
    Add one line to docs/partner-run-guide.md only if it already lists known Windows launcher limits; otherwise leave the guide alone.
  </action>
  <verify>
    <automated>cd /home/jsagi/dev/mindrian-eureka && PYTHONPATH=src:tests /home/jsagi/.local/bin/pytest tests/test_partner_bundle.py tests/test_readme_commands.py -q</automated>
  </verify>
  <done>start.ps1 passes the uv sync arguments as an array, tests pin it, and the bash launcher is shown to keep a path with a space whole in a dry run.</done>
</task>

</tasks>

<success_criteria>
- `git add <exact paths>` then `git commit --only <exact paths>`; never `git add -A` (unrelated story/ changes, an untracked docs/research/ and an untracked .planning/phases/05-* folder exist). Never push.
- No edit or git in /home/jsagi/dev/MindrianOS-Plugin-release or /home/jsagi/MindrianOS-Plugin. Do not edit src/mindrian_eureka/hsi_reference.py.
- Run the pinning set before you finish: tests/test_hub_assets.py tests/test_partner_bundle.py tests/test_readme_commands.py tests/test_public_example.py tests/test_example_check.py tests/test_release_gate_record.py tests/test_room_seed_docs.py tests/test_host_handoff_docs.py.
</success_criteria>
