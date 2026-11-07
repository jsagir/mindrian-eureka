"""Tests of the carry-in bundle builder (Phase 2.2, D-07).

The host bundle is built once per session, offline, with the wheel step skipped.
Nothing in this file touches the network. The 3 D-07 targets are not built here.
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
from mindrian_eureka import models
from mindrian_eureka.partner_bundle import builder
from mindrian_eureka.partner_bundle.builder import (
    MACOS_ARM64_PIP_PLATFORMS,
    PYTORCH_CPU_INDEX,
    TARGETS,
    BundleError,
    BundleOptions,
    BundleReport,
    _pip_download_base,
    build_bundle,
    resolve_target,
)
from mindrian_eureka.run.contracts import LABEL
from mindrian_eureka.run.manifest import sha256_file

REPO = Path(__file__).resolve().parents[1]
D07_NAMES = ("linux-x86_64", "windows-x86_64", "macos-arm64")


def _git(*args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(REPO), *args], check=True, capture_output=True, text=True
    )
    return done.stdout.strip()


def _host_name() -> str:
    machine = platform.machine().lower()
    if machine in {"aarch64", "arm64"}:
        machine = "aarch64"
    elif machine in {"x86_64", "amd64"}:
        machine = "x86_64"
    return f"{platform.system().lower()}-{machine}"


def _files_under(folder: Path) -> set[str]:
    found: set[str] = set()
    for root, _dirs, files in os.walk(folder):
        for name in files:
            found.add((Path(root) / name).relative_to(folder).as_posix())
    return found


@pytest.fixture(scope="session")
def host_report(tmp_path_factory: pytest.TempPathFactory) -> BundleReport:
    out = tmp_path_factory.mktemp("bundle")
    resolution = models.discover_model(None)
    model_path = resolution.path if resolution.ok else None
    options = BundleOptions(
        target="host", out_dir=out, online=False, wheels="skip", model_path=model_path
    )
    return build_bundle(options)


@pytest.fixture(scope="session")
def host_bundle(host_report: BundleReport) -> Path:
    return host_report.bundle_dir


@pytest.fixture(scope="session")
def manifest(host_bundle: Path) -> dict:
    return json.loads((host_bundle / "BUNDLE-MANIFEST.json").read_text(encoding="utf-8"))


# --- targets ------------------------------------------------------------------


def test_targets_and_host_alias() -> None:
    assert set(D07_NAMES) <= set(TARGETS)
    assert TARGETS["linux-x86_64"].uv_triple == "x86_64-unknown-linux-gnu"
    assert TARGETS["linux-x86_64"].archive == "tar.gz"
    assert TARGETS["linux-x86_64"].python_platform == "x86_64-manylinux_2_28"
    assert TARGETS["linux-x86_64"].pip_platforms == (
        "manylinux_2_28_x86_64",
        "manylinux2014_x86_64",
    )
    assert TARGETS["linux-x86_64"].python_key == "cpython-3.12-linux-x86_64-gnu"
    assert TARGETS["linux-x86_64"].launcher == "sh"
    assert TARGETS["windows-x86_64"].uv_triple == "x86_64-pc-windows-msvc"
    assert TARGETS["windows-x86_64"].archive == "zip"
    assert TARGETS["windows-x86_64"].python_platform == "x86_64-pc-windows-msvc"
    assert TARGETS["windows-x86_64"].pip_platforms == ("win_amd64",)
    assert TARGETS["windows-x86_64"].python_key == "cpython-3.12-windows-x86_64-none"
    assert TARGETS["windows-x86_64"].launcher == "ps1"
    assert TARGETS["macos-arm64"].uv_triple == "aarch64-apple-darwin"
    assert TARGETS["macos-arm64"].archive == "tar.gz"
    assert TARGETS["macos-arm64"].python_platform == "aarch64-apple-darwin"
    assert TARGETS["macos-arm64"].pip_platforms == MACOS_ARM64_PIP_PLATFORMS
    assert TARGETS["macos-arm64"].python_key == "cpython-3.12-macos-aarch64-none"
    assert TARGETS["macos-arm64"].launcher == "sh"
    for name in D07_NAMES:
        assert resolve_target(name) is TARGETS[name]

    host = resolve_target("host")
    assert host.name == _host_name()
    if host.name == "linux-aarch64":
        assert host.uv_triple == "aarch64-unknown-linux-gnu"
        assert host.python_platform == "aarch64-manylinux_2_28"
        assert host.pip_platforms == ("manylinux_2_28_aarch64", "manylinux2014_aarch64")

    with pytest.raises(BundleError) as caught:
        resolve_target("zzother")
    for name in (*D07_NAMES, "host"):
        assert name in caught.value.message
    assert caught.value.exit_code == 2


@pytest.mark.parametrize("name", D07_NAMES)
def test_pip_download_args_carry_the_extra_index(name: str, tmp_path: Path) -> None:
    args = _pip_download_base(TARGETS[name], tmp_path / "wheels", "uv")
    assert PYTORCH_CPU_INDEX == "https://download.pytorch.org/whl/cpu"
    assert args.count("--extra-index-url") == 1
    assert args[args.index("--extra-index-url") + 1] == PYTORCH_CPU_INDEX
    # PyPI stays the default index: no `--index-url` and no `--no-index`.
    assert "--index-url" not in args
    assert "--no-index" not in args
    assert "--only-binary=:all:" in args
    platforms = [args[i + 1] for i, a in enumerate(args) if a == "--platform"]
    assert tuple(platforms) == TARGETS[name].pip_platforms


def test_macos_arm64_tags_reach_the_highest_lock_tag(tmp_path: Path) -> None:
    lock = (REPO / "uv.lock").read_text(encoding="utf-8")
    found = {int(m.group(1)) for m in re.finditer(r"macosx_(\d+)_0_arm64", lock)}
    assert found
    tags = TARGETS["macos-arm64"].pip_platforms
    for n in range(11, max(found) + 1):
        assert f"macosx_{n}_0_arm64" in tags
    assert "macosx_10_9_universal2" in tags
    args = _pip_download_base(TARGETS["macos-arm64"], tmp_path, "uv")
    assert [args[i + 1] for i, a in enumerate(args) if a == "--platform"] == list(tags)


def test_hashes_in_requirements_are_not_changed(host_bundle: Path, tmp_path: Path) -> None:
    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv is not on PATH")
    expected = tmp_path / "expected.txt"
    subprocess.run(
        [
            uv,
            "export",
            "--frozen",
            "--no-dev",
            "--no-emit-project",
            "--format",
            "requirements-txt",
            "--offline",
            "--extra",
            "modern-encoder",
            "--extra",
            "hub-gate",
            "-o",
            str(expected),
        ],
        cwd=REPO,
        check=True,
        capture_output=True,
    )
    built = (host_bundle / "requirements.txt").read_text(encoding="utf-8")
    hashes = {line.strip(" \\") for line in built.splitlines() if "--hash=sha256:" in line}
    want = {
        line.strip(" \\")
        for line in expected.read_text(encoding="utf-8").splitlines()
        if "--hash=sha256:" in line
    }
    assert hashes
    assert hashes == want


def test_wheel_download_keeps_require_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], **_kwargs: object) -> object:
        calls.append(list(args))
        return None

    monkeypatch.setattr(builder, "_run", fake_run)
    monkeypatch.setattr(builder, "_require_online", lambda *_a, **_k: None)
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    options = BundleOptions(target="macos-arm64", out_dir=tmp_path, online=True, repo_root=REPO)
    builder._download_wheels(options, TARGETS["macos-arm64"], bundle, "uv")
    assert len(calls) == 2
    assert "--require-hashes" in calls[0]
    assert "--requirement" in calls[0]
    assert all("--extra-index-url" in call for call in calls)


def test_other_targets_refuse_offline(tmp_path: Path) -> None:
    out = tmp_path / "out"
    options = BundleOptions(target="windows-x86_64", out_dir=out, online=False)
    with pytest.raises(BundleError) as caught:
        build_bundle(options)
    assert "--online" in caught.value.message or "--online" in str(caught.value.fix)
    assert not out.exists() or not any(out.iterdir())


def test_docker_refused_when_absent(tmp_path: Path) -> None:
    if shutil.which("docker") is not None:
        pytest.skip("docker is on PATH; the refusal cannot be tested here")
    out = tmp_path / "out"
    options = BundleOptions(target="host", out_dir=out, wheels="skip", docker=True)
    with pytest.raises(BundleError) as caught:
        build_bundle(options)
    assert "docker" in caught.value.message
    assert not out.exists() or not any(out.iterdir())


def test_existing_bundle_folder_is_refused(tmp_path: Path) -> None:
    out = tmp_path / "out"
    taken = out / f"eureka-partner-bundle-{_host_name()}"
    taken.mkdir(parents=True)
    (taken / "left-over.txt").write_text("x", encoding="utf-8")
    options = BundleOptions(target="host", out_dir=out, wheels="skip")
    with pytest.raises(BundleError) as caught:
        build_bundle(options)
    assert "not empty" in caught.value.message
    assert (taken / "left-over.txt").read_text(encoding="utf-8") == "x"


# --- the host bundle ----------------------------------------------------------


def test_host_bundle_folder_and_uv(host_bundle: Path, host_report: BundleReport) -> None:
    assert host_bundle.name == f"eureka-partner-bundle-{_host_name()}"
    assert host_report.target == _host_name()
    system_uv = shutil.which("uv")
    assert system_uv is not None
    bundled = host_bundle / "uv"
    assert bundled.read_bytes() == Path(system_uv).read_bytes()
    assert bundled.stat().st_mode & stat.S_IXUSR


def test_host_bundle_source_requirements_and_files(host_bundle: Path) -> None:
    for relative in (
        "source/pyproject.toml",
        "source/uv.lock",
        "source/src/mindrian_eureka/cli.py",
        "source/docs/offline-install.md",
    ):
        assert (host_bundle / relative).is_file(), relative
    requirements = (host_bundle / "requirements.txt").read_text(encoding="utf-8")
    assert "sentence-transformers==" in requirements
    assert "--hash=sha256:" in requirements
    mapping = host_bundle / "mapping" / "technology-audit-export.json"
    assert (
        mapping.read_bytes()
        == (REPO / "examples" / "mappings" / "technology-audit-export.json").read_bytes()
    )
    example = host_bundle / "sidecar" / "text-sidecar.example.csv"
    assert (
        example.read_bytes()
        == (REPO / "examples" / "mappings" / "text-sidecar.example.csv").read_bytes()
    )
    guide = host_bundle / "docs" / "partner-run-guide.md"
    assert guide.read_bytes() == (REPO / "docs" / "partner-run-guide.md").read_bytes()


def test_host_bundle_wheels_skipped_and_model_rule(
    host_bundle: Path, host_report: BundleReport, manifest: dict
) -> None:
    assert not (host_bundle / "wheels").exists()
    assert manifest["builder"]["wheels"] == "skipped"
    assert host_report.builder["wheels"] == "skipped"
    if models.discover_model(None).ok:
        assert (host_bundle / "model" / "config.json").is_file()
        assert not (host_bundle / "model" / "config.json").is_symlink()
        assert manifest["builder"]["model"] == "explicit"
    else:
        assert not (host_bundle / "model").exists()
        assert manifest["builder"]["model"] == "absent"
    assert manifest["builder"]["python"] == "machine"
    assert not (host_bundle / "python").exists()


def test_manifest_hashes_sizes_and_paths(
    host_bundle: Path, host_report: BundleReport, manifest: dict, tmp_path: Path
) -> None:
    text = (host_bundle / "BUNDLE-MANIFEST.json").read_text(encoding="utf-8")
    assert str(host_bundle) not in text
    assert str(tmp_path.parent) not in text
    assert "/home/" not in text
    assert manifest["schema"] == "eureka.partner-bundle.v1"
    assert manifest["label"] == LABEL
    assert manifest["target"] == _host_name()
    assert manifest["engine_version"] == "0.1.0"
    assert manifest["source_commit"] == _git("rev-parse", "HEAD")
    assert manifest["built_at"].endswith("Z")
    builder = manifest["builder"]
    assert builder["online"] is False
    assert builder["docker"] is False
    assert builder["uv_version"]
    assert builder["python_version"]
    assert builder["host"] == _host_name()

    files = manifest["files"]
    paths = [entry["path"] for entry in files]
    assert paths == sorted(paths)
    assert "BUNDLE-MANIFEST.json" not in paths
    assert set(paths) == _files_under(host_bundle) - {"BUNDLE-MANIFEST.json"}
    for entry in files:
        target = host_bundle / entry["path"]
        assert entry["sha256"] == sha256_file(target), entry["path"]
        assert entry["bytes"] == target.stat().st_size, entry["path"]
        assert not entry["path"].startswith("/")
    assert host_report.file_count == len(files)
    assert host_report.manifest_sha256 == sha256_file(host_bundle / "BUNDLE-MANIFEST.json")


# --- launchers ----------------------------------------------------------------

NETWORK_WORDS = ("curl", "wget", "http://", "https://", "Invoke-WebRequest")


def _dry_run(bundle: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(bundle / "start.sh"), *args, "--dry-run"],
        cwd=bundle,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _in_order(text: str, needles: tuple[str, ...]) -> None:
    position = 0
    for needle in needles:
        found = text.find(needle, position)
        assert found >= 0, f"{needle!r} missing after position {position}"
        position = found + len(needle)


def test_bundle_holds_launchers_and_sidecar_readme(host_bundle: Path) -> None:
    start_sh = host_bundle / "start.sh"
    assert start_sh.is_file()
    assert start_sh.stat().st_mode & stat.S_IXUSR
    assert (host_bundle / "start.ps1").is_file()
    readme = (host_bundle / "sidecar" / "README.md").read_text(encoding="utf-8")
    lines = [line for line in readme.splitlines() if line.strip()]
    assert 8 <= len(lines) <= 12
    assert "text" in readme
    assert LABEL not in readme
    assert not (host_bundle / "start-docker.sh").exists()
    assert not (host_bundle / "eureka-image.tar").exists()


def test_start_sh_dry_run(host_bundle: Path) -> None:
    done = _dry_run(host_bundle)
    assert done.returncode == 0, done.stderr
    _in_order(
        done.stdout,
        (
            "would run:",
            "uv sync --offline",
            "would run:",
            "eureka doctor",
            "would run:",
            "eureka run",
            "--mapping",
            "technology-audit-export.json",
            "would run:",
            "eureka hub",
            "hub.html",
        ),
    )
    assert "--text-sidecar" not in done.stdout
    assert not (host_bundle / "source" / ".venv").exists()
    assert not (host_bundle / "output").exists()
    assert not (host_bundle.parent / "output").exists()
    assert not (host_bundle / ".uv-cache").exists()


def test_start_sh_dry_run_with_a_dropped_sidecar(host_bundle: Path) -> None:
    dropped = host_bundle / "sidecar" / "partner.csv"
    dropped.write_text("case_number,text\nC00001,A synthetic sentence for the test.\n")
    try:
        done = _dry_run(host_bundle)
    finally:
        dropped.unlink()
    assert done.returncode == 0, done.stderr
    assert "--text-sidecar" in done.stdout
    assert "partner.csv" in done.stdout


def test_start_sh_dry_run_takes_input_and_output_folders(host_bundle: Path, tmp_path: Path) -> None:
    done = _dry_run(host_bundle, str(tmp_path / "in"), str(tmp_path / "out"))
    assert done.returncode == 0, done.stderr
    assert str(tmp_path / "in") in done.stdout
    assert str(tmp_path / "out") + "-hub" in done.stdout
    assert not (tmp_path / "out").exists()


def test_launchers_make_no_network_call(host_bundle: Path) -> None:
    names = ("start.sh", "start.ps1", "start-docker.sh", "start-docker.ps1")
    for name in names:
        path = host_bundle / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for word in NETWORK_WORDS:
            assert word not in text, f"{name} holds {word!r}"


def test_start_ps1_has_the_same_sequence(host_bundle: Path) -> None:
    text = (host_bundle / "start.ps1").read_text(encoding="utf-8")
    for needle in (
        "eureka doctor",
        "eureka run",
        "--out",
        "--mapping",
        "technology-audit-export.json",
        "eureka hub",
        "Start-Process",
        "DryRun",
        "LASTEXITCODE",
        "UV_OFFLINE",
        "HF_HUB_OFFLINE",
    ):
        assert needle in text, needle
    assert "--output " not in text


def test_doctor_runs_from_inside_the_bundle(host_bundle: Path, tmp_path: Path) -> None:
    if not models.discover_model(None).ok:
        pytest.skip("local model absent")
    env = dict(os.environ)
    env["PATH"] = f"{host_bundle}{os.pathsep}{env.get('PATH', '')}"
    env["UV_PROJECT_ENVIRONMENT"] = str(tmp_path / "venv")
    env["UV_PYTHON"] = "3.12"
    env.pop("VIRTUAL_ENV", None)
    env["UV_OFFLINE"] = "1"
    env["UV_NO_PROGRESS"] = "1"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env.pop("MINDRIAN_EUREKA_RS_MODEL_PATH", None)
    env.pop("MINDRIAN_EUREKA_HSI_MODEL_PATH", None)
    source = host_bundle / "source"
    synced = subprocess.run(
        ["uv", "sync", "--offline", "--extra", "modern-encoder"],
        cwd=source,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert synced.returncode == 0, synced.stderr.strip().splitlines()[:3]
    done = subprocess.run(
        [
            "uv",
            "run",
            "--offline",
            "eureka",
            "doctor",
            "--json",
            "--model-path",
            str(host_bundle / "model"),
        ],
        cwd=source,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    report = json.loads(done.stdout)
    statuses = {check["id"]: check["status"] for check in report["checks"]}
    assert statuses["D2"] == "PASS", report
    assert statuses["D4"] == "PASS", report
    assert done.returncode == 0, report
    assert report["ok"] is True
    assert not (source / ".venv").exists()
