"""The `eureka doctor` command: check the setup and print the exact fix for each failure.

The doctor checks Python, uv, the encoder libraries, the local model, the cache folder,
the data folder and the offline variables. It prints fix commands. It never runs them.
It makes no network call and creates, changes or deletes nothing on disk. Heavy
libraries load only when the user passes `--load-model`.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TextIO

from .models import (
    discover_model,
    missing_model_message,
    model_fix_text,
    os_variants,
)
from .run.contracts import EXIT_FAILURE, EXIT_OK

DOCTOR_SCHEMA = "eureka.doctor.v1"
MIN_PYTHON = (3, 11, 0)
REQUIRED_LIBRARIES = ("numpy", "sklearn", "scipy", "jsonschema", "sentence_transformers")
ENV_CACHE_DIR = "MINDRIAN_EUREKA_CACHE_DIR"
ENV_DATA_DIR = "MINDRIAN_EUREKA_DATA_DIR"
_CHECK_SENTENCE = "Eureka doctor check sentence."


class Status(str, Enum):
    """The result of one check."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class CheckResult:
    """The result of one check.

    Attributes:
        id: The check id, D1 to D8.
        name: The short check name.
        status: PASS, WARN or FAIL.
        message: What was found, in plain English. It can span several lines.
        fix: The exact fix text, or None for a PASS.
    """

    id: str
    name: str
    status: Status
    message: str
    fix: str | None


def _default_python_version() -> tuple[int, int, int]:
    info = sys.version_info
    return (info.major, info.minor, info.micro)


def _default_which(command: str) -> str | None:
    return shutil.which(command)


def _default_find_spec(name: str) -> object | None:
    return importlib.util.find_spec(name)


def _default_run_command(args: Sequence[str]) -> str:
    """Run a fixed argument list without a shell and return its standard output."""
    done = subprocess.run(
        list(args), capture_output=True, text=True, timeout=10, check=False
    )
    if done.returncode != 0:
        raise OSError(f"exit code {done.returncode}")
    return done.stdout


def _default_is_posix() -> bool:
    return os.name == "posix"


def _default_geteuid() -> int:
    getter = getattr(os, "geteuid", None)
    return int(getter()) if getter is not None else -1


def _default_loader(model_dir: Path) -> int:
    """Load the local model, encode one sentence and return the vector width."""
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(str(model_dir), local_files_only=True)
    vectors = model.encode([_CHECK_SENTENCE])
    return int(vectors.shape[-1])


@dataclass(frozen=True)
class Probes:
    """The system probes of the doctor. Tests replace them.

    Attributes:
        python_version: The Python version as three integers.
        which: Find a program on PATH.
        find_spec: Find an import spec without importing the module.
        run_command: Run a fixed argument list and return standard output.
        is_posix: True on Linux and macOS.
        geteuid: The user id of the current user.
        loader: Load the model folder and return the vector width.
    """

    python_version: tuple[int, int, int] = field(default_factory=_default_python_version)
    which: Callable[[str], str | None] = _default_which
    find_spec: Callable[[str], object | None] = _default_find_spec
    run_command: Callable[[Sequence[str]], str] = _default_run_command
    is_posix: bool = field(default_factory=_default_is_posix)
    geteuid: Callable[[], int] = _default_geteuid
    loader: Callable[[Path], int] = _default_loader


def _check_python(probes: Probes) -> CheckResult:
    found = probes.python_version
    text = ".".join(str(part) for part in found)
    if found < MIN_PYTHON:
        return CheckResult(
            "D1",
            "Python",
            Status.FAIL,
            f"Python {text}. Eureka needs 3.11 or newer.",
            "Run: uv python install 3.12\n"
            "Offline machine: ask the administrator to install Python 3.11 or newer, "
            "then run: uv sync --extra modern-encoder",
        )
    return CheckResult("D1", "Python", Status.PASS, f"Python {text}.", None)


def _check_uv(probes: Probes) -> CheckResult:
    if probes.which("uv") is None:
        fix = (
            os_variants(
                "curl -LsSf https://astral.sh/uv/install.sh | sh",
                "powershell -ExecutionPolicy ByPass -c "
                '"irm https://astral.sh/uv/install.ps1 | iex"',
            )
            + "\nOffline machine: copy the uv program from a trusted release into a folder "
            "on PATH, then run: uv --version"
        )
        return CheckResult("D2", "uv", Status.FAIL, "uv was not found on PATH.", fix)
    try:
        version = probes.run_command(["uv", "--version"]).strip()
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        return CheckResult(
            "D2",
            "uv",
            Status.WARN,
            f"uv is on PATH but its version could not be read ({error}).",
            "Run: uv --version",
        )
    return CheckResult("D2", "uv", Status.PASS, f"{version or 'uv'} found on PATH.", None)


def _check_libraries(probes: Probes) -> CheckResult:
    missing = [name for name in REQUIRED_LIBRARIES if probes.find_spec(name) is None]
    if missing:
        return CheckResult(
            "D3",
            "Libraries",
            Status.FAIL,
            "Missing Python libraries: " + ", ".join(missing) + ".",
            "Run: uv sync --extra modern-encoder\n"
            "Offline machine: uv sync --extra modern-encoder --offline "
            "(needs the packages in the uv cache), or: "
            "uv pip install --no-index --find-links <wheel-folder> sentence-transformers",
        )
    return CheckResult(
        "D3", "Libraries", Status.PASS, "All encoder libraries can be imported.", None
    )


def _check_model(
    model_path: Path | None, env: Mapping[str, str], home: Path
) -> tuple[CheckResult, Path | None]:
    resolution = discover_model(model_path, env=env, home=home)
    if not resolution.ok or resolution.path is None:
        message = missing_model_message(resolution, explicit_given=model_path is not None)
        result = CheckResult("D4", "Local model", Status.FAIL, message, model_fix_text())
        return result, None
    text = f"Model folder {resolution.path} (from {resolution.origin})."
    return CheckResult("D4", "Local model", Status.PASS, text, None), resolution.path


def _cache_dir(env: Mapping[str, str], home: Path) -> Path:
    override = env.get(ENV_CACHE_DIR, "")
    return Path(override).expanduser() if override else home / ".cache" / "mindrian-eureka"


def _data_dir(env: Mapping[str, str], home: Path) -> Path:
    override = env.get(ENV_DATA_DIR, "")
    if override:
        return Path(override).expanduser()
    return home / ".local" / "share" / "mindrian-eureka"


def _icacls(folder: Path) -> str:
    return f'icacls "{folder}" /inheritance:r /grant:r "%USERNAME%:(OI)(CI)F"'


def _nearest_existing_parent(folder: Path) -> Path:
    parent = folder.parent
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent
    return parent


def _check_folder(
    check_id: str, name: str, folder: Path, variable: str, probes: Probes
) -> CheckResult:
    """Check one folder for owner-only permissions. Nothing is created or changed."""
    chmod_fix = os_variants(f"chmod 700 {folder}", _icacls(folder))
    if not probes.is_posix:
        return CheckResult(
            check_id,
            name,
            Status.WARN,
            f"{folder}: owner-only permissions are not checked on this operating system.",
            "Restrict the folder to your own user. " + chmod_fix,
        )
    if not folder.exists():
        parent = _nearest_existing_parent(folder)
        if os.access(parent, os.W_OK):
            return CheckResult(
                check_id,
                name,
                Status.PASS,
                f"{folder} does not exist yet; it will be created with mode 700.",
                None,
            )
        return CheckResult(
            check_id,
            name,
            Status.FAIL,
            f"{folder} does not exist and {parent} is not writable.",
            f"Make {parent} writable for your user, or set {variable} to a folder you own.",
        )
    if not folder.is_dir():
        return CheckResult(
            check_id,
            name,
            Status.FAIL,
            f"{folder} exists but is not a folder.",
            f"Move or delete that file, or set {variable} to a folder you own.",
        )
    info = folder.stat()
    mode = stat.S_IMODE(info.st_mode)
    if info.st_uid != probes.geteuid():
        return CheckResult(
            check_id,
            name,
            Status.FAIL,
            f"{folder} is owned by another user (user id {info.st_uid}).",
            f"Use a folder you own: set {variable} to a new folder, then run: "
            + os_variants("chmod 700 <new-folder>", _icacls(Path("<new-folder>"))),
        )
    if mode & 0o077:
        return CheckResult(
            check_id,
            name,
            Status.FAIL,
            f"{folder} has mode {mode:o}; group or other users can enter it.",
            chmod_fix,
        )
    if not os.access(folder, os.W_OK | os.X_OK):
        return CheckResult(
            check_id,
            name,
            Status.FAIL,
            f"{folder} is not writable for your user (mode {mode:o}).",
            chmod_fix,
        )
    loose: list[tuple[Path, int]] = []
    for entry in sorted(folder.iterdir(), key=lambda item: item.name):
        entry_mode = entry.lstat().st_mode
        if stat.S_ISREG(entry_mode) and stat.S_IMODE(entry_mode) & 0o077:
            loose.append((entry, stat.S_IMODE(entry_mode)))
    if loose:
        listed = ", ".join(f"{entry.name} (mode {file_mode:o})" for entry, file_mode in loose)
        fixes = "\n".join(
            os_variants(f"chmod 600 {entry}", _icacls(folder)) for entry, _ in loose
        )
        return CheckResult(
            check_id,
            name,
            Status.WARN,
            f"{folder} has mode {mode:o}, but these files allow group or other access: "
            f"{listed}.",
            fixes,
        )
    return CheckResult(check_id, name, Status.PASS, f"{folder} has mode {mode:o}.", None)


def _check_offline_env(env: Mapping[str, str]) -> CheckResult:
    unset = [
        name for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE") if env.get(name) != "1"
    ]
    if unset:
        return CheckResult(
            "D7",
            "Offline variables",
            Status.WARN,
            "Not set to 1: " + ", ".join(unset) + ". `eureka run` sets them itself.",
            os_variants(
                "export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1",
                '$env:HF_HUB_OFFLINE = "1"; $env:TRANSFORMERS_OFFLINE = "1"',
            ),
        )
    text = "HF_HUB_OFFLINE and TRANSFORMERS_OFFLINE are 1."
    return CheckResult("D7", "Offline variables", Status.PASS, text, None)


def _check_model_loads(model_dir: Path, probes: Probes) -> CheckResult:
    try:
        width = probes.loader(model_dir)
    except Exception as error:  # model libraries raise many error types
        return CheckResult(
            "D8",
            "Model loads",
            Status.FAIL,
            f"The model did not load from {model_dir}: {type(error).__name__}: {error}",
            model_fix_text(),
        )
    text = f"The model loaded and gave vectors of width {width}."
    return CheckResult("D8", "Model loads", Status.PASS, text, None)


def run_checks(
    *,
    model_path: Path | None = None,
    load_model: bool = False,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
    probes: Probes | None = None,
) -> list[CheckResult]:
    """Run all checks. Nothing is created, changed or downloaded.

    Args:
        model_path: The folder given with `--model-path`, or None.
        load_model: True to load the model and encode one sentence (check D8).
        env: The environment. The default is `os.environ`.
        home: The home folder. The default is `Path.home()`.
        probes: Replacement system probes. The default uses the real system.

    Returns:
        The results in order D1 to D7, then D8 when `load_model` is true and D4 passed.
    """
    environment: Mapping[str, str] = os.environ if env is None else env
    home_dir = Path.home() if home is None else home
    system = Probes() if probes is None else probes
    model_result, model_dir = _check_model(model_path, environment, home_dir)
    results = [
        _check_python(system),
        _check_uv(system),
        _check_libraries(system),
        model_result,
        _check_folder(
            "D5", "Cache folder", _cache_dir(environment, home_dir), ENV_CACHE_DIR, system
        ),
        _check_folder("D6", "Data folder", _data_dir(environment, home_dir), ENV_DATA_DIR, system),
        _check_offline_env(environment),
    ]
    if load_model and model_dir is not None:
        results.append(_check_model_loads(model_dir, system))
    return results


def _message_holds_fix(result: CheckResult) -> bool:
    """True when every line of the fix already appears in the message (check D4)."""
    if result.fix is None:
        return True
    held = {line.strip() for line in result.message.splitlines()}
    return all(line.strip() in held for line in result.fix.splitlines())


def format_report(results: Sequence[CheckResult]) -> str:
    """Format the results as plain text. No color, no prompts.

    Args:
        results: The check results.

    Returns:
        The report with a final newline.
    """
    lines = ["Eureka doctor"]
    for result in results:
        head, *rest = result.message.splitlines() or [""]
        lines.append(f"[{result.status.value}] {result.id} {result.name}: {head}")
        lines.extend(f"  {line}" if line else "" for line in rest)
        if result.fix is not None and not _message_holds_fix(result):
            fix_lines = result.fix.splitlines()
            lines.append(f"  Fix: {fix_lines[0]}")
            lines.extend(f"  {line}" for line in fix_lines[1:])
    passed = sum(1 for item in results if item.status is Status.PASS)
    warned = sum(1 for item in results if item.status is Status.WARN)
    failed = sum(1 for item in results if item.status is Status.FAIL)
    lines.append(f"Result: {passed} passed, {warned} warnings, {failed} failed.")
    return "\n".join(lines) + "\n"


def report_json(results: Sequence[CheckResult]) -> str:
    """Format the results as canonical JSON (sorted keys, indent 2, final newline).

    Args:
        results: The check results.

    Returns:
        The JSON text.
    """
    document = {
        "schema_version": DOCTOR_SCHEMA,
        "ok": all(item.status is not Status.FAIL for item in results),
        "checks": [
            {
                "id": item.id,
                "name": item.name,
                "status": item.status.value,
                "message": item.message,
                "fix": item.fix,
            }
            for item in results
        ],
    }
    return json.dumps(document, sort_keys=True, indent=2, ensure_ascii=False) + "\n"


def doctor_command(
    *,
    json_output: bool,
    load_model: bool,
    model_path: Path | None,
    out: TextIO | None = None,
) -> int:
    """Run the doctor and print the report.

    Args:
        json_output: True to print JSON instead of text.
        load_model: True to run check D8.
        model_path: The folder given with `--model-path`, or None.
        out: The output stream. The default is standard output at call time.

    Returns:
        0 when no check is FAIL, else 1.
    """
    stream = sys.stdout if out is None else out
    results = run_checks(model_path=model_path, load_model=load_model)
    stream.write(report_json(results) if json_output else format_report(results))
    failed = any(item.status is Status.FAIL for item in results)
    return EXIT_FAILURE if failed else EXIT_OK
