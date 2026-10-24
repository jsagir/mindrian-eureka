"""Check every asset byte and its packaging provenance."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import pytest
from mindrian_eureka.hub import assets


@pytest.mark.parametrize("name,digest", sorted(assets.EXPECTED_STATIC.items()))
def test_static_asset_hash(name: str, digest: str) -> None:
    assert hashlib.sha256((assets.ASSETS_ROOT / "static" / name).read_bytes()).hexdigest() == digest


def test_static_file_table_is_complete() -> None:
    folder = assets.ASSETS_ROOT / "static"
    actual = {path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file()}
    assert actual == set(assets.EXPECTED_STATIC)
    assert set(assets.BOOK_SOURCES) == actual


@pytest.mark.parametrize("name,source", sorted(assets.BOOK_SOURCES.items()))
def test_book_source_is_byte_identical(name: str, source: str) -> None:
    if source.startswith("npm:"):
        return
    book = Path(os.environ.get("MOS_BRAND_BOOK", str(Path.home() / "mos-brand")))
    if not book.is_dir():
        pytest.skip("The canonical mos-brand checkout is unavailable")
    assert (assets.ASSETS_ROOT / "static" / name).read_bytes() == (book / source).read_bytes()


def test_font_files_licenses_and_token_urls_exist() -> None:
    folder = assets.ASSETS_ROOT / "static"
    tokens = (folder / "tokens.css").read_text()
    fonts = re.findall(r"url\(['\"]?(\./assets/fonts/[^)'\"]+)", tokens)
    assert len(fonts) == 4
    assert all((folder / font).is_file() for font in fonts)
    for stem in ("figtree", "dmsans", "jetbrainsmono", "heebo"):
        assert "SIL OPEN FONT LICENSE" in (folder / f"assets/fonts/{stem}-OFL.txt").read_text()


def test_exact_lockup_and_distinct_theo_faces() -> None:
    folder = assets.ASSETS_ROOT / "static"
    assert (folder / "assets/brand/mos-lockup-paper-v2.svg").is_file()
    faces = [
        (folder / f"assets/faces/theo-{name}.svg").read_bytes()
        for name in ("handover", "limit", "boundary", "rest")
    ]
    assert len(set(faces)) == 4
    for suffix in ("svg", "16.png", "32.png", "48.png", "180.png"):
        name = "favicon.svg" if suffix == "svg" else f"favicon-{suffix}"
        assert (folder / "assets" / name).is_file()


def test_canonical_assets_have_no_remote_loads() -> None:
    remote = re.compile(rb"(?:href|src)\s*=\s*['\"]\s*https?:|url\(\s*['\"]?\s*https?:", re.I)
    for asset in assets.static_assets():
        if not asset.output_path.startswith("vendor/"):
            assert not remote.search(asset.package_path.read_bytes()), asset.output_path


def test_authored_assets_missing_folder_is_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(assets, "ASSETS_ROOT", tmp_path)
    assert assets.authored_assets() == ()


def test_authored_assets_are_sorted_and_have_no_static_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "authored"
    folder.mkdir()
    (folder / "z.js").write_text("z")
    (folder / "a.css").write_text("a")
    monkeypatch.setattr(assets, "ASSETS_ROOT", tmp_path)
    result = assets.authored_assets()
    assert [item.output_path for item in result] == ["a.css", "z.js"]
    assert all(item.sha256 is None for item in result)


def test_combined_assets_are_unique_and_static_first() -> None:
    result = assets.all_assets()
    names = [item.output_path for item in result]
    assert len(set(names)) == len(names)
    assert result[: len(assets.EXPECTED_STATIC)] == assets.static_assets()


def test_shadowing_a_canonical_file_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = tmp_path / "authored"
    folder.mkdir()
    (folder / "tokens.css").write_text("changed")
    monkeypatch.setattr(assets, "ASSETS_ROOT", tmp_path)
    with pytest.raises(ValueError, match="duplicate output paths"):
        assets.all_assets()


def test_vendor_library_and_notices_are_packaged() -> None:
    folder = assets.ASSETS_ROOT / "static/vendor"
    assert (folder / "LICENSE-3d-force-graph.txt").read_text().startswith("MIT License")
    notices = (folder / "NOTICES.txt").read_text()
    assert "Direct dependency license metadata" in notices
    assert "BSD-3-Clause" in notices and "ISC" in notices
    assert "ForceGraph3D" in (folder / "3d-force-graph.min.js").read_text()


def test_package_data_covers_assets_and_optional_gate() -> None:
    import tomllib

    project = Path(__file__).resolve().parents[1]
    config = tomllib.loads((project / "pyproject.toml").read_text())
    patterns = config["tool"]["setuptools"]["package-data"]["mindrian_eureka"]
    package = project / "src/mindrian_eureka"
    matched = {path for pattern in patterns for path in package.glob(pattern) if path.is_file()}
    assert all(item.package_path in matched for item in assets.static_assets())
    assert "hub/assets/authored/*" in patterns
    assert config["project"]["optional-dependencies"]["hub-gate"] == ["cryptography>=44,<51"]
    assert config["project"]["dependencies"] == [
        "jsonschema>=4.20,<5",
        "numpy>=2.0,<3",
        "scikit-learn>=1.6,<2",
    ]


def test_wheel_contains_tokens_and_vendor_bundle(tmp_path: Path) -> None:
    import importlib.util
    import subprocess
    import sys
    import zipfile

    if not all(importlib.util.find_spec(name) for name in ("setuptools", "wheel")):
        pytest.skip("setuptools and wheel are required for the offline wheel check")
    project = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-deps",
            "--no-build-isolation",
            "--no-index",
            "-w",
            str(tmp_path),
        ],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    wheels = list(tmp_path.glob("*.whl"))
    assert len(wheels) == 1
    with zipfile.ZipFile(wheels[0]) as wheel:
        names = set(wheel.namelist())
    assert "mindrian_eureka/hub/assets/static/tokens.css" in names
    assert "mindrian_eureka/hub/assets/static/vendor/3d-force-graph.min.js" in names


def test_static_assets_do_not_include_local_paths() -> None:
    for asset in assets.static_assets():
        data = asset.package_path.read_bytes()
        assert str(Path.home()).encode() not in data
        assert str(Path.cwd()).encode() not in data
