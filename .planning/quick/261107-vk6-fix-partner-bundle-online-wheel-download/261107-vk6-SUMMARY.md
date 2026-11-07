---
phase: quick
plan: 261107-vk6
subsystem: partner-bundle
tags: [packaging, pip-download, wheels, partner-bundle]
requires: []
provides:
  - "scripts/build-partner-bundle --online builds all three targets (exit 0)"
affects: [docs/partner-run-guide.md]
tech-stack:
  added: []
  patterns:
    - "Marker filtering of a temporary requirements copy with packaging.markers, per target"
key-files:
  created: []
  modified:
    - src/mindrian_eureka/partner_bundle/builder.py
    - tests/test_partner_bundle.py
    - docs/partner-run-guide.md
decisions:
  - "Filter the locked list by target markers in a temporary copy; requirements.txt in the bundle stays the unchanged uv export."
  - "Download with --no-deps because the lock is the full closure."
requirements-completed: [PKG-07]
duration: 40 min
completed: 2026-11-07
---

# Quick 261107-vk6: Partner bundle online wheel download fix Summary

`scripts/build-partner-bundle --online` now builds linux-x86_64, windows-x86_64 and macos-arm64 with exit 0, using the PyTorch CPU extra index, macOS arm64 tags 11 to 14, and per-target marker filtering of the locked list.

## Commits

- 5357443: extra index constant `PYTORCH_CPU_INDEX`; `MACOS_ARM64_PIP_PLATFORMS`; function `_pip_download_base`; tests.
- 4f79e3f: function `filter_requirements_for_target`; `--no-deps`; tests.
- 05f8bbd: drop the true marker from kept entries; tests.
- 522f62b: guide records the builds as PROVEN.

## Root causes (4)

1. PROVEN: linux and windows. The lock pins `torch==2.14.1+cpu` from the `pytorch-cpu` index. The builder asked PyPI only. Fix: `--extra-index-url` from one constant.
2. PROVEN: macOS. The builder passed only `macosx_11_0_arm64`; scikit-learn 1.9.1 ships `macosx_12_0_arm64`. Fix: tags `macosx_11_0` to `macosx_14_0` arm64 (14 is the highest N in uv.lock) plus universal2 tags 10_9, 10_13, 10_15 (found in uv.lock). `macosx_11_0_universal2` is not in the lock, so it is not added.
3. PROVEN: found by the second run. `pip download --platform` selects wheel tags for the target, but pip evaluates environment markers on the builder machine (Linux). macOS got `torch==2.14.1+cpu` (no darwin wheel), and Windows failed on a pulled `cuda-toolkit==13.0.3` dependency. Fix: the builder writes a temporary copy of `requirements.txt` that keeps only entries true for the target, and passes `--no-deps`.
4. PROVEN: found by checking the wheel list after the third run. pip also applies the marker of a kept entry on the builder machine, so `colorama` (Windows) and `torch==2.14.1` (macOS) were skipped silently with exit 0. Fix: kept entries lose their marker in the temporary copy. The check that exposed it compared every locked name and version for the target to the wheel folder.

The shipped `requirements.txt` is unchanged (a test compares its hashes to a fresh `uv export`).

## Build results (final run, Linux builder, `--online`, output in the scratchpad `bundles2` folder)

| Target | Exit | Size (du -sh) | Wheels | Locked entries for target | Missing | Manifest files vs disk |
|--------|------|---------------|--------|---------------------------|---------|------------------------|
| linux-x86_64 | 0 | 459M | 51 | 49 | 0 | 1103 / 1103, 0 differences |
| windows-x86_64 | 0 | 390M | 52 | 50 | 0 | 1104 / 1104, 0 differences |
| macos-arm64 | 0 | 368M | 51 | 49 | 0 | 1103 / 1103, 0 differences |

The 2 wheels over the locked entries come from the build-backend download (`setuptools>=75` and `wheel`); a second `setuptools` version can sit next to a locked one. Key wheels: torch `2.14.1+cpu` (linux, windows), torch `2.14.1` macosx_14_0_arm64, scikit-learn macosx_12_0_arm64, colorama on windows.

## Verification

- `PYTHONPATH=src:tests pytest tests/test_partner_bundle.py tests/test_readme_commands.py tests/test_room_seed_docs.py -q`: 39 passed.
- `ruff check` on the touched files: clean. Repo `ruff check src tests`: 1465 errors (baseline unchanged). `mypy src`: 88 errors in 17 files (baseline unchanged).
- Tests use the argument builder and the filter only. No test uses the network or runs pip.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Marker evaluation on the builder machine (root causes 3 and 4)**
- Found during: Task 2 (first and second re-runs).
- Issue: see root causes 3 and 4. Plan expected two root causes.
- Fix: `filter_requirements_for_target`, `--no-deps`, marker removal; tests added.
- Files: builder.py, tests/test_partner_bundle.py.
- Commits: 4f79e3f, 05f8bbd.

**2. [Rule 3] Existing assertion changed.** `test_targets_and_host_alias` asserted the single tag `macosx_11_0_arm64`; it now asserts the new constant.

TDD note: tests and code were written in one pass per task, not as a separate failing commit. The plan allowed one commit per task.

## Known limits

- `packaging` is imported when the filter runs. It is not a declared dependency of the project; it is present in the dev environment (version 26.3). If missing, the builder raises a `BundleError` with a fix.
- The host-only target `darwin-aarch64` keeps the single tag `macosx_11_0_arm64` (plan said keep other rows unchanged). It gets the marker filter and the extra index.
- UNVERIFIED: launchers on any of the three operating systems; installing from the built wheels; whether the macOS wheel set resolves on macOS 11 (scikit-learn needs macOS 12, torch needs macOS 14 as downloaded).
- RISK: torch `2.14.1` for macOS arm64 downloaded as `macosx_14_0_arm64`, so the macOS bundle needs macOS 14 or newer at install time. The guide does not yet state this.

## Self-Check: PASSED

Commits 5357443, 4f79e3f, 05f8bbd, 522f62b exist on main. Modified files exist. No unrelated file staged.
