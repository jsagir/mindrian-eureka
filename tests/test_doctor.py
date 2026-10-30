"""Tests for `eureka doctor` (doctor.py)."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
from mindrian_eureka.doctor import (
    CheckResult,
    Probes,
    Status,
    doctor_command,
    format_report,
    report_json,
    run_checks,
)
from mindrian_eureka.models import ENV_RS_MODEL_PATH

SRC = Path(__file__).resolve().parents[1] / "src"
IS_POSIX = os.name == "posix"
IS_ROOT = IS_POSIX and os.geteuid() == 0


def _uid() -> int:
    return os.geteuid() if IS_POSIX else -1


def _probes(
    *,
    python_version: tuple[int, int, int] = (3, 12, 3),
    which: Callable[[str], str | None] | None = None,
    find_spec: Callable[[str], object | None] | None = None,
    run_command: Callable[[Sequence[str]], str] | None = None,
    is_posix: bool = True,
    geteuid: Callable[[], int] | None = None,
    loader: Callable[[Path], int] | None = None,
) -> Probes:
    return Probes(
        python_version=python_version,
        which=which or (lambda name: f"/usr/bin/{name}"),
        find_spec=find_spec or (lambda name: object()),
        run_command=run_command or (lambda args: "uv 0.9.4\n"),
        is_posix=is_posix,
        geteuid=geteuid or _uid,
        loader=loader or (lambda path: 384),
    )


def _env(tmp_path: Path) -> dict[str, str]:
    return {
        "MINDRIAN_EUREKA_CACHE_DIR": str(tmp_path / "cache"),
        "MINDRIAN_EUREKA_DATA_DIR": str(tmp_path / "data"),
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
    }


def _run(
    tmp_path: Path,
    model: Path | None,
    *,
    probes: Probes | None = None,
    env: dict[str, str] | None = None,
    load_model: bool = False,
) -> dict[str, CheckResult]:
    results = run_checks(
        model_path=model,
        load_model=load_model,
        env=_env(tmp_path) if env is None else env,
        home=tmp_path / "home",
        probes=probes or _probes(),
    )
    return {item.id: item for item in results}


# --- healthy setup ----------


def test_healthy_setup_has_no_failure(tmp_path: Path, fake_model_dir: Path) -> None:
    checks = _run(tmp_path, fake_model_dir)
    assert list(checks) == ["D1", "D2", "D3", "D4", "D5", "D6", "D7"]
    assert all(item.status is Status.PASS for item in checks.values())
    assert all(item.fix is None for item in checks.values())


# --- D1 Python ----------


@pytest.mark.parametrize(
    ("version", "status"),
    [
        ((3, 8, 0), Status.FAIL),
        ((3, 10, 14), Status.FAIL),
        ((3, 11, 0), Status.PASS),
        ((3, 12, 3), Status.PASS),
    ],
)
def test_python_version(
    tmp_path: Path, fake_model_dir: Path, version: tuple[int, int, int], status: Status
) -> None:
    result = _run(tmp_path, fake_model_dir, probes=_probes(python_version=version))["D1"]
    assert result.status is status


def test_python_fail_text(tmp_path: Path, fake_model_dir: Path) -> None:
    result = _run(tmp_path, fake_model_dir, probes=_probes(python_version=(3, 10, 4)))["D1"]
    assert result.message == "Python 3.10.4. Eureka needs 3.11 or newer."
    assert result.fix is not None
    assert "Run: uv python install 3.12" in result.fix
    assert (
        "Offline machine: ask the administrator to install Python 3.11 or newer, "
        "then run: uv sync --extra modern-encoder"
    ) in result.fix


# --- D2 uv ----------


def test_missing_uv_is_fail_with_both_systems(tmp_path: Path, fake_model_dir: Path) -> None:
    probes = _probes(which=lambda name: None)
    result = _run(tmp_path, fake_model_dir, probes=probes)["D2"]
    assert result.status is Status.FAIL
    assert result.fix is not None
    assert "On Linux or macOS: curl -LsSf https://astral.sh/uv/install.sh | sh" in result.fix
    assert "On Windows (PowerShell): powershell -ExecutionPolicy ByPass" in result.fix
    assert "Offline machine: copy the uv program from a trusted release" in result.fix


def test_uv_version_comes_from_the_command_runner(tmp_path: Path, fake_model_dir: Path) -> None:
    seen: list[list[str]] = []

    def runner(args: Sequence[str]) -> str:
        seen.append(list(args))
        return "uv 9.9.9\n"

    result = _run(tmp_path, fake_model_dir, probes=_probes(run_command=runner))["D2"]
    assert seen == [["uv", "--version"]]
    assert result.status is Status.PASS
    assert "uv 9.9.9" in result.message


def test_uv_version_failure_is_warn(tmp_path: Path, fake_model_dir: Path) -> None:
    def broken(args: Sequence[str]) -> str:
        raise OSError("boom")

    result = _run(tmp_path, fake_model_dir, probes=_probes(run_command=broken))["D2"]
    assert result.status is Status.WARN
    assert result.fix == "Run: uv --version"


# --- D3 libraries ----------


def test_missing_libraries_are_listed(tmp_path: Path, fake_model_dir: Path) -> None:
    gone = {"scipy", "sentence_transformers"}
    probes = _probes(find_spec=lambda name: None if name in gone else object())
    result = _run(tmp_path, fake_model_dir, probes=probes)["D3"]
    assert result.status is Status.FAIL
    assert "scipy, sentence_transformers" in result.message
    assert result.fix is not None
    assert "Run: uv sync --extra modern-encoder" in result.fix
    assert "uv sync --extra modern-encoder --offline" in result.fix
    assert "uv pip install --no-index --find-links <wheel-folder> sentence-transformers" in (
        result.fix
    )


# --- D4 model (DOC-02) ----------


def test_missing_model_names_every_searched_place(tmp_path: Path) -> None:
    result = _run(tmp_path, None)["D4"]
    assert result.status is Status.FAIL
    assert result.message.startswith("No local model found.")
    for place in ("--model-path", "MINDRIAN_EUREKA_RS_MODEL_PATH",
                  "MINDRIAN_EUREKA_HSI_MODEL_PATH", "Hugging Face cache"):
        assert place in result.message
    assert result.fix is not None
    held = {line.strip() for line in result.message.splitlines()}
    assert all(line.strip() in held for line in result.fix.splitlines())
    assert "uv run hf download sentence-transformers/all-MiniLM-L6-v2" in result.fix


def test_missing_model_is_loud(isolated_env: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = io.StringIO()
    code = doctor_command(json_output=False, load_model=False, model_path=None, out=out)
    report = out.getvalue()
    assert code == 1
    assert "[FAIL] D4 Local model: No local model found." in report
    assert "Searched:" in report
    assert "Result:" in report
    assert report.count("uv run hf download") == 1
    assert capsys.readouterr().err == ""


def test_invalid_explicit_model_is_fail_not_fallthrough(
    tmp_path: Path, fake_model_dir: Path
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    env = {**_env(tmp_path), ENV_RS_MODEL_PATH: str(fake_model_dir)}
    result = _run(tmp_path, empty, env=env)["D4"]
    assert result.status is Status.FAIL
    assert result.message.startswith("The local model is not usable.")


# --- D5 and D6 folders ----------

FOLDERS = [("D5", "MINDRIAN_EUREKA_CACHE_DIR", "cache"), ("D6", "MINDRIAN_EUREKA_DATA_DIR", "data")]


@pytest.mark.skipif(not IS_POSIX, reason="needs POSIX permissions")
@pytest.mark.parametrize(("check", "variable", "name"), FOLDERS)
def test_folder_mode_700_passes(
    tmp_path: Path, fake_model_dir: Path, check: str, variable: str, name: str
) -> None:
    folder = tmp_path / name
    folder.mkdir()
    folder.chmod(0o700)
    result = _run(tmp_path, fake_model_dir)[check]
    assert result.status is Status.PASS
    assert "mode 700" in result.message


@pytest.mark.skipif(not IS_POSIX, reason="needs POSIX permissions")
@pytest.mark.parametrize(("check", "variable", "name"), FOLDERS)
@pytest.mark.parametrize("mode", [0o755, 0o750, 0o705, 0o777])
def test_folder_open_to_others_fails(
    tmp_path: Path, fake_model_dir: Path, check: str, variable: str, name: str, mode: int
) -> None:
    folder = tmp_path / name
    folder.mkdir()
    folder.chmod(mode)
    result = _run(tmp_path, fake_model_dir)[check]
    assert result.status is Status.FAIL
    assert f"mode {mode:o}" in result.message
    assert result.fix is not None
    assert f"On Linux or macOS: chmod 700 {folder}" in result.fix
    assert f'On Windows (PowerShell): icacls "{folder}" /inheritance:r' in result.fix


@pytest.mark.skipif(not IS_POSIX, reason="needs POSIX permissions")
@pytest.mark.parametrize(("check", "variable", "name"), FOLDERS)
def test_loose_file_in_private_folder_is_warn(
    tmp_path: Path, fake_model_dir: Path, check: str, variable: str, name: str
) -> None:
    folder = tmp_path / name
    folder.mkdir()
    folder.chmod(0o700)
    loose = folder / "embeddings.sqlite3-wal"
    loose.write_text("x", encoding="utf-8")
    loose.chmod(0o644)
    (folder / "ok.bin").write_text("x", encoding="utf-8")
    (folder / "ok.bin").chmod(0o600)
    result = _run(tmp_path, fake_model_dir)[check]
    assert result.status is Status.WARN
    assert "embeddings.sqlite3-wal (mode 644)" in result.message
    assert "ok.bin" not in result.message
    assert result.fix is not None
    assert f"chmod 600 {loose}" in result.fix


@pytest.mark.skipif(not IS_POSIX, reason="needs POSIX permissions")
def test_folder_of_another_owner_fails(tmp_path: Path, fake_model_dir: Path) -> None:
    folder = tmp_path / "cache"
    folder.mkdir()
    folder.chmod(0o700)
    probes = _probes(geteuid=lambda: _uid() + 1)
    result = _run(tmp_path, fake_model_dir, probes=probes)["D5"]
    assert result.status is Status.FAIL
    assert "owned by another user" in result.message
    assert result.fix is not None
    assert "MINDRIAN_EUREKA_CACHE_DIR" in result.fix


def test_missing_folder_with_writable_parent_passes(tmp_path: Path, fake_model_dir: Path) -> None:
    result = _run(tmp_path, fake_model_dir)["D5"]
    assert result.status is Status.PASS
    assert "will be created with mode 700" in result.message


@pytest.mark.skipif(not IS_POSIX or IS_ROOT, reason="needs POSIX permissions and a normal user")
def test_missing_folder_with_unwritable_parent_fails(
    tmp_path: Path, fake_model_dir: Path
) -> None:
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        env = {**_env(tmp_path), "MINDRIAN_EUREKA_CACHE_DIR": str(locked / "deep" / "cache")}
        result = _run(tmp_path, fake_model_dir, env=env)["D5"]
    finally:
        locked.chmod(0o700)
    assert result.status is Status.FAIL
    assert "not writable" in result.message
    assert result.fix is not None
    assert "MINDRIAN_EUREKA_CACHE_DIR" in result.fix


def test_folder_path_that_is_a_file_fails(tmp_path: Path, fake_model_dir: Path) -> None:
    (tmp_path / "data").write_text("x", encoding="utf-8")
    result = _run(tmp_path, fake_model_dir)["D6"]
    assert result.status is Status.FAIL
    assert "not a folder" in result.message


def test_non_posix_system_gets_a_warning_with_windows_fix(
    tmp_path: Path, fake_model_dir: Path
) -> None:
    checks = _run(tmp_path, fake_model_dir, probes=_probes(is_posix=False))
    for key in ("D5", "D6"):
        assert checks[key].status is Status.WARN
        assert "not checked on this operating system" in checks[key].message
        fix = checks[key].fix
        assert fix is not None
        assert "icacls" in fix
        assert "On Windows (PowerShell)" in fix


def test_folder_paths_equal_the_cache_and_job_defaults(
    isolated_env: Path, fake_model_dir: Path
) -> None:
    from mindrian_eureka.opportunity_pairs.cache import default_cache_path
    from mindrian_eureka.opportunity_pairs.jobs import default_data_dir

    results = {item.id: item for item in run_checks(model_path=fake_model_dir)}
    assert str(default_cache_path().parent) in results["D5"].message
    assert str(default_data_dir()) in results["D6"].message


def test_folder_paths_equal_the_defaults_without_overrides(
    isolated_env: Path, fake_model_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mindrian_eureka.opportunity_pairs.cache import default_cache_path
    from mindrian_eureka.opportunity_pairs.jobs import default_data_dir

    monkeypatch.delenv("MINDRIAN_EUREKA_CACHE_DIR")
    monkeypatch.delenv("MINDRIAN_EUREKA_DATA_DIR")
    results = {item.id: item for item in run_checks(model_path=fake_model_dir)}
    assert str(default_cache_path().parent) in results["D5"].message
    assert str(default_data_dir()) in results["D6"].message


# --- D7 offline variables ----------


@pytest.mark.parametrize(
    ("values", "status"),
    [
        ({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}, Status.PASS),
        ({"HF_HUB_OFFLINE": "1"}, Status.WARN),
        ({"TRANSFORMERS_OFFLINE": "1"}, Status.WARN),
        ({"HF_HUB_OFFLINE": "0", "TRANSFORMERS_OFFLINE": "1"}, Status.WARN),
        ({}, Status.WARN),
    ],
)
def test_offline_variables(
    tmp_path: Path, fake_model_dir: Path, values: dict[str, str], status: Status
) -> None:
    env = {k: v for k, v in _env(tmp_path).items() if not k.endswith("OFFLINE")}
    env.update(values)
    result = _run(tmp_path, fake_model_dir, env=env)["D7"]
    assert result.status is status
    if status is Status.WARN:
        assert result.fix is not None
        assert "On Linux or macOS: export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1" in result.fix
        assert 'On Windows (PowerShell): $env:HF_HUB_OFFLINE = "1"' in result.fix
        assert "`eureka run` sets them itself" in result.message


# --- D8 model loads ----------


def test_model_load_passes_with_width_from_the_loader(
    tmp_path: Path, fake_model_dir: Path
) -> None:
    seen: list[Path] = []

    def loader(path: Path) -> int:
        seen.append(path)
        return 7

    checks = _run(tmp_path, fake_model_dir, probes=_probes(loader=loader), load_model=True)
    assert checks["D8"].status is Status.PASS
    assert "width 7" in checks["D8"].message
    assert seen == [fake_model_dir]


def test_model_load_failure_is_fail_with_exception_text(
    tmp_path: Path, fake_model_dir: Path
) -> None:
    def loader(path: Path) -> int:
        raise RuntimeError("weights are broken")

    checks = _run(tmp_path, fake_model_dir, probes=_probes(loader=loader), load_model=True)
    assert checks["D8"].status is Status.FAIL
    assert "weights are broken" in checks["D8"].message
    assert checks["D8"].fix is not None
    assert "uv run hf download" in checks["D8"].fix


def test_model_load_is_skipped_when_the_model_is_missing(tmp_path: Path) -> None:
    called: list[Path] = []

    def loader(path: Path) -> int:
        called.append(path)
        return 1

    checks = _run(tmp_path, None, probes=_probes(loader=loader), load_model=True)
    assert "D8" not in checks
    assert called == []


def test_model_load_is_not_run_by_default(tmp_path: Path, fake_model_dir: Path) -> None:
    def loader(path: Path) -> int:
        raise AssertionError("must not load")

    checks = _run(tmp_path, fake_model_dir, probes=_probes(loader=loader))
    assert "D8" not in checks


@pytest.mark.skipif(
    not os.environ.get("EUREKA_TEST_MODEL_PATH"), reason="EUREKA_TEST_MODEL_PATH is not set"
)
def test_real_model_loads(tmp_path: Path) -> None:
    folder = Path(os.environ["EUREKA_TEST_MODEL_PATH"])
    checks = _run(tmp_path, folder, probes=Probes(), load_model=True)
    assert checks["D8"].status is Status.PASS


# --- report and JSON ----------


def test_report_layout(tmp_path: Path, fake_model_dir: Path) -> None:
    probes = _probes(python_version=(3, 9, 1))
    results = list(_run(tmp_path, fake_model_dir, probes=probes).values())
    lines = format_report(results).splitlines()
    assert lines[0] == "Eureka doctor"
    assert lines[1] == "[FAIL] D1 Python: Python 3.9.1. Eureka needs 3.11 or newer."
    assert lines[2] == "  Fix: Run: uv python install 3.12"
    assert lines[3].startswith("  Offline machine: ask the administrator")
    assert lines[4].startswith("[PASS] D2 uv: ")
    assert lines[-1] == "Result: 6 passed, 0 warnings, 1 failed."
    assert "\x1b" not in "\n".join(lines)


def test_every_fail_prints_its_fix(tmp_path: Path) -> None:
    probes = _probes(
        python_version=(3, 8, 0), which=lambda name: None, find_spec=lambda name: None
    )
    results = list(_run(tmp_path, None, probes=probes).values())
    report = format_report(results)
    failed = [item for item in results if item.status is Status.FAIL]
    assert [item.id for item in failed] == ["D1", "D2", "D3", "D4"]
    for item in failed:
        assert item.fix is not None
        for line in item.fix.splitlines():
            assert line in report


def test_json_shape_and_canonical_form(tmp_path: Path, fake_model_dir: Path) -> None:
    results = list(_run(tmp_path, fake_model_dir, probes=_probes(which=lambda n: None)).values())
    text = report_json(results)
    data = json.loads(text)
    assert set(data) == {"schema_version", "ok", "checks"}
    assert data["schema_version"] == "eureka.doctor.v1"
    assert data["ok"] is False
    assert set(data["checks"][0]) == {"id", "name", "status", "message", "fix"}
    assert data["checks"][0]["fix"] is None
    assert text.endswith("\n")
    assert text == json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def test_json_ok_is_true_with_warnings_only(tmp_path: Path, fake_model_dir: Path) -> None:
    env = {k: v for k, v in _env(tmp_path).items() if not k.endswith("OFFLINE")}
    results = list(_run(tmp_path, fake_model_dir, env=env).values())
    data = json.loads(report_json(results))
    assert data["ok"] is True
    assert data["checks"][-1]["status"] == "WARN"


def test_exit_code_zero_without_failure(
    isolated_env: Path, fake_model_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mindrian_eureka import doctor

    monkeypatch.setattr(doctor, "Probes", lambda: _probes())
    out = io.StringIO()
    code = doctor_command(json_output=True, load_model=False, model_path=fake_model_dir, out=out)
    assert code == 0
    assert json.loads(out.getvalue())["ok"] is True


def test_doctor_command_writes_to_stdout_by_default(
    isolated_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = doctor_command(json_output=False, load_model=False, model_path=None)
    captured = capsys.readouterr()
    assert code == 1
    assert captured.out.startswith("Eureka doctor\n")
    assert captured.err == ""


# --- safety ----------


def _tree(root: Path) -> list[tuple[str, int, bytes]]:
    entries: list[tuple[str, int, bytes]] = []
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        data = path.read_bytes() if path.is_file() else b""
        entries.append((str(path.relative_to(root)), info.st_mode, data))
    return entries


@pytest.mark.skipif(not IS_POSIX, reason="needs POSIX permissions")
def test_checks_change_nothing_on_disk(tmp_path: Path, fake_model_dir: Path) -> None:
    cache = tmp_path / "cache"
    cache.mkdir()
    cache.chmod(0o755)
    (cache / "embeddings.sqlite3").write_text("x", encoding="utf-8")
    (cache / "embeddings.sqlite3").chmod(0o644)
    before = _tree(tmp_path)
    run_checks(
        model_path=fake_model_dir,
        env=_env(tmp_path),
        home=tmp_path / "home",
        probes=_probes(),
    )
    assert _tree(tmp_path) == before
    assert not (tmp_path / "data").exists()
    assert not (tmp_path / "home").exists()


def test_no_socket_is_opened(
    isolated_env: Path, fake_model_dir: Path, no_network: list[object]
) -> None:
    run_checks(model_path=fake_model_dir)
    doctor_command(json_output=False, load_model=False, model_path=None, out=io.StringIO())
    assert no_network == []


def test_light_import_and_run(tmp_path: Path) -> None:
    code = (
        "import sys\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from pathlib import Path\n"
        "from mindrian_eureka.doctor import Probes, run_checks\n"
        "probes = Probes(which=lambda n: '/bin/' + n, find_spec=lambda n: object(),\n"
        "                run_command=lambda a: 'uv 1\\n')\n"
        "run_checks(env={}, home=Path(sys.argv[2]), probes=probes)\n"
        "heavy = {'numpy', 'torch', 'sklearn', 'scipy', 'sentence_transformers',\n"
        "         'huggingface_hub', 'transformers'}\n"
        "found = heavy & set(sys.modules)\n"
        "print(sorted(found))\n"
        "sys.exit(1 if found else 0)\n"
    )
    done = subprocess.run(
        [sys.executable, "-I", "-c", code, str(SRC), str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr


def test_check_result_is_frozen() -> None:
    item = CheckResult("D1", "Python", Status.PASS, "ok", None)
    with pytest.raises(AttributeError):
        item.id = "D2"  # type: ignore[misc]
