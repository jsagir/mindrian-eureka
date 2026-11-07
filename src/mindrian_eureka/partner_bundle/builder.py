"""Build one carry-in folder for a partner machine (Phase 2.2, D-07).

The folder `eureka-partner-bundle-<target>` holds the `uv` binary for the target, the
Eureka source at HEAD, the locked requirement list with hashes, the wheel folder
(online builds only), the model folder copied from a local path, the shipped mapping,
a side-car slot, the partner guide, the launchers and `BUNDLE-MANIFEST.json` with a
sha256 and a byte size for every file.

The builder is offline by default. Network is used only inside the `--online`
branches, and only in the functions whose name starts with `_download_`. The model is
never downloaded without `--allow-model-download`. Every subprocess call passes an
argument list; no shell string is built.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import io
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mindrian_eureka import __version__, models
from mindrian_eureka.run.contracts import LABEL
from mindrian_eureka.run.manifest import sha256_file

from . import launchers

MANIFEST_SCHEMA = "eureka.partner-bundle.v1"
MANIFEST_NAME = "BUNDLE-MANIFEST.json"
BUNDLE_PREFIX = "eureka-partner-bundle-"
HOST_ALIAS = "host"
DEFAULT_OUT = "dist"
DEFAULT_IMAGE = "mindrian-eureka:local"
EXTRAS = ("modern-encoder", "hub-gate")
MAPPING_FILE = "technology-audit-export.json"
SIDECAR_EXAMPLE = "text-sidecar.example.csv"
GUIDE_FILE = "partner-run-guide.md"
UV_RELEASE_BASE = "https://github.com/astral-sh/uv/releases/download"


class BundleError(Exception):
    """A build cannot continue. The command line prints the message and the fix.

    Attributes:
        message: What went wrong, in plain English.
        fix: The exact action that fixes it, or None.
    """

    exit_code = 2

    def __init__(self, message: str, *, fix: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.fix = fix


@dataclass(frozen=True)
class Target:
    """One build target.

    Attributes:
        name: The bundle suffix, for example `linux-x86_64`.
        uv_triple: The uv release triple.
        archive: The uv release archive kind, `tar.gz` or `zip`.
        python_platform: The `--python-platform` value of uv.
        pip_platforms: The `--platform` values of `pip download`.
        python_key: The managed Python key of `uv python`.
        launcher: `sh` or `ps1`; the launcher the target opens first.
    """

    name: str
    uv_triple: str
    archive: str
    python_platform: str
    pip_platforms: tuple[str, ...]
    python_key: str
    launcher: str


# The PyTorch CPU index of pyproject.toml (index `pytorch-cpu`). The lock pins torch
# `2.14.1+cpu` from this index, so `pip download` needs it next to PyPI.
PYTORCH_CPU_INDEX = "https://download.pytorch.org/whl/cpu"

# macOS arm64 wheel tags. Source: the wheel file names in uv.lock. The lock holds
# `macosx_11_0_arm64`, `macosx_12_0_arm64` and `macosx_14_0_arm64` (14 is the highest N),
# and the universal2 tags `macosx_10_9`, `macosx_10_13` and `macosx_10_15`.
# `macosx_11_0_universal2` does not appear in the lock.
MACOS_ARM64_PIP_PLATFORMS: tuple[str, ...] = (
    *(f"macosx_{n}_0_arm64" for n in range(11, 15)),
    "macosx_10_9_universal2",
    "macosx_10_13_universal2",
    "macosx_10_15_universal2",
)

# The marker values of each target, keyed by uv triple. `pip download --platform` picks
# the wheel tags of the target, but pip still evaluates every environment marker on the
# builder machine. The builder therefore filters the locked list for the target itself.
_LINUX_MARKERS = {"sys_platform": "linux", "platform_system": "Linux", "os_name": "posix"}
_MACOS_MARKERS = {"sys_platform": "darwin", "platform_system": "Darwin", "os_name": "posix"}
_WINDOWS_MARKERS = {"sys_platform": "win32", "platform_system": "Windows", "os_name": "nt"}
TARGET_MARKERS: dict[str, dict[str, str]] = {
    "x86_64-unknown-linux-gnu": {**_LINUX_MARKERS, "platform_machine": "x86_64"},
    "aarch64-unknown-linux-gnu": {**_LINUX_MARKERS, "platform_machine": "aarch64"},
    "x86_64-pc-windows-msvc": {**_WINDOWS_MARKERS, "platform_machine": "AMD64"},
    "aarch64-apple-darwin": {**_MACOS_MARKERS, "platform_machine": "arm64"},
}
_COMMON_MARKERS = {
    "implementation_name": "cpython",
    "platform_python_implementation": "CPython",
    "python_version": "3.12",
    "python_full_version": "3.12.0",
    "extra": "",
}

TARGETS: dict[str, Target] = {
    "linux-x86_64": Target(
        "linux-x86_64",
        "x86_64-unknown-linux-gnu",
        "tar.gz",
        "x86_64-manylinux_2_28",
        ("manylinux_2_28_x86_64", "manylinux2014_x86_64"),
        "cpython-3.12-linux-x86_64-gnu",
        "sh",
    ),
    "windows-x86_64": Target(
        "windows-x86_64",
        "x86_64-pc-windows-msvc",
        "zip",
        "x86_64-pc-windows-msvc",
        ("win_amd64",),
        "cpython-3.12-windows-x86_64-none",
        "ps1",
    ),
    "macos-arm64": Target(
        "macos-arm64",
        "aarch64-apple-darwin",
        "tar.gz",
        "aarch64-apple-darwin",
        MACOS_ARM64_PIP_PLATFORMS,
        "cpython-3.12-macos-aarch64-none",
        "sh",
    ),
}

# Builder machines that are not a D-07 target. Only `host` resolves to them.
_HOST_ONLY: dict[str, Target] = {
    "linux-aarch64": Target(
        "linux-aarch64",
        "aarch64-unknown-linux-gnu",
        "tar.gz",
        "aarch64-manylinux_2_28",
        ("manylinux_2_28_aarch64", "manylinux2014_aarch64"),
        "cpython-3.12-linux-aarch64-gnu",
        "sh",
    ),
    "darwin-aarch64": Target(
        "darwin-aarch64",
        "aarch64-apple-darwin",
        "tar.gz",
        "aarch64-apple-darwin",
        ("macosx_11_0_arm64",),
        "cpython-3.12-macos-aarch64-none",
        "sh",
    ),
}

ACCEPTED_NAMES = (*TARGETS, HOST_ALIAS)


def _normalized_machine() -> str:
    machine = platform.machine().lower()
    if machine in {"aarch64", "arm64"}:
        return "aarch64"
    if machine in {"x86_64", "amd64"}:
        return "x86_64"
    return machine


def host_name() -> str:
    """Return `<os>-<arch>` of this machine, for example `linux-aarch64`."""
    return f"{platform.system().lower()}-{_normalized_machine()}"


def resolve_target(name: str) -> Target:
    """Return the target for a name; `host` means the builder machine.

    Args:
        name: One of the 3 D-07 names or `host`.

    Returns:
        The target.

    Raises:
        BundleError: The name is not accepted, or the host machine has no entry.
    """
    accepted = ", ".join(ACCEPTED_NAMES)
    if name == HOST_ALIAS:
        host = host_name()
        found = TARGETS.get(host) or _HOST_ONLY.get(host)
        if found is None:
            raise BundleError(
                f"This machine ({host}) has no target entry.",
                fix=f"Pass --target with one of: {accepted}.",
            )
        return found
    found = TARGETS.get(name)
    if found is None:
        raise BundleError(
            f"Unknown target. Accepted names: {accepted}.",
            fix=f"Pass --target with one of: {accepted}.",
        )
    return found


def _repo_root() -> Path:
    here = Path(__file__).resolve().parent
    done = subprocess.run(
        ["git", "-C", str(here), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise BundleError(
            "The builder must run inside the Eureka git checkout.",
            fix="Run scripts/build-partner-bundle from the repository.",
        )
    return Path(done.stdout.strip())


@dataclass(frozen=True)
class BundleOptions:
    """The builder inputs.

    Attributes:
        target: One of the 3 D-07 names or `host`.
        out_dir: The folder that receives `eureka-partner-bundle-<target>`.
        online: Allow network in the download steps.
        wheels: `download` (needs online) or `skip`.
        model_path: The local model folder. None means the usual search.
        allow_model_download: Fetch the model when none is found (needs online).
        python_from: A managed Python folder to copy, or None.
        docker: Also write the docker variant.
        repo_root: The git checkout that supplies the source.
    """

    target: str
    out_dir: Path
    online: bool = False
    wheels: str = "download"
    model_path: Path | None = None
    allow_model_download: bool = False
    python_from: Path | None = None
    docker: bool = False
    repo_root: Path = field(default_factory=_repo_root)


@dataclass(frozen=True)
class BundleReport:
    """What one build wrote.

    Attributes:
        bundle_dir: The bundle folder.
        target: The resolved target name.
        file_count: The number of files listed in the manifest.
        manifest_sha256: The sha256 of the manifest file.
        builder: The `builder` block of the manifest.
    """

    bundle_dir: Path
    target: str
    file_count: int
    manifest_sha256: str
    builder: dict[str, Any]


def _run(args: Sequence[str], *, cwd: Path | None = None, what: str) -> subprocess.CompletedProcess:
    done = subprocess.run(
        list(args), cwd=cwd, capture_output=True, text=False, check=False
    )
    if done.returncode != 0:
        detail = done.stderr.decode("utf-8", "replace").strip().splitlines()
        first = detail[-1] if detail else f"exit code {done.returncode}"
        raise BundleError(f"{what} failed: {first}", fix=f"Run `{' '.join(args)}` by hand.")
    return done


def _uv_version(uv: str) -> str:
    done = _run([uv, "--version"], what="uv --version")
    words = done.stdout.decode("utf-8", "replace").split()
    return words[1] if len(words) > 1 else words[0] if words else "unknown"


def _require_online(options: BundleOptions, what: str) -> None:
    if not options.online:
        raise BundleError(
            f"{what} needs the network, and --online was not given.",
            fix="Pass --online on a machine with internet, or use --target host.",
        )


# --- steps ------------------------------------------------------------------------


def _check_preconditions(options: BundleOptions, target: Target) -> str:
    uv = shutil.which("uv")
    if uv is None:
        raise BundleError("uv is not on PATH.", fix="Install uv, then run the builder again.")
    if target.name != host_name():
        _require_online(options, f"The target {target.name} (uv binary and wheels)")
    if options.wheels not in {"download", "skip"}:
        raise BundleError(
            f"--wheels must be download or skip, not {options.wheels}.",
            fix="Pass --wheels download or --wheels skip.",
        )
    if options.wheels == "download":
        _require_online(options, "The wheel download")
    if options.allow_model_download:
        _require_online(options, "The model download")
    if options.docker and shutil.which("docker") is None:
        raise BundleError(
            "docker is not on PATH; the --docker variant needs it",
            fix="Install docker, or build without --docker.",
        )
    if options.python_from is not None and not options.python_from.is_dir():
        raise BundleError(
            "The --python-from folder does not exist.",
            fix="Pass a managed Python folder, or leave --python-from out.",
        )
    return uv


def _make_bundle_dir(options: BundleOptions, target: Target) -> Path:
    bundle = options.out_dir / f"{BUNDLE_PREFIX}{target.name}"
    if bundle.exists() and any(bundle.iterdir()):
        raise BundleError(
            f"The folder {bundle.name} exists and is not empty.",
            fix="Remove it, or pass another --out folder.",
        )
    bundle.mkdir(parents=True, exist_ok=True)
    return bundle


def _write_source(options: BundleOptions, bundle: Path) -> str:
    done = _run(
        ["git", "-C", str(options.repo_root), "archive", "--format=tar", "HEAD"],
        what="git archive HEAD",
    )
    source = bundle / "source"
    source.mkdir()
    with tarfile.open(fileobj=io.BytesIO(done.stdout), mode="r:") as archive:
        archive.extractall(source, filter="data")
    commit = _run(
        ["git", "-C", str(options.repo_root), "rev-parse", "HEAD"], what="git rev-parse HEAD"
    )
    return commit.stdout.decode("utf-8").strip()


def _write_requirements(options: BundleOptions, bundle: Path, uv: str) -> None:
    args = [
        uv,
        "export",
        "--frozen",
        "--no-dev",
        "--no-emit-project",
        "--format",
        "requirements-txt",
        "--offline",
        "-o",
        str(bundle / "requirements.txt"),
    ]
    for extra in EXTRAS:
        args[2:2] = ["--extra", extra]
    _run(args, cwd=options.repo_root, what="uv export")


def _write_uv(options: BundleOptions, target: Target, bundle: Path, uv: str) -> None:
    if target.name == host_name():
        name = "uv.exe" if target.launcher == "ps1" else "uv"
        destination = bundle / name
        shutil.copyfile(uv, destination)
        destination.chmod(0o755)
        return
    _download_uv(options, target, bundle)


def _download_uv(options: BundleOptions, target: Target, bundle: Path) -> None:
    """Fetch the uv release archive for the target and verify its published sha256.

    ASSUMED: the release URL shape and the `.sha256` file name. Not run on this machine.
    """
    _require_online(options, f"The uv download for {target.name}")
    import urllib.request

    version = _uv_version(shutil.which("uv") or "uv")
    file_name = f"uv-{target.uv_triple}.{target.archive}"
    url = f"{UV_RELEASE_BASE}/{version}/{file_name}"
    with tempfile.TemporaryDirectory() as temp:
        archive = Path(temp) / file_name
        urllib.request.urlretrieve(url, archive)  # noqa: S310 - fixed https host
        urllib.request.urlretrieve(f"{url}.sha256", archive.with_suffix(archive.suffix + ".sha256"))
        published = (
            archive.with_suffix(archive.suffix + ".sha256").read_text(encoding="utf-8").split()[0]
        )
        actual = sha256_file(archive)
        if actual != published:
            raise BundleError(
                f"The uv archive {file_name} does not match its published sha256.",
                fix="Run the build again. If it repeats, fetch uv by hand from the release page.",
            )
        binary = "uv.exe" if target.archive == "zip" else "uv"
        if target.archive == "zip":
            with zipfile.ZipFile(archive) as packed:
                zip_member = next(m for m in packed.namelist() if m.endswith(binary))
                (bundle / binary).write_bytes(packed.read(zip_member))
        else:
            with tarfile.open(archive, mode="r:gz") as packed:
                tar_member = next(
                    m for m in packed.getmembers() if m.name.endswith("/" + binary)
                )
                handle = packed.extractfile(tar_member)
                if handle is None:
                    raise BundleError(f"The uv archive holds no file named {binary}.")
                (bundle / binary).write_bytes(handle.read())
        (bundle / binary).chmod(0o755)


def _write_wheels(options: BundleOptions, target: Target, bundle: Path, uv: str) -> str:
    if options.wheels == "skip":
        return "skipped"
    _download_wheels(options, target, bundle, uv)
    return "download"


def _pip_download_base(
    target: Target, wheels: Path, uv: str, *, extra_index: bool = True
) -> list[str]:
    """Return the shared `pip download` arguments for one target.

    PyPI stays the default index. The PyTorch CPU index is added with
    `--extra-index-url` because the lock pins `torch==2.14.1+cpu` from it. Only the
    download of the locked, hashed requirements needs it. A download of unpinned,
    unhashed requirements passes `extra_index=False`, so a second index cannot
    answer for them.
    """
    base = [
        uv,
        "run",
        "--with",
        "pip",
        "python",
        "-m",
        "pip",
        "download",
        "--only-binary=:all:",
        *(["--extra-index-url", PYTORCH_CPU_INDEX] if extra_index else []),
        "--python-version",
        "3.12",
        "--implementation",
        "cp",
        "--abi",
        "cp312",
    ]
    for name in target.pip_platforms:
        base.extend(["--platform", name])
    base.extend(["--dest", str(wheels)])
    return base


def filter_requirements_for_target(text: str, target: Target) -> str:
    """Return the locked requirement list without the entries that do not apply to the target.

    `uv export` writes one entry per package, with an optional environment marker and
    indented `--hash` and comment lines below it. The entry stays when it has no marker
    or when the marker is true for the target; a kept entry loses its marker. The shipped
    `requirements.txt` is not changed; the partner machine evaluates the markers there.
    """
    try:
        from packaging.markers import Marker
    except ImportError as error:  # pragma: no cover - depends on the builder environment
        raise BundleError(
            "The wheel download needs the `packaging` module to read the markers.",
            fix=(
                "Run the builder with `uv run --offline --extra bundle` inside the repository "
                "checkout, or use `scripts/build-partner-bundle`."
            ),
        ) from error
    environment = {**_COMMON_MARKERS, **TARGET_MARKERS[target.uv_triple]}
    kept: list[str] = []
    keep = True
    for line in text.splitlines():
        if line and not line[0].isspace() and not line.startswith("#"):
            head = line.removesuffix("\\").rstrip()
            requirement, _sep, marker = head.partition(" ; ")
            keep = not marker or Marker(marker.strip()).evaluate(environment)
            # pip would evaluate a kept marker again on the builder machine and skip the
            # entry. The marker is already true for the target, so the copy drops it.
            if keep and marker:
                line = requirement + (" \\" if line.endswith("\\") else "")
        elif not line.strip() or line.startswith("#"):
            keep = True
        if keep:
            kept.append(line)
    return "\n".join(kept) + "\n"


def _download_wheels(options: BundleOptions, target: Target, bundle: Path, uv: str) -> None:
    """Fetch every locked wheel for the target with `pip download --require-hashes`.

    The lock holds the full closure, so `--no-deps` stops pip from reading the metadata
    of a wheel and pulling an entry for the builder machine (for example `cuda-toolkit`).
    """
    _require_online(options, f"The wheel download for {target.name}")
    wheels = bundle / "wheels"
    wheels.mkdir()
    base = _pip_download_base(target, wheels, uv)
    locked = (bundle / "requirements.txt").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="eureka-bundle-") as scratch:
        filtered = Path(scratch) / "requirements-target.txt"
        filtered.write_text(filter_requirements_for_target(locked, target), encoding="utf-8")
        _run(
            [*base, "--no-deps", "--require-hashes", "--requirement", str(filtered)],
            cwd=options.repo_root,
            what="pip download of the locked wheels",
        )
    backend_base = _pip_download_base(target, wheels, uv, extra_index=False)
    _run(
        [*backend_base, "setuptools>=75", "wheel"],
        cwd=options.repo_root,
        what="pip download of the build backend",
    )


def _model_kind(resolution: models.ModelResolution) -> str:
    if resolution.origin == models.ORIGIN_FLAG:
        return "explicit"
    if resolution.origin == models.ORIGIN_CACHE:
        return "hf-cache"
    return "environment"


def _write_model(options: BundleOptions, bundle: Path) -> str:
    resolution = models.discover_model(options.model_path)
    if resolution.ok and resolution.path is not None:
        shutil.copytree(resolution.path, bundle / "model", symlinks=False)
        return _model_kind(resolution)
    if not options.allow_model_download:
        explicit_given = options.model_path is not None
        print(models.missing_model_message(resolution, explicit_given=explicit_given))
        print("The bundle is written without a model folder.")
        return "absent"
    _download_model(options, bundle)
    return "downloaded"


def _download_model(options: BundleOptions, bundle: Path) -> None:
    """Fetch the model folder with `hf download` (docs/offline-install.md).

    ASSUMED: not run on this machine.
    """
    _require_online(options, "The model download")
    _run(
        [
            "uv",
            "run",
            "hf",
            "download",
            models.MODEL_REPO,
            "--local-dir",
            str(bundle / "model"),
        ],
        cwd=options.repo_root,
        what="hf download",
    )


def _write_python(options: BundleOptions, bundle: Path) -> str:
    if options.python_from is None:
        return "machine"
    destination = bundle / "python" / options.python_from.name
    shutil.copytree(options.python_from, destination, symlinks=True)
    return "bundled"


def _write_files(options: BundleOptions, bundle: Path) -> None:
    repo = options.repo_root
    (bundle / "mapping").mkdir()
    mappings = repo / "examples" / "mappings"
    shutil.copyfile(mappings / MAPPING_FILE, bundle / "mapping" / MAPPING_FILE)
    (bundle / "sidecar").mkdir()
    shutil.copyfile(mappings / SIDECAR_EXAMPLE, bundle / "sidecar" / SIDECAR_EXAMPLE)
    (bundle / "sidecar" / "README.md").write_text(launchers.SIDECAR_README, encoding="utf-8")
    (bundle / "docs").mkdir()
    shutil.copyfile(repo / "docs" / GUIDE_FILE, bundle / "docs" / GUIDE_FILE)


def _write_text(path: Path, text: str, *, executable: bool) -> None:
    filled = text.replace("@PYTHON_SERIES@", launchers.PYTHON_SERIES)
    path.write_text(filled, encoding="utf-8", newline="\n")
    if executable:
        path.chmod(0o755)


def _write_launchers(bundle: Path) -> None:
    _write_text(bundle / "start.sh", launchers.START_SH, executable=True)
    _write_text(bundle / "start.ps1", launchers.START_PS1, executable=False)


def _write_docker(options: BundleOptions, bundle: Path) -> str:
    """Save the local image and write the docker launcher pair.

    ASSUMED: docker is absent on this machine, so this step was not run here.
    """
    image = os.environ.get("MINDRIAN_EUREKA_IMAGE", DEFAULT_IMAGE)
    _run(["docker", "image", "inspect", image], what=f"docker image inspect {image}")
    _run(
        ["docker", "save", image, "-o", str(bundle / "eureka-image.tar")],
        what=f"docker save {image}",
    )
    _write_text(bundle / "start-docker.sh", launchers.START_DOCKER_SH, executable=True)
    _write_text(bundle / "start-docker.ps1", launchers.START_DOCKER_PS1, executable=False)
    return image


def _list_files(bundle: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for root, dirs, files in os.walk(bundle):
        dirs.sort()
        for name in files:
            path = Path(root) / name
            relative = path.relative_to(bundle).as_posix()
            if relative == MANIFEST_NAME:
                continue
            entries.append(
                {"path": relative, "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            )
    entries.sort(key=lambda entry: entry["path"])
    return entries


def write_manifest(
    bundle: Path, *, target: Target, source_commit: str, builder: dict[str, Any]
) -> str:
    """Write `BUNDLE-MANIFEST.json` last and return its sha256.

    Args:
        bundle: The bundle folder.
        target: The resolved target.
        source_commit: The git commit of the source folder.
        builder: The builder inputs block. It holds no absolute path.

    Returns:
        The sha256 of the manifest file.
    """
    document = {
        "schema": MANIFEST_SCHEMA,
        "label": LABEL,
        "target": target.name,
        "engine_version": str(__version__),
        "source_commit": source_commit,
        "built_at": _dt.datetime.now(_dt.UTC).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        ),
        "builder": builder,
        "files": _list_files(bundle),
    }
    text = json.dumps(document, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    path = bundle / MANIFEST_NAME
    path.write_text(text, encoding="utf-8")
    return sha256_file(path)


def build_bundle(options: BundleOptions) -> BundleReport:
    """Write `<out_dir>/eureka-partner-bundle-<target>` and return the report.

    Args:
        options: The builder inputs.

    Returns:
        The report with the bundle folder, the file count and the manifest sha256.

    Raises:
        BundleError: A precondition failed, or a step failed. Nothing is written when a
            precondition fails.
    """
    target = resolve_target(options.target)
    uv = _check_preconditions(options, target)
    bundle = _make_bundle_dir(options, target)
    source_commit = _write_source(options, bundle)
    _write_requirements(options, bundle, uv)
    _write_uv(options, target, bundle, uv)
    wheels = _write_wheels(options, target, bundle, uv)
    model = _write_model(options, bundle)
    python = _write_python(options, bundle)
    _write_files(options, bundle)
    _write_launchers(bundle)
    docker_image: str | None = None
    if options.docker:
        docker_image = _write_docker(options, bundle)
    builder: dict[str, Any] = {
        "host": host_name(),
        "uv_version": _uv_version(uv),
        "python_version": platform.python_version(),
        "online": bool(options.online),
        "wheels": wheels,
        "model": model,
        "python": python,
        "docker": bool(options.docker),
    }
    if docker_image is not None:
        builder["docker_image"] = docker_image
    manifest_sha256 = write_manifest(
        bundle, target=target, source_commit=source_commit, builder=builder
    )
    file_count = len(_list_files(bundle))
    return BundleReport(bundle, target.name, file_count, manifest_sha256, builder)


# --- command line -----------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="build-partner-bundle",
        description=(
            "Write one carry-in folder for a partner machine. Offline by default; "
            "--online is needed for a target other than host."
        ),
    )
    parser.add_argument("--target", required=True, choices=ACCEPTED_NAMES)
    parser.add_argument("--out", default=DEFAULT_OUT, metavar="DIR")
    parser.add_argument("--online", action="store_true", help="allow network in the download steps")
    parser.add_argument("--wheels", choices=("download", "skip"), default="download")
    parser.add_argument("--model-path", metavar="DIR", help="local model folder to copy")
    parser.add_argument(
        "--allow-model-download",
        action="store_true",
        help="fetch the model when none is found (needs --online)",
    )
    parser.add_argument("--python-from", metavar="DIR", help="managed Python folder to copy")
    parser.add_argument("--docker", action="store_true", help="also write the docker variant")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the builder from the command line.

    Args:
        argv: The arguments after the program name. None means `sys.argv[1:]`.

    Returns:
        0 on success, 2 on a build error.
    """
    args = _parser().parse_args(argv)
    try:
        options = BundleOptions(
            target=args.target,
            out_dir=Path(args.out),
            online=args.online,
            wheels=args.wheels,
            model_path=Path(args.model_path) if args.model_path else None,
            allow_model_download=args.allow_model_download,
            python_from=Path(args.python_from) if args.python_from else None,
            docker=args.docker,
        )
        report = build_bundle(options)
    except BundleError as error:
        print(f"error: {error.message}", file=sys.stderr)
        if error.fix:
            print(f"fix: {error.fix}", file=sys.stderr)
        return error.exit_code
    print(f"bundle: {report.bundle_dir}")
    print(f"files: {report.file_count}")
    print(f"manifest sha256: {report.manifest_sha256}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
