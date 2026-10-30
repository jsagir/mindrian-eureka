"""Prove public-data review routes and keep synthetic marked records test-only."""

from __future__ import annotations

import io
import json
from pathlib import Path
from urllib.parse import unquote

import pytest
from hub_browser_support import require_browser
from hub_scan import scan_dashes, scan_for_network, scan_internal_names
from hub_support import tree_hash
from mindrian_eureka.hub.deck import DECK
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.hub.verify import verify_payload
from mindrian_eureka.hub.writer import HubRequest, build_hub
from mindrian_eureka.run.console import Console
from mindrian_eureka.run.contracts import LABEL
from test_hub_browser_core import CHECKS, scenario
from test_hub_browser_graph import positive_hub

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "tests/fixtures/hub_public"
STAGE = str(CHECKS / "stage-state.js")


def build(tmp_path: Path, name: str, *, source=False, password=None) -> Path:
    out = tmp_path / name
    build_hub(HubRequest(PUBLIC / "run", out, PUBLIC / "input" if source else None,
                         password=password), Console(stderr=io.StringIO()))
    return out


def payload(out: Path):
    text = (out / "hub-data.js").read_text().strip()
    assert text.startswith("window.HUB = ") and text.endswith(";")
    return json.loads(text.removeprefix("window.HUB = ").removesuffix(";"))


def test_public_default_and_source_links_deterministic_offline(tmp_path: Path) -> None:
    first, second = build(tmp_path, "one"), build(tmp_path, "two")
    assert tree_hash(first) == tree_hash(second)
    data = payload(first)
    expected = build_payload(load_run(PUBLIC / "run"))
    assert verify_payload(data) == []
    assert data["counts"] == expected["counts"]
    assert data["counts"]["records"] == 36
    assert data["counts"]["pairs"] == {"unusual_pairs": 63, "wording_and_meaning": 200}
    assert data["graph"]["earned"] and data["bridges"] == []
    assert all(record["source_link"].startswith("#") for record in data["records"])
    html = (first / "hub.html").read_text()
    assert [html.index(f'id="{name}"') for name in ("bank", "graph", "catalogue")] == sorted(
        html.index(f'id="{name}"') for name in ("bank", "graph", "catalogue"))
    linked = build(tmp_path, "linked", source=True)
    for record in payload(linked)["records"]:
        assert record["file_link"] == record["source_link"]
        assert (linked / unquote(record["source_link"])).is_file()
    for folder in (first, second, linked):
        assert scan_for_network(folder) == []
        assert scan_dashes(folder) == []
        assert scan_internal_names(folder) == []


def test_public_views_and_leading_pair_panels(tmp_path: Path) -> None:
    require_browser()
    out = build(tmp_path, "hub")
    script = tmp_path / "review.js"
    script.write_text('''
const app=HubApp;
app.go('bank',{focus:false});
const engines=Array.from(document.querySelectorAll('#bank-list [data-engine]'))
  .map(n=>n.dataset.engine);
const panels=[];
const pairs=app.data.pairs.slice().sort((a,b)=>a.rank-b.rank||a.engine.localeCompare(b.engine));
for(const pair of pairs.slice(0,16)) {
  app.select({type:'pair',key:pair.key});
  const panel=document.getElementById('hub-panel');
  const sources=Array.from(panel.querySelectorAll('a')).map(n=>n.getAttribute('href'));
  panels.push({label:panel.textContent.includes(app.data.label),
    sources:[pair.left.source_link,pair.right.source_link].every(href=>sources.includes(href))});
}
app.clearSelection(); app.go('catalogue',{focus:false});
for(let i=0;i<Math.ceil(app.data.records.length/app.data.config.catalogue_page);i++){
  const more=document.getElementById('catalogue-more');
  if(!more||more.hidden) break;
  more.click();
}
const rows=Array.from(document.querySelectorAll('#catalogue-list tbody tr'));
return {engines,panels,rows:rows.length,
  sources:rows.every(row=>Boolean(row.querySelector('a[href]')))};
''')
    state = scenario(out, steps=[{"kind": "eval", "file": str(script), "as": "views"},
                                {"kind": "eval", "file": STAGE, "as": "graph"}])
    assert set(state["views"]["engines"]) == {"unusual_pairs", "wording_and_meaning"}
    assert len(state["views"]["panels"]) == 16
    assert all(panel["label"] and panel["sources"] for panel in state["views"]["panels"])
    assert state["views"]["rows"] == 36 and state["views"]["sources"]
    assert state["graph"]["mode"] == "3d" and state["graph"]["expectedLinks"] == 263
    none = scenario(out, steps=[
        {"kind": "eval", "file": STAGE, "as": "graph"},
        {"kind": "eval", "file": str(CHECKS / "graph-state.js"), "as": "none"}])["none"]
    assert none["bridges"] == [] and none["tourHidden"]
    assert none["tourEmpty"] == {"visible": True, "text": DECK["Gr09"]}


def test_public_locked_build_unlocks_same_views(tmp_path: Path) -> None:
    require_browser()
    pytest.importorskip("cryptography")
    password = "synthetic public example test passphrase"
    out = build(tmp_path, "locked", password=password)
    script = tmp_path / "locked-views.js"
    script.write_text("return ['bank','graph','catalogue'].map(name=>{"
                      "HubApp.go(name,{focus:false});"
                      "const node=document.getElementById(name);"
                      "const visible=Boolean(node.getClientRects().length);"
                      "return {name,visible};});")
    state = scenario(out, steps=[
        {"kind": "fill", "selector": "#hub-passphrase", "value": password},
        {"kind": "press", "selector": "#hub-passphrase", "key": "Enter"},
        {"kind": "eval", "file": str(CHECKS / "gate-state.js"), "as": "unlocked",
         "args": {"wait": "unlocked"}},
        {"kind": "eval", "file": STAGE, "as": "graph"},
        {"kind": "eval", "file": str(script), "as": "views"}])
    assert state["unlocked"]["schema"] == "eureka.hub-data.v1"
    assert state["unlocked"]["count"] == 36 and not state["unlocked"]["locked"]
    assert state["graph"]["mode"] == "3d" and state["graph"]["expectedNodes"] == 36
    assert state["views"] == [{"name": name, "visible": True}
                              for name in ("bank", "graph", "catalogue")]


def test_synthetic_marked_routes_are_separate_from_public(tmp_path: Path) -> None:
    require_browser()
    out = positive_hub(tmp_path)
    state = scenario(out, steps=[{"kind": "eval", "file": STAGE, "as": "stage"},
        {"kind": "eval", "file": str(CHECKS / "graph-state.js"), "as": "tour",
         "args": {"tour": 2}}])
    marked = [node for node in state["stage"]["nodes"] if node["bridge"]]
    assert len(marked) == 2 and all(node["shell"]["color"] == "111111" for node in marked)
    assert len(state["stage"]["chips"]) == 2
    assert all(chip["status"] == LABEL and chip["source"] for chip in state["stage"]["chips"])
    assert [stop["selection"]["id"] for stop in state["tour"]["tourStates"]] == [
        "synthetic-b-000", "synthetic-z-connector"]
    assert all(DECK["P03.why"] in stop["panel"] and LABEL in stop["panel"]
               for stop in state["tour"]["tourStates"])
