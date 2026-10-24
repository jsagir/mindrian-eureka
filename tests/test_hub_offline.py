"""Prove every static network control with positive and negative fixtures."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from hub_scan import scan_dashes, scan_for_network, scan_internal_names
from hub_support import make_run_folder
from mindrian_eureka.hub import assets
from mindrian_eureka.hub.writer import HubRequest, build_hub
from mindrian_eureka.run.console import Console


@pytest.mark.parametrize("hostile", [False, True])
def test_written_hub_is_offline(tmp_path: Path, no_network: list[object], hostile: bool) -> None:
    run = make_run_folder(tmp_path, hostile=hostile)
    out = tmp_path / "hub"
    build_hub(HubRequest(run, out), Console(stderr=io.StringIO()))
    assert scan_for_network(out) == []
    assert scan_dashes(out) == []
    assert scan_internal_names(out) == []
    assert no_network == []


@pytest.mark.parametrize("name,text", [
    ("bad.html", '<img src="http://host/x">'),
    ("bad.html", '<link rel="preconnect" href="./local">'),
    ("bad.css", '@import url(https://host/x);'),
    ("bad.css", 'a{background:url(//host/x)}'),
    ("bad.js", 'fetch("./x")'),
    ("bad.js", 'new XMLHttpRequest()'),
    ("bad.js", 'new WebSocket("./x")'),
    ("bad.js", 'navigator.sendBeacon("./x")'),
    ("bad.js", 'const url="https://host/x"'),
    ("bad.js", 'import("https://host/x")'),
    ("bad.js", 'new EventSource("./x")'),
    ("bad.js", 'importScripts("./x")'),
    ("bad.js", 'navigator.serviceWorker.register("./x")'),
    ("bad.html", '<meta http-equiv="refresh" content="0;url=./x">'),
    ("bad.html", '<img srcset="./safe 1x, https://host/x 2x">'),
    ("bad.svg", '<image href="https://host/x"/>'),
    ("unknown.blob", 'https://host/x'),
])
def test_negative_network_control(tmp_path: Path, name: str, text: str) -> None:
    path = tmp_path / name
    path.write_text(text)
    assert scan_for_network(tmp_path)


def test_namespace_and_vendor_skip(tmp_path: Path) -> None:
    (tmp_path / "safe.js").write_text('const ns="http://www.w3.org/2000/svg";')
    vendor = tmp_path / "vendor"
    vendor.mkdir()
    (vendor / "bundle.js").write_text('fetch("https://host/x")')
    assert scan_for_network(tmp_path) == []
    js = [asset.output_path for asset in assets.all_assets() if asset.output_path.endswith(".js")]
    assert [name for name in js if name.startswith("vendor/")] == ["vendor/3d-force-graph.min.js"]
    (tmp_path / "safe.js").write_text('fetch("./x")')
    assert scan_for_network(tmp_path) == ["safe.js: remote URL or network API"]


@pytest.mark.parametrize("scanner,text", [
    (scan_dashes, "bad" + chr(0x2014) + "copy"),
    (scan_internal_names, "R" + "S"),
])
def test_copy_negative_control(tmp_path: Path, scanner, text: str) -> None:
    (tmp_path / "hub.html").write_text(text)
    assert scanner(tmp_path) == ["hub.html"]
