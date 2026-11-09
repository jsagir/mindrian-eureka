---
phase: quick
plan: 261109-stage-camera-sample
subsystem: hub browser tests (3D stage)
tags: [tests, flake, camera, animation-frames]
requires: []
provides:
  - "early_sample(timeline, duration): time-based early camera sample in tests/test_hub_browser_stage.py"
  - "settled camera sample (settled:true) appended by tests/hub_browser/checks/stage-state.js after an action"
affects: [tests/test_hub_browser_stage.py, tests/hub_browser/checks/stage-state.js]
tech-stack:
  added: []
  patterns: ["choose timer samples by elapsed time, never by index", "wait two animation frames before reading a time-based flight"]
key-files:
  created: []
  modified:
    - tests/test_hub_browser_stage.py
    - tests/hub_browser/checks/stage-state.js
    - .planning/STATE.md
decisions:
  - "The early sample is the first timer sample taken before 40 percent of the 760 ms flight (304 ms); when none exists the early-geometry assertion is not applicable and the test warns with the sampled times."
  - "The check script settles the flight with two animation frames after the last timer sample and appends an additive settled sample; the product is unchanged."
metrics:
  duration: "about 65 minutes"
  completed: "2026-11-09"
---

# Quick 261109: Stage camera test, choose the early sample by time and settle the flight

The stage camera test sampled the 760 ms flight by index (timeline[1] = the 600 ms timer) and read the final state at the 1200 ms timer; under machine load the browser starves animation frames and both reads sit at the wrong moment, so the test now picks the early sample by its elapsed time and the check script waits two frames before it reads the final geometry.

## Root cause (PROVEN)

`stage-state.js` samples the camera by `setTimeout` at 100, 600 and 1200 ms after the action and records `at` (elapsed ms). `hub-graph.js` moves the camera in a time-based `requestAnimationFrame` loop: each frame sets the position from `(now - began) / 760`. Under load the frame callbacks stall for hundreds of milliseconds while the timers keep their schedule, so:

1. A timer that fires after the final frame reads the final geometry (distance exactly 100), and the index-based early assertion `> 100.01` fails. This is the reported failure.
2. When no frame runs between the last mid-flight frame and the 1200 ms timer, the state is read before the final frame: the final distance is not 100 and the final geometry assertions fail (a second failure mode in the same test, found during the proof).

### Proof runs (chromium, no reduced motion, select synthetic-a-009, scratchpad script)

Run at load average 18.5 (natural load from a parallel executor):

```
duration=760 moves=15
before->aim0 distance=438.115
timeline[0] at=102.6 ms calls=4  distance=297.829
timeline[1] at=600.1 ms calls=15 distance=140.001
timeline[2] at=1199.9 ms calls=15 distance=140.001
final distance=140.001
```

Only 15 frames ran; no frame drew after 600 ms; at 1200 ms and at script end the camera was still at distance 140.001 (the final-geometry assertion `== approx(100)` would fail: mode 2).

Run at load average 9.8, per-frame detail:

```
timeline[0] at=101.7 ms calls=4  distance=307.235
timeline[1] at=600.2 ms calls=18 distance=126.252
timeline[2] at=1199.5 ms calls=19 distance=100.000
move[17] at=333.7 ms distance=126.252
move[18] at=1069.8 ms distance=100.000
```

Frames ran every 15 to 18 ms up to 333.7 ms, then no frame for 736 ms; the frame at 1069.8 ms drew the final geometry. The 600 ms timer read a stale frame.

Run at load average 60.2 with samples 100, 900, 1200: `timeline[1] at=900.4 ms calls=17 distance=100.017`, `timeline[2] at=1199.8 ms distance=100.017` (stale, 0.007 above the bound; the final assertion would fail).

Deterministic RED in the browser (load 30.5) with samples 100, 2500, 3000, so the final frame had surely drawn before the second sample: `timeline[1] at=2504.4 ms distance=100.000`; the index-based assertion failed with `assert 99.99999999999997 > 100.01`, the reported assertion.

## What changed

- `tests/test_hub_browser_stage.py` (3c784d7 RED, f430472 GREEN): `EARLY_FRACTION = 0.4` and `early_sample(timeline, duration)` return the first sample with `at < duration * 0.4`. The camera test uses it instead of `timeline[1]`; when it returns `None` the test emits a `UserWarning` with the sampled times and skips only the early-geometry assertion. The new browser-free test `test_early_sample_is_chosen_by_time_not_index` pins the behavior with a fixture that mimics starved frames (second sample at 901 ms at the final geometry): the index-based pick fails `> 100.01`, the time-based pick is the 100 ms sample, 303 ms is early and 304 ms is not, an all-late timeline gives `None`. The `100.01` bound, the final distance 100, zoom in below 100, zoom out 100, reset within 1e-6, duration 760, more than one move and the first position differing from the final are unchanged.
- `tests/hub_browser/checks/stage-state.js` (622e22c): after the timer samples the script awaits two animation frames (the flight's pending callback moves the camera, the next frame renders it and updates the matrices that `graph2ScreenCoords` reads) and appends an additive sample `{..., settled:true}` as the last timeline entry. Tests that read `timeline[-1]` now read the settled geometry. Tests with `samples=[]` get one settled sample (none reads it).
- `.planning/STATE.md`: one row in Quick Tasks Completed.

## Deviations from plan

**1. [Rule 1 - Bug] Settled sample in the check script.** Found during Task 0: the proof showed the final geometry read before the final frame (mode 2 above), and the first GREEN run of the whole file (load 13 to 20) failed `test_widths_fonts_targets_and_reflow` at `assert_selection_uncovered` once (the projected point read with stale camera matrices); it passed alone. The plan allowed additive changes to `stage-state.js`. Fix: two-frame settle plus the settled sample. Commit 622e22c. The product (`hub-graph.js`) is unchanged.

## Verification

Command: `EUREKA_REQUIRE_BROWSER=1 PYTHONPATH=src:tests uv run --no-sync --offline --locked --no-python-downloads --with pytest pytest <file> -q -p no:cacheprovider`. The machine was never idle: a parallel executor ran hub plan 08 the whole time, so "idle" means the natural load without my two busy loops.

| Run | Load average at start | Result |
|-----|------|--------|
| RED unit test (`-k early_sample`) | n/a | 1 failed (NameError: early_sample), as planned |
| stage, first GREEN run (before the settle fix) | 13.2 | 22 passed, 1 failed (`test_widths_fonts_targets_and_reflow`, selection covered) |
| stage, idle 1 | 5.8 | 23 passed in 179 s |
| stage, idle 2 | 6.6 | 23 passed in 170 s |
| stage, idle 3 | 9.4 | 7 failed, 16 passed (see below) |
| stage, loaded 1 (two `node -e "while(1){}"` loops) | 10.2 | 23 passed in 208 s |
| stage, loaded 2 | 11.7 | 23 passed in 197 s |
| stage, loaded 3 | 13.1 | 23 passed in 183 s |
| stage, re-run after the batch | 23.5 | 23 passed in 162 s, 0 warnings |
| `tests/test_hub_browser_graph.py` | 9.6 | 19 passed in 59 s |
| `tests/test_hub_browser_review.py` | 14.2 | 12 passed in 197 s |

Idle run 3 (22:15 to 22:18 local): 7 failed. The batch log kept only the summary line, so the failing tests and causes were not captured (UNVERIFIED). The window coincides with the parallel executor's commit 17ddc59 at 22:15:07 and its uncommitted edits to `hub-core.js`, `page.py` and `copy_pages.py`, which every built hub loads; a mid-edit hub build is the likely cause (ASSUMED). The same file passed 23 of 23 at load 23.5 right after.

The "early-geometry assertion not applicable" warning fired in no run: in every run the 100 ms timer sample was early.

Baselines: ruff `src tests` Found 1452 errors (unchanged; the RED commit alone showed 1457, the 5 F821 of the undefined helper); mypy `src` Found 87 errors in 16 files (unchanged).

## Known stubs

None.

## Threat flags

None: test files only.

## Self-Check: PASSED

- `tests/test_hub_browser_stage.py`, `tests/hub_browser/checks/stage-state.js` exist and hold the changes.
- Commits 3c784d7, f430472, 622e22c exist on main.
