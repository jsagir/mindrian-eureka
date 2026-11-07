"""Fresh-checkout tests of the public example.

The helper copies the tracked and new files into an empty folder. A test then runs Eureka from
that folder only, so it proves that nothing from the development tree is needed. The real-model
run is opt-in: set EUREKA_EXAMPLE_REAL_RUN=1.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from mindrian_eureka.example.contracts import OUTPUT_FILES, RESULT_MATCH
from mindrian_eureka.models import discover_model

ROOT = Path(__file__).resolve().parents[1]
INPUT = "tests/fixtures/hub_public/input"
REFERENCE = "examples/public-example/reference-run"
SKIPPED_PREFIXES = ("story/", ".planning/", ".git/")
DEFAULT_TIMEOUT = 120
REAL_RUN_TIMEOUT = 1800
RUNNER = "import sys; from mindrian_eureka.cli import main; sys.exit(main(sys.argv[1:]))"


@pytest.fixture(scope="module")
def checkout(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Copy the tracked files and the new, not ignored files into an empty folder."""
    target = tmp_path_factory.mktemp("fresh") / "checkout"
    listing = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        check=True,
        timeout=DEFAULT_TIMEOUT,
    ).stdout
    for raw in listing.split(b"\0"):
        if not raw:
            continue
        relative = raw.decode("utf-8")
        if relative.startswith(SKIPPED_PREFIXES):
            continue
        source = ROOT / relative
        if not source.is_file():
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    copied = [p for p in target.rglob("*") if p.is_file()]
    assert len(copied) > 500
    assert (target / "examples/public-example/expected-hashes.json").is_file()
    assert (target / INPUT).is_dir()
    assert (target / "src/mindrian_eureka/cli.py").is_file()
    return target


def child_env(checkout: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONPATH"] = str(checkout / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["UV_OFFLINE"] = "1"
    if extra:
        env.update(extra)
    return env


def run_in_checkout(
    checkout: Path,
    *args: str,
    timeout: int = DEFAULT_TIMEOUT,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", RUNNER, *args],
        cwd=checkout,
        env=child_env(checkout, env_extra),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def flip_one_byte(path: Path) -> None:
    data = bytearray(path.read_bytes())
    data[len(data) // 2] ^= 0x01
    path.write_bytes(bytes(data))


def test_checkout_imports_its_own_copy(checkout: Path) -> None:
    done = subprocess.run(
        [sys.executable, "-c", "import mindrian_eureka; print(mindrian_eureka.__file__)"],
        cwd=checkout,
        env=child_env(checkout),
        capture_output=True,
        text=True,
        timeout=DEFAULT_TIMEOUT,
    )
    assert done.returncode == 0, done.stderr
    assert Path(done.stdout.strip()).is_relative_to(checkout)


def test_fresh_checkout_dry_run_reads_36_records(checkout: Path) -> None:
    out = checkout.parent / "dry-out"
    done = run_in_checkout(checkout, "run", INPUT, "--out", str(out), "--dry-run", "--json")
    assert done.returncode == 0, done.stderr
    summary = json.loads(done.stdout)
    assert summary["dry_run"] is True
    assert summary["counts"]["records_used"] == 36
    assert summary["counts"]["dropped"] == 0
    assert summary["caps_hit"] == []
    assert not out.exists()


def test_fresh_checkout_check_passes_on_the_reference_run(checkout: Path) -> None:
    done = run_in_checkout(checkout, "check-example", REFERENCE)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "Result: MATCH" in done.stdout
    assert RESULT_MATCH in done.stdout


def test_fresh_checkout_check_fails_on_a_changed_byte(checkout: Path) -> None:
    copy = checkout / "changed-run"
    shutil.copytree(checkout / REFERENCE, copy)
    try:
        flip_one_byte(copy / "unusual-pairs.json")
        done = run_in_checkout(checkout, "check-example", str(copy))
    finally:
        shutil.rmtree(copy)
    assert done.returncode == 1, done.stdout + done.stderr
    assert "unusual-pairs.json" in done.stdout


@pytest.mark.skipif(
    os.environ.get("EUREKA_EXAMPLE_REAL_RUN") != "1",
    reason="set EUREKA_EXAMPLE_REAL_RUN=1 to run the real model",
)
def test_fresh_checkout_real_run_matches_the_expected_hashes(
    checkout: Path, tmp_path: Path
) -> None:
    found = discover_model()
    if found.path is None:
        pytest.fail(
            "The real run was requested but no local meaning model was found. "
            "Run `uv run eureka doctor` and follow the fix text. "
            + " ".join(found.problems or found.searched)
        )
    out = tmp_path / "my-run"
    ran = run_in_checkout(
        checkout,
        "run",
        INPUT,
        "--out",
        str(out),
        "--threads",
        "1",
        timeout=REAL_RUN_TIMEOUT,
    )
    assert ran.returncode == 0, ran.stderr
    checked = run_in_checkout(checkout, "check-example", str(out))
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert RESULT_MATCH in checked.stdout
    for name in OUTPUT_FILES:
        assert (out / name).read_bytes() == (ROOT / REFERENCE / name).read_bytes(), name
    flip_one_byte(out / "unusual-pairs.json")
    changed = run_in_checkout(checkout, "check-example", str(out))
    assert changed.returncode == 1, changed.stdout + changed.stderr
