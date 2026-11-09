---
phase: quick
plan: 261109-stage-camera-sample
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/test_hub_browser_stage.py
  - .planning/STATE.md
autonomous: true
requirements: []
---

<objective>
Make `tests/test_hub_browser_stage.py::test_camera_selection_tour_find_zoom_reset` stable under machine load without a retry and without a product change. The test fails at `assert distance(early["position"], early["aim"]) > 100.01` with `early = selected["timeline"][1]`. Prove the cause first: `stage-state.js` samples the camera by `setTimeout` at 100, 600 and 1200 ms after the action and records the elapsed time in the `at` field of each sample. The second sample sits at 600 ms, 79 percent into the 760 ms flight. Under load the timer fires late; a sample at or after 760 ms sits at the final geometry, where the distance is exactly 100. The geometry is right. The index-based choice of the early sample is wrong.
</objective>

<hard_rules>
- Do not change `hub-graph.js`, `stage-state.js` (it already records `at`), `page.py`, `hub-core.js`, `hub-pages.*`, `copy_pages.py`, `figures.py` or the pages tests. Another executor edits those files.
- Do not weaken the final geometry assertions. Do not loosen `100.01`. Do not add a retry.
- Run tests with `EUREKA_REQUIRE_BROWSER=1 PYTHONPATH=src:tests uv run --no-sync --offline --locked --no-python-downloads --with pytest pytest <files> -q -p no:cacheprovider`.
- Baselines: ruff src tests 1452 errors; mypy src 87 errors. Do not raise them.
- `git add <exact paths>` then `git commit --only <exact paths>`. Never `git add -A`. Never push. Never amend.
- STATE.md: one row in the Quick Tasks Completed table only.
- No long dash characters. Trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
</hard_rules>

<tasks>

<task type="auto">
  <name>Task 0: Proof</name>
  <files>none (scratchpad script)</files>
  <action>Run the select step with the camera tracked under artificial load (two `node -e "while(1){}"` loops) and idle. Print each timeline entry: `at`, distance from position to aim. Record the values in the SUMMARY.</action>
  <done>The failing run shows a second sample with `at` at or past 760 ms and a distance of 100. The passing run shows a second sample well before 760 ms and a distance above 100.01.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 1: RED, a time-based early sample helper</name>
  <files>tests/test_hub_browser_stage.py</files>
  <action>Add `test_early_sample_is_chosen_by_time_not_index`, a browser-free test with a fixture timeline that mimics starved frames (`at` values 100, 900, 1200 with the 900 sample at the final geometry). It asserts that `early_sample(timeline, 760)` returns the 100 ms sample, that it returns `None` when every sample is at or past 40 percent of the duration, and that the index-based pick (`timeline[1]`) sits at distance 100 for the starved fixture. The helper does not exist yet, so the test fails.</action>
  <verify><automated>cd /home/jsagi/dev/mindrian-eureka && PYTHONPATH=src:tests uv run --no-sync --offline --locked --no-python-downloads --with pytest pytest tests/test_hub_browser_stage.py -q -p no:cacheprovider -k early_sample</automated></verify>
  <done>The new test fails with a NameError before the helper exists.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: GREEN, choose the early sample by time</name>
  <files>tests/test_hub_browser_stage.py</files>
  <action>Add `EARLY_FRACTION = 0.4` and `early_sample(timeline, duration)`: the first entry whose `at` is below `duration * EARLY_FRACTION`, else `None`. In the camera test replace `early = selected["timeline"][1]` with the helper. When the helper returns `None`, emit a `UserWarning` that names the sampled `at` values and says the early-geometry assertion is not applicable because frames were starved; keep every other assertion (duration 760, more than one move, first position differs from the final, final distance 100, zoom in below 100, zoom out 100, reset within 1e-6).</action>
  <verify><automated>cd /home/jsagi/dev/mindrian-eureka && EUREKA_REQUIRE_BROWSER=1 PYTHONPATH=src:tests uv run --no-sync --offline --locked --no-python-downloads --with pytest pytest tests/test_hub_browser_stage.py -q -p no:cacheprovider</automated></verify>
  <done>The stage file passes 3 runs idle and 3 runs under the artificial load; graph and review files pass; ruff and mypy stay at the baselines.</done>
</task>

</tasks>
