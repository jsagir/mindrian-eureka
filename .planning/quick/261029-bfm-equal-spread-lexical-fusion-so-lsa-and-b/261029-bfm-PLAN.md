---
quick: 261029-bfm
phase: quick-261029-bfm
plan: 01
type: execute
wave: 1
depends_on: []
autonomous: true
requirements: [QUICK-261029-bfm]
files_modified:
  - tests/test_lexical_fusion.py
  - tests/test_run_engines.py
  - src/mindrian_eureka/hsi_reference.py
  - src/mindrian_eureka/hsi_engine.py
  - src/mindrian_eureka/run/engines.py
  - .planning/quick/261029-bfm-equal-spread-lexical-fusion-so-lsa-and-b/261029-bfm-SUMMARY.md
  - .planning/STATE.md
must_haves:
  truths:
    - "The hybrid lexical leg is fuse_lexical_hybrid(lsa, bm25) at all 3 call sites (hsi_engine.py, hsi_reference.main, run/engines.py); no assignment `= 0.5 * (lsa` remains in src/."
    - "On the synthetic asymmetric case (16 docs, seed 2026, spread ratio 1.79x) the fused matrix correlates with each leg within 0.05 and gives each leg a variance share within 0.05; the raw average fails the same assertions (gaps 0.37 and 0.51)."
    - "With equal spread the fused matrix equals the raw average within 0.02 (measured 1.1e-16); constant legs and fewer than 3 pairs return the raw average exactly."
    - "The fused matrix is float64, in [0, 1], symmetric, diagonal exactly 1.0, identical across 2 calls."
    - "lsa and bm25 single-leg modes and the degraded lexical-only-bm25-proxy branch are unchanged and report lexical_fusion 'none'; hybrid reports 'equal_spread_average'."
    - "Provenance carries lexical_fusion in engines.wording_params, in the hsi_reference.main params dict, and in hsi_engine result metadata; RECORDED_PARAMS_HASH is bea4c100c2013300 and equals wording_params_hash(200)."
    - "No file under tests/fixtures/ changed; the frozen hub manifest keeps 7affae3c94c6bed9."
    - "The count of 'candidate, not verified' in src/ stays 4; nothing under story/ is staged; nothing is pushed."
  artifacts:
    - path: "tests/test_lexical_fusion.py"
      provides: "8 tests: asymmetric defect-and-fix, equal spread, zero-spread guard, bounds, run_hsi provenance x3, degraded proxy"
      min_lines: 150
    - path: "src/mindrian_eureka/hsi_reference.py"
      provides: "fuse_lexical_hybrid helper next to zscores; CLI main uses it; params dict carries lexical_fusion"
      contains: "def fuse_lexical_hybrid"
    - path: "src/mindrian_eureka/hsi_engine.py"
      provides: "hybrid mode fuses by equal spread; metadata lexical_fusion"
      contains: "lexical_fusion"
    - path: "src/mindrian_eureka/run/engines.py"
      provides: "facade fuses by equal spread; wording_params lexical_fusion; RECORDED_PARAMS_HASH bea4c100c2013300"
      contains: "bea4c100c2013300"
    - path: "tests/test_run_engines.py"
      provides: "expected_lexical via the helper; new hash and prefixes; lexical_fusion setting asserted"
      contains: "fuse_lexical_hybrid"
  key_links:
    - from: "src/mindrian_eureka/run/engines.py::run_wording_and_meaning"
      to: "hsi_reference.fuse_lexical_hybrid"
      via: "lexical = reference.fuse_lexical_hybrid(lsa, bm25)"
      pattern: "reference\\.fuse_lexical_hybrid\\(lsa, bm25\\)"
    - from: "src/mindrian_eureka/hsi_engine.py::run_hsi"
      to: "hsi_reference.fuse_lexical_hybrid"
      via: "hybrid branch"
      pattern: "reference\\.fuse_lexical_hybrid\\(lsa, bm25\\)"
    - from: "src/mindrian_eureka/hsi_reference.py::main"
      to: "fuse_lexical_hybrid"
      via: "lexical_matrix = fuse_lexical_hybrid(lsa_matrix, bm25_matrix)"
      pattern: "fuse_lexical_hybrid\\(lsa_matrix, bm25_matrix\\)"
    - from: "tests/test_run_engines.py::test_wording_call_order_and_arguments"
      to: "reference.fuse_lexical_hybrid"
      via: "expected_lexical"
      pattern: "reference\\.fuse_lexical_hybrid\\("
---

<objective>
Replace the raw lexical average `0.5 * (lsa + bm25)` in the Eureka hybrid lexical leg with an equal-spread average, so LSA and BM25 each hold half the vote on every corpus.

Defect (PROVEN by the read-only probe /tmp/claude-1000/-home-jsagi/6524eaaa-94db-4c53-a8de-9f6d15b98f81/scratchpad/fusion_probe.py): both legs are cosines in [0, 1], but their spreads differ per corpus. On tests/fixtures/hub_public/input (36 docs, 630 pairs) LSA std is 0.0505 and BM25 std is 0.0242 (ratio 2.09x). The raw average gives the hybrid variance share 51% to LSA and 12% to BM25; the top-10% overlap is 57/63 with LSA and 45/63 with BM25. The leg with the larger spread takes the vote, so the BM25 rare-identifier signal (quick 261029-184, commit 5165aba) is partly drowned on real corpora.

Fix: 1 helper `fuse_lexical_hybrid(lsa_matrix, bm25_matrix)` in hsi_reference.py. It standardises each leg over the pairs (upper triangle, k=1), averages the 2 z-scores, maps back to the pooled mean and pooled spread, clips to [0, 1], keeps symmetry, sets the diagonal to 1.0. Guard: fewer than 3 pairs or a leg spread below 1e-12 returns the raw average unchanged. The 3 call sites use the helper. Provenance records `lexical_fusion`. The recorded params hash moves from 7affae3c94c6bed9 to bea4c100c2013300.

Purpose: an equal vote keeps the hybrid honest about what it measures and lets the BM25 fix reach the ranking.
Output: 1 new test file, 1 edited test file, 3 source edits, 1 summary, 1 STATE.md row, 1 implementation commit, 1 docs commit. No push.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
@/home/jsagi/.claude/protocols/agent-interaction-protocol.md
</execution_context>

<context>
@/home/jsagi/dev/mindrian-eureka/CLAUDE.md
@/home/jsagi/dev/mindrian-eureka/.planning/STATE.md
@/home/jsagi/dev/mindrian-eureka/src/mindrian_eureka/hsi_engine.py (lines 59 to 121)
@/home/jsagi/dev/mindrian-eureka/src/mindrian_eureka/hsi_reference.py (lines 10 to 16, 306 to 336, 1204 to 1209, 1304 to 1331)
@/home/jsagi/dev/mindrian-eureka/src/mindrian_eureka/run/engines.py (lines 45 to 50, 95 to 125, 359 to 396, 411 to 493)
@/home/jsagi/dev/mindrian-eureka/tests/test_run_engines.py (lines 356 to 384 and 386 to 449)
@/tmp/claude-1000/-home-jsagi/6524eaaa-94db-4c53-a8de-9f6d15b98f81/scratchpad/fuse_lexical_hybrid_ref.py (the exact helper to paste; reference implementation)
@/tmp/claude-1000/-home-jsagi/6524eaaa-94db-4c53-a8de-9f6d15b98f81/scratchpad/test_lexical_fusion_ref.py (the exact new test module to copy)
@/tmp/claude-1000/-home-jsagi/6524eaaa-94db-4c53-a8de-9f6d15b98f81/scratchpad/fusion_proto.py and fusion_proto2.py (planner prototypes that measured the numbers below)

Facts the planner measured (PROVEN unless marked):
- Test command: `uv run --offline --with pytest python -m pytest <files> -q`. Plain `uv run pytest` fails with ModuleNotFoundError.
- Targeted baseline, 6 files (tests/test_run_engines.py tests/test_wrong_number_fixes.py tests/test_hsi_latest_integration.py tests/test_hub_public_fixture.py tests/test_rs_engine_parity.py tests/test_bm25_rare_terms.py): 123 passed, 3 skipped, 10.3 s. Parity verdict line: `bm25 max abs delta 2.4e-07, lsa max abs delta 3.4e-08`.
- Full suite baseline `tests/`: 1 failed, 1290 passed, 6 skipped, 45 subtests passed, 475.65 s. The 1 failure is pre-existing and unrelated to this task: `tests/test_hub_assets.py::test_book_source_is_byte_identical[tokens.css-segments/foundations/tokens/entries/2026-10-19/asset-b1c43da20b.css]` (a mos-brand book asset byte check). Do not fix it in this task.
- Ruff baseline `uv run --offline ruff check src tests`: `Found 1467 errors.` (the 74 figure in the task text was 2 files in quick 261029-184). Per file: hsi_engine.py 15, hsi_reference.py 55, run/engines.py 0 (All checks passed), tests/test_run_engines.py 0. The reference test module and the reference helper pass ruff with 0 findings.
- Mypy baseline `uv run --offline mypy src`: `Found 88 errors in 17 files (checked 80 source files)` (the 6 figure in the task text was 1 file in quick 261029-184).
- `grep -rn "candidate, not verified" src/ | wc -l` is 4.
- The 3 fusion sites: hsi_engine.py line 73, hsi_reference.py line 1330, run/engines.py line 462. hsi_reference.py line 503 `sym = 0.5 * (rel + rel.T)` is a different matrix and stays.
- Hash ties: `tests/test_run_engines.py:361` asserts `engines.RECORDED_PARAMS_HASH == "7affae3c94c6bed9"` and line 362 asserts `wording_params_hash(200)` equals the constant; lines 366 and 367 assert the prefixes `5b4b370a` (top_k 20) and `0b2948b9` (top_k 100). `tests/test_run_manifest.py:114` uses the string `7affae3c94c6bed9` in a hand-built sample section for schema validation only; it does not read the live constant and needs no edit. No test compares the frozen manifest `tests/fixtures/hub_public/run/manifest.json` params_hash with the live constant (grep of tests/ for the hash, `RECORDED_PARAMS_HASH`, and `wording_params`). `tests/test_hub_public_fixture.py` verifies file hashes of the frozen run only; `tests/test_hub_bridge_fixture.py` forbids the model and loads the frozen run; neither reruns the engine.
- New fingerprints with the key `lexical_fusion: "equal_spread_average"` added to `wording_params`: top_k 200 `bea4c100c2013300`; top_k 20 `9412dcb52d7b6058`; top_k 100 `9d8cd3b43c7f8e35`. `params_fingerprint` is sha256 of `json.dumps(params, sort_keys=True, default=str)` cut to 16 hex characters, so the key position in the dict does not matter.
- Prototype results, asymmetric case (16 docs, 120 pairs, numpy default_rng seed 2026; leg A std 0.1885, leg B std 0.1052, ratio 1.79x, corr(A, B) 0.024): equal-spread fusion gives pearson(F, A) = pearson(F, B) = 0.7157 (gap 0.0000) and variance shares 0.4881 / 0.4881 (gap 0.0000); the raw average gives pearson 0.8761 / 0.5032 (gap 0.3729) and shares 0.7472 / 0.2325 (gap 0.5147). Fused range [0.1434, 1.0], 0 clipped cells, diagonal 1.0, symmetric, identical across 2 calls.
- Equal-spread case (leg B rescaled to the exact pair spread of leg A, both std 0.150817): max |fused - raw| = 1.1e-16.
- Guard: 2 constant legs, 1 constant leg, and a 2-document input each return the raw average exactly (array_equal). A 3-document input (3 pairs) is fused.
- Real corpora with the helper: rs_parity corpus (32 docs, 496 pairs) share gap 0.0016 (raw 0.0551); hub input (36 docs, 630 pairs) pearson gap 0.0048 (raw 0.0876), share gap 0.0219 (raw 0.3930). Clip at 1.0 saturates 0 pairs on both; the floor at 0.0 catches 60/496 and 45/630 pairs whose pre-clip values are -0.0006 and -0.0040 at the minimum (pairs already at the zero floor). The top-10 fused values are 10 distinct values on both corpora (no new ties).
- The reference test module run against the reference helper: tests 1 to 4 pass; the 4 run_hsi cases fail with `KeyError: 'lexical_fusion'` and nothing else (the degraded path and `lexical_method` assertions already hold).
- `surprise_type` in compute_hsi_matrix derives from `lsa_sim` versus `sem_sim` (hsi_reference.py line 1132), both untouched here; the polarity tests in tests/test_wrong_number_fixes.py do not depend on the fused values. Pair key `lexical_sim` (line 1153) does change value.
- `.planning/quick/` is not ignored (`git check-ignore -v` exit 1). Peer uncommitted edits exist under `story/`.
- The STE protocol applies. Report with STATUS, CHANGED, VERIFIED, UNVERIFIED, RISKS, NEXT.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Write the tests (RED)</name>
  <files>tests/test_lexical_fusion.py, tests/test_run_engines.py</files>
  <read_first>
    - /tmp/claude-1000/-home-jsagi/6524eaaa-94db-4c53-a8de-9f6d15b98f81/scratchpad/test_lexical_fusion_ref.py (copy it unchanged)
    - tests/test_run_engines.py lines 356 to 384 and 386 to 449
  </read_first>
  <behavior>
    - New module `tests/test_lexical_fusion.py`, 8 tests: (1) asymmetric spread: fused pearson gap and variance-share gap each <= 0.05, and the raw average fails both (> 0.05) with the wider leg on top; (2) equal spread: max |fused - raw| < 0.02; (3) constant legs and a 2-document input return the raw average exactly; (4) float64, shape, [0, 1], diagonal 1.0, symmetric, identical across 2 calls, differs from the raw average; (5) parametrized x3: `run_hsi` metadata `lexical_fusion` is `equal_spread_average` for hybrid and `none` for lsa and bm25; (6) degraded proxy (no dense_vectors, no model path): status `completed_degraded_lexical_only`, `lexical_fusion` `none`.
    - `tests/test_run_engines.py`: the recorded hash is `bea4c100c2013300`; the prefixes are `9412dcb5` (top_k 20) and `9d8cd3b4` (top_k 100); `wording_params(200)["lexical_fusion"] == "equal_spread_average"`; `expected_lexical` in `test_wording_call_order_and_arguments` is computed by `reference.fuse_lexical_hybrid` on the recorded matrices.
  </behavior>
  <action>
    Step 1. Copy the reference module unchanged: `cp /tmp/claude-1000/-home-jsagi/6524eaaa-94db-4c53-a8de-9f6d15b98f81/scratchpad/test_lexical_fusion_ref.py /home/jsagi/dev/mindrian-eureka/tests/test_lexical_fusion.py`. The module uses `numpy.random.default_rng(2026)` inside the builders only; it has no module-level RNG state. Its fixture texts and vectors are a copy of the 6 records in tests/test_wrong_number_fixes.py, so no model is needed. Do not edit thresholds: TOLERANCE 0.05, equal-spread bound 0.02, ratio band 1.5 to 2.5.

    Step 2. Edit tests/test_run_engines.py.
    (a) Line 361: change the literal to `"bea4c100c2013300"`. Add 1 comment line above the assertion: `# quick 261029-bfm: the settings dict gained lexical_fusion; the frozen hub manifest keeps 7affae3c94c6bed9.` Keep the line at or under 100 characters; split into 2 comment lines if needed.
    (b) Line 366: `startswith("9412dcb5")`. Line 367: `startswith("9d8cd3b4")`.
    (c) In `test_wording_params_has_the_recorded_settings`, after the `params["lexical"] == "hybrid"` assertion, add `assert params["lexical_fusion"] == "equal_spread_average"`.
    (d) Lines 441 to 443: replace the `expected_lexical = 0.5 * (...)` statement with `expected_lexical = reference.fuse_lexical_hybrid(returned["compute_lsa_similarity"], returned["compute_bm25_similarity"])` split over lines under 100 characters, with 1 comment line above: `# The facade fuses by equal spread (quick 261029-bfm), not by the raw average.` Line 444 `np.allclose(...)` stays.

    Step 3. Run RED. New module: expected 1 error at collection, `ImportError: cannot import name 'fuse_lexical_hybrid'`. Edited module, selection `-k "params_hash or recorded_settings or call_order"`: expected 4 failed (the hash constant, the 2 prefixes, the KeyError on lexical_fusion, the AttributeError on `reference.fuse_lexical_hybrid`) and 0 passed in that selection. Record both RED outputs for the summary. Ruff on the 2 test files: `uv run --offline ruff check tests/test_lexical_fusion.py tests/test_run_engines.py` must print `All checks passed!`. Do not commit yet.
  </action>
  <verify>
    <automated>cd /home/jsagi/dev/mindrian-eureka && uv run --offline --with pytest python -m pytest tests/test_lexical_fusion.py -q 2>&1 | tail -3; uv run --offline --with pytest python -m pytest tests/test_run_engines.py -q -k "params_hash or recorded_settings or call_order" 2>&1 | tail -2; uv run --offline ruff check tests/test_lexical_fusion.py tests/test_run_engines.py</automated>
  </verify>
  <done>tests/test_lexical_fusion.py exists and is byte-identical to the reference module (`cmp` returns 0). Before the fix: the new module errors at collection on the missing import; the selection in test_run_engines.py gives 4 failed. Ruff on both test files: All checks passed.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add the helper, fuse at the 3 sites, record provenance (GREEN)</name>
  <files>src/mindrian_eureka/hsi_reference.py, src/mindrian_eureka/hsi_engine.py, src/mindrian_eureka/run/engines.py</files>
  <read_first>
    - /tmp/claude-1000/-home-jsagi/6524eaaa-94db-4c53-a8de-9f6d15b98f81/scratchpad/fuse_lexical_hybrid_ref.py (lines 11 to 44 are the function to paste; do not paste its module docstring or its import)
    - src/mindrian_eureka/hsi_reference.py lines 10 to 16, 306 to 336, 1204 to 1209, 1304 to 1331
    - src/mindrian_eureka/hsi_engine.py lines 59 to 121
    - src/mindrian_eureka/run/engines.py lines 45 to 50, 95 to 125, 359 to 396, 411 to 493
  </read_first>
  <behavior>
    - `hsi_reference.fuse_lexical_hybrid(lsa_matrix, bm25_matrix)` exists next to `zscores`, is pure numpy float64, no randomness, no seed; semantics and guard as in the reference implementation.
    - All 3 hybrid sites call the helper. `lsa` and `bm25` single-leg modes and the degraded `lexical-only-bm25-proxy` branch keep their current matrices.
    - `engines.wording_params(k)["lexical_fusion"]` is `equal_spread_average`; `engines.RECORDED_PARAMS_HASH == "bea4c100c2013300" == engines.wording_params_hash(200)`.
    - `hsi_reference.main` params dict has `lexical_fusion` (`equal_spread_average` for hybrid, `none` otherwise).
    - `run_hsi` metadata has `lexical_fusion` next to `lexical_method`: `equal_spread_average` for hybrid, `none` for lsa, bm25, and the degraded proxy.
    - Ruff per file does not increase (hsi_engine.py <= 15, hsi_reference.py <= 55, run/engines.py All checks passed). Keep every new line at or under 100 characters.
  </behavior>
  <action>
    hsi_reference.py.
    (1) After `zscores` (its `return (v - float(v.mean())) / sd` is line 333) and before the `# Lexical leg: LSA (kept) and BM25 (new)` banner, paste the function `fuse_lexical_hybrid` from the reference file, unchanged, with 2 blank lines before and after. `np` is already a module-level name in this file (zscores uses it).
    (2) Line 1330: replace `lexical_matrix = 0.5 * (lsa_matrix + bm25_matrix)` with `lexical_matrix = fuse_lexical_hybrid(lsa_matrix, bm25_matrix)`.
    (3) In the `params` dict (line 1304), after `'lexical': args.lexical,` add on its own line `'lexical_fusion': 'equal_spread_average' if args.lexical == 'hybrid' else 'none',`. Reason: the dict feeds `params_fingerprint`, so the fusion rule becomes part of the recorded settings and of the cache key; an old `.hsi-cache.json` then misses and recomputes, which is the intended effect.
    (4) Module docstring line 14: change `mean of LSA (TF-IDF + seeded SVD) and` to `equal-spread mean of LSA (TF-IDF + seeded SVD) and` and keep the rest. Argparse help (line 1207): change `hybrid = mean(LSA, BM25) (default)` to `hybrid = equal-spread mean of LSA and BM25 (default)`.
    Do not edit `compute_lsa_similarity`, `compute_bm25_similarity`, `compute_hsi_matrix`, the result `provenance` block, or any `candidate, not verified` wording.

    hsi_engine.py.
    (5) Replace line 73 with 5 lines: `lexical_fusion = "equal_spread_average" if lexical_mode == "hybrid" else "none"`, then `if lexical_mode == "hybrid":` / `lexical = reference.fuse_lexical_hybrid(lsa, bm25)` / `else:` / `lexical = lsa if lexical_mode == "lsa" else bm25`.
    (6) In the degraded branch (lines 98 to 102), after `lexical = lsa`, add `lexical_fusion = "none"` with 1 comment: no fusion happens in the proxy.
    (7) In the result `metadata` dict, after `"lexical_method": lexical_mode,` add `"lexical_fusion": lexical_fusion,` on its own line (the existing line 115 is already long; do not lengthen it).

    run/engines.py.
    (8) Line 48: set `RECORDED_PARAMS_HASH = "bea4c100c2013300"`. Add 2 comment lines above: `# quick 261029-bfm: the settings dict gained "lexical_fusion", so the fingerprint moved from` / `# 7affae3c94c6bed9. The frozen hub fixture manifest keeps the old value as the record of that run.`
    (9) In `wording_params`, after `"lexical": settings.lexical,` add `"lexical_fusion": "equal_spread_average" if settings.lexical == "hybrid" else "none",`. This mirrors the dict in `hsi_reference.main`, as the docstring of `wording_params` requires.
    (10) Line 462: `lexical = reference.fuse_lexical_hybrid(lsa, bm25)`.
    (11) Docstrings: line 103 `"hybrid" is the mean of two measures.` becomes `"hybrid" is the equal-spread mean of two measures.`; line 421 `the mean of both` becomes `the equal-spread mean of both`.

    Run GREEN: `tests/test_lexical_fusion.py` expected 8 passed; `tests/test_run_engines.py` expected all passed (the module had 0 failures at baseline). Confirm the fingerprint with the one-line command in verify. Confirm no raw assignment remains: `grep -rn "= 0.5 \* (lsa" src/` prints nothing (the helper docstring mentions `0.5 * (lsa + bm25)` without `=`, so this pattern does not count it).
  </action>
  <verify>
    <automated>cd /home/jsagi/dev/mindrian-eureka && uv run --offline --with pytest python -m pytest tests/test_lexical_fusion.py tests/test_run_engines.py -q 2>&1 | tail -2 && uv run --offline python -c "from mindrian_eureka.run import engines; print(engines.wording_params_hash(200), engines.RECORDED_PARAMS_HASH)" && grep -rn "= 0.5 \* (lsa" src/ | wc -l && grep -c "fuse_lexical_hybrid(" src/mindrian_eureka/hsi_reference.py src/mindrian_eureka/hsi_engine.py src/mindrian_eureka/run/engines.py</automated>
  </verify>
  <done>8 passed in the new module; test_run_engines.py all passed. The python one-liner prints `bea4c100c2013300 bea4c100c2013300`. The `= 0.5 \* (lsa` count is 0. `fuse_lexical_hybrid(` appears 2 or more times in hsi_reference.py (def + call) and 1 time each in hsi_engine.py and run/engines.py. `git diff --stat` shows only the 3 source files and the 2 test files.</done>
</task>

<task type="auto">
  <name>Task 3: Guard suites, lint, honest-label and fixture checks</name>
  <files>none (read-only checks)</files>
  <action>
    Step 1, targeted set: `uv run --offline --with pytest python -m pytest tests/test_lexical_fusion.py tests/test_run_engines.py tests/test_wrong_number_fixes.py tests/test_hsi_latest_integration.py tests/test_hub_public_fixture.py tests/test_rs_engine_parity.py tests/test_bm25_rare_terms.py -q`. Expected: 131 passed, 3 skipped (baseline 123 passed, 3 skipped, plus the 8 new tests; ASSUMED arithmetic). The parity verdict line must still print `bm25 max abs delta 2.4e-07, lsa max abs delta 3.4e-08` (the parity test compares the single legs, which this task does not touch). Warning: if any test in tests/test_wrong_number_fixes.py or tests/test_hsi_latest_integration.py fails, stop; do not edit its assertion; report STATUS: BLOCKED with the test name, the assertion, and the printed values.

    Step 2, full suite: `uv run --offline --with pytest python -m pytest tests -q`. Expected: 1298 passed, 6 skipped, 45 subtests passed, and exactly 1 failed, which must be the pre-existing `tests/test_hub_assets.py::test_book_source_is_byte_identical[tokens.css-...]` case (baseline 1 failed, 1290 passed, 6 skipped). Any other failure is a regression. Runtime about 8 minutes. Warning: a failure in any hub test (`tests/test_hub_*.py`) means the frozen fixture was touched or a frozen value leaked into live code; stop and report BLOCKED.

    Step 3, fixtures: `git status --short tests/fixtures/ | wc -l` must print 0. Never regenerate or edit anything under tests/fixtures/.

    Step 4, lint: `uv run --offline ruff check src tests | grep -E "^Found|All checks"` must report 1467 or fewer errors (baseline 1467, pre-existing). Per file: `uv run --offline ruff check src/mindrian_eureka/hsi_engine.py` 15 or fewer; `src/mindrian_eureka/hsi_reference.py` 55 or fewer; `src/mindrian_eureka/run/engines.py`, `tests/test_run_engines.py`, `tests/test_lexical_fusion.py` each `All checks passed!`. `uv run --offline mypy src | tail -1` must report 88 or fewer errors (baseline 88 in 17 files, pre-existing). Do not fix pre-existing lint in this task.

    Step 5, honest label: `grep -rn "candidate, not verified" src/ | wc -l` must print 4 (same as before). `git diff -- src/ | grep -c "candidate, not verified"` must print 0.

    Step 6, story guard: `git diff --cached --name-only | grep -c "^story/"` must print 0 (nothing from story/ is staged). Do not stage, revert, or stash anything under story/.
  </action>
  <verify>
    <automated>cd /home/jsagi/dev/mindrian-eureka && uv run --offline --with pytest python -m pytest tests/test_lexical_fusion.py tests/test_run_engines.py tests/test_wrong_number_fixes.py tests/test_hsi_latest_integration.py tests/test_hub_public_fixture.py tests/test_rs_engine_parity.py tests/test_bm25_rare_terms.py -q 2>&1 | tail -2; git status --short tests/fixtures/ | wc -l; grep -rn "candidate, not verified" src/ | wc -l; uv run --offline ruff check src tests 2>&1 | grep -E "^Found|All checks"; uv run --offline mypy src 2>&1 | tail -1</automated>
  </verify>
  <done>Targeted set 131 passed, 3 skipped. Full suite: 1298 passed, 6 skipped, exactly 1 failed and it is the pre-existing test_hub_assets tokens.css case. tests/fixtures/ status prints 0. Honest-label count 4. Ruff total 1467 or fewer; the 3 clean files stay clean. Mypy 88 or fewer.</done>
</task>

<task type="auto">
  <name>Task 4: Record the summary, update STATE.md, commit by explicit path</name>
  <files>.planning/quick/261029-bfm-equal-spread-lexical-fusion-so-lsa-and-b/261029-bfm-SUMMARY.md, .planning/STATE.md</files>
  <read_first>
    - .planning/quick/261029-184-fix-bm25-vocab-cap-so-rare-identifiers-a/261029-184-SUMMARY.md (format to follow)
    - .planning/STATE.md lines 25 to 35 and 99 to 108
  </read_first>
  <action>
    Step 1, implementation commit, explicit paths only. Warning: peer uncommitted edits exist under `story/`. Never use `git add -A`, `git add .`, or `git commit -a`. Write the message to `/tmp/claude-1000/-home-jsagi/6524eaaa-94db-4c53-a8de-9f6d15b98f81/scratchpad/commit_msg_bfm.txt` with this content. Subject: `fix(quick-261029-bfm): fuse the lexical legs by equal spread so LSA and BM25 each hold half the vote`. Blank line. Body bullets: the raw average 0.5 * (lsa + bm25) gave the vote to the leg with the larger spread (hub corpus: LSA std 0.0505, BM25 std 0.0242, variance share 51% versus 12%); `hsi_reference.fuse_lexical_hybrid` standardises each leg over the pairs, averages the z-scores, maps back to the pooled mean and spread, clips to [0, 1], keeps symmetry, diagonal 1.0; guard returns the raw average for fewer than 3 pairs or a zero-spread leg; the 3 call sites (hsi_engine.py, hsi_reference.main, run/engines.py) use the helper; lsa and bm25 single-leg modes and the degraded proxy are unchanged; provenance key `lexical_fusion` added to wording_params, the CLI params dict, and run_hsi metadata; RECORDED_PARAMS_HASH moved from 7affae3c94c6bed9 to bea4c100c2013300 because the settings dict gained the key `lexical_fusion`; the frozen hub fixture manifest keeps 7affae3c94c6bed9 as the record of that run; no file under tests/fixtures/ changed; tests/test_lexical_fusion.py adds 8 tests. Blank line. Last line exactly: `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
    Then run `git add src/mindrian_eureka/hsi_reference.py src/mindrian_eureka/hsi_engine.py src/mindrian_eureka/run/engines.py tests/test_lexical_fusion.py tests/test_run_engines.py` and `git commit --only src/mindrian_eureka/hsi_reference.py src/mindrian_eureka/hsi_engine.py src/mindrian_eureka/run/engines.py tests/test_lexical_fusion.py tests/test_run_engines.py -F /tmp/claude-1000/-home-jsagi/6524eaaa-94db-4c53-a8de-9f6d15b98f81/scratchpad/commit_msg_bfm.txt`. Record the short sha with `git rev-parse --short HEAD`.

    Step 2, summary: write `261029-bfm-SUMMARY.md` in the quick folder with front matter `quick: 261029-bfm`, `status: complete`, `implementation_commit: <sha>`. Body, 14 lines or fewer, STE style, in this order: the defect with the hub numbers; the rule of the helper and the guard; the 3 call sites; the provenance key and the hash move with its reason; RED counts (collection error on the new module, 4 failed in the selection) and GREEN counts (8 passed, test_run_engines.py all passed); the targeted set count and the parity verdict line; the full suite count; the lint counts against the baselines 1467 and 88; the honest-label count 4 before and after; the statement that no file under tests/fixtures/ changed and nothing was pushed.

    Step 3, STATE.md: change line 31 to `Last activity: 2026-10-29 -- Completed quick task 261029-bfm: Equal-spread lexical fusion so LSA and BM25 each hold half the vote`. Add 1 row after the 261029-184 row of the `Quick Tasks Completed` table: `| 261029-bfm | [Equal-spread lexical fusion so LSA and BM25 each hold half the vote](quick/261029-bfm-equal-spread-lexical-fusion-so-lsa-and-b/261029-bfm-SUMMARY.md), implementation <sha> | complete |`. Edit nothing else in STATE.md.

    Step 4, docs commit: `git add .planning/quick/261029-bfm-equal-spread-lexical-fusion-so-lsa-and-b/261029-bfm-SUMMARY.md .planning/STATE.md` then `git commit --only` those 2 paths with the subject `docs(quick-261029-bfm): record the equal-spread lexical fusion`, a 1-line body naming the implementation sha, and the last line `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. Include the plan file `261029-bfm-PLAN.md` from the same folder in this commit, as quick 261029-184 did (commit 6bbc68b). Do not push.
  </action>
  <verify>
    <automated>cd /home/jsagi/dev/mindrian-eureka && git log --oneline -2 && git show --stat --format= HEAD~1 | tail -8 && git status --short tests/fixtures/ | wc -l && git diff --cached --name-only | grep -c "^story/"; git status --short | grep -c "story/"</automated>
  </verify>
  <done>2 new commits exist with the subjects above. The implementation commit touches exactly 5 files (3 sources, 2 tests). tests/fixtures/ status prints 0. The staged story/ count prints 0, and the story/ working-tree entries are unchanged in count from the start. `git log origin/main..HEAD` lists the new commits; nothing was pushed.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| document text to lexical matrices | untrusted text enters `compute_lsa_similarity` and `compute_bm25_similarity` as today; the helper consumes only the 2 numeric matrices they return and adds no parsing |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-qbfm-01 | Denial of service | `fuse_lexical_hybrid` | accept | elementwise numpy on an n x n matrix, same order as the raw average it replaces; the input size is already capped by MAX_ARTIFACTS |
| T-qbfm-02 | Tampering | `tests/fixtures/hub_public/**`, `tests/fixtures/rs_parity/**` | mitigate | Task 3 Step 3 and Task 4 require `git status --short tests/fixtures/` to print 0 lines; no regeneration is permitted |
| T-qbfm-03 | Repudiation | provenance of the fusion rule | mitigate | `lexical_fusion` recorded in wording_params, the CLI params dict (so in `cache_params_hash`), and run_hsi metadata; the hash move and its reason are in the commit body and in a code comment |
| T-qbfm-04 | Information disclosure | numpy guard on non-finite spread | accept | the guard returns the raw average and exposes no new data; `np.isfinite` check prevents NaN propagation |
| T-qbfm-SC | Tampering | package installs | accept | no package is installed; `--with pytest` uses the offline uv cache only (`--offline` flag) |
</threat_model>

<verification>
- RED recorded: the new module errors at collection on the missing import; 4 failed in the hash/settings/call-order selection of tests/test_run_engines.py.
- GREEN: 8 passed in tests/test_lexical_fusion.py; tests/test_run_engines.py all passed; `wording_params_hash(200)` prints bea4c100c2013300.
- Targeted set: 131 passed, 3 skipped; parity verdict line unchanged.
- Full suite: 1298 passed, 6 skipped, exactly 1 failed (the pre-existing `tests/test_hub_assets.py` tokens.css byte check; not touched by this task).
- No file under tests/fixtures/ changed. The frozen manifest keeps 7affae3c94c6bed9.
- Ruff total 1467 or fewer; engines.py and both test files clean; mypy 88 or fewer.
- `candidate, not verified` count in src/ is 4 before and after; 0 occurrences in the source diff.
- 2 commits, explicit paths, nothing from story/ staged, no push.
</verification>

<success_criteria>
- Every hybrid lexical leg in src/ is `fuse_lexical_hybrid(lsa, bm25)`; each leg holds half the vote regardless of corpus spread, proven by the asymmetric test that the raw average fails.
- Single-leg modes and the degraded proxy are unchanged and report `lexical_fusion: none`.
- Provenance records `lexical_fusion`; RECORDED_PARAMS_HASH is bea4c100c2013300 with the reason recorded.
- The 3 source files and 2 test files are in 1 implementation commit; the summary and STATE.md row are in 1 docs commit. No push.
- The executor report uses STATUS, CHANGED, VERIFIED, UNVERIFIED, RISKS, NEXT.
</success_criteria>

<output>
Create `.planning/quick/261029-bfm-equal-spread-lexical-fusion-so-lsa-and-b/261029-bfm-SUMMARY.md` when done (Task 4, Step 2).
</output>
