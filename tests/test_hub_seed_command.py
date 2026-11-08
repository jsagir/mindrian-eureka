"""Tests for the seed command row in the hub (Phase 2.3, plan 04, D-04 and SEED-05).

Every test builds its own synthetic seedable run folder with `make_seed_run`. The page
shows the command as text. It runs nothing. The frozen public fixture is never touched.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import shlex
from pathlib import Path
from typing import Any

import pytest
from hub_browser_support import require_browser
from hub_support import make_run_folder
from mindrian_eureka.hub import page
from mindrian_eureka.hub.contracts import is_hub_folder
from mindrian_eureka.hub.deck import DECK
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.hub.writer import HubRequest, build_hub
from mindrian_eureka.run.console import Console
from mindrian_eureka.run.output import OUTPUT_UNUSUAL
from mindrian_eureka.seed.command import register_seed
from mindrian_eureka.seed.contracts import PAIR_ID_PATTERN, RUN_PLACEHOLDER, pair_command
from seed_support import make_seed_run
from test_hub_browser_core import CHECKS, scenario
from test_hub_extras import edit_records
from test_hub_reader import edit_json

REPO = Path(__file__).resolve().parents[1]
HUB = REPO / "src" / "mindrian_eureka" / "hub"
BANK_JS = HUB / "assets" / "authored" / "hub-bank.js"
BANK_CSS = HUB / "assets" / "authored" / "hub-bank.css"
SEED_ROW = str(CHECKS / "seed-row.js")
ENV_OUT = "EUREKA_SEED_HUB_OUT"
LABEL_COPY = "Start a room from this pair"
HINT_COPY = (
    "Copy the command under a pair and run it in a terminal. "
    "Replace RUN_FOLDER with your run folder. "
    "The command writes a new folder that MindrianOS can open as a room. "
    "It changes no room."
)
SEED_FACTS = ("seed_command", "hub-pair-seed", "has_seed_commands", "hub-seed-hint")


def build(run: Path, out: Path) -> Path:
    build_hub(HubRequest(run, out), Console(stderr=io.StringIO()))
    return out


def page_html(run: Path, out: Path) -> str:
    return (build(run, out) / "hub.html").read_text(encoding="utf-8")


@pytest.fixture
def seedable(tmp_path: Path) -> Path:
    return make_seed_run(tmp_path, name="seedable")


# --- 1. the payload ---------------------------------------------------------


def test_payload_has_a_command_for_every_seedable_pair(seedable: Path) -> None:
    payload = build_payload(load_run(seedable))
    assert payload["pairs"]
    for pair in payload["pairs"]:
        assert pair["seed_command"] == pair_command(pair["pair_id"])
        assert PAIR_ID_PATTERN.fullmatch(pair["pair_id"])
    assert payload["has_seed_commands"] is True


def test_command_parses_with_the_real_seed_parser(seedable: Path) -> None:
    parser = argparse.ArgumentParser(prog="eureka")
    register_seed(parser.add_subparsers(dest="command"))
    pairs = build_payload(load_run(seedable))["pairs"]
    assert len(pairs) >= 5
    for pair in pairs[:5]:
        words = shlex.split(pair["seed_command"])
        assert words[:2] == ["eureka", "seed"]
        args = parser.parse_args(words[1:])
        assert args.run_dir == RUN_PLACEHOLDER
        assert args.pair == pair["pair_id"]


# --- 2. runs that cannot be seeded ------------------------------------------


@pytest.mark.parametrize("kind", ["plain", "classed"])
def test_plain_and_classed_runs_have_no_seed_keys(tmp_path: Path, kind: str) -> None:
    run = make_run_folder(tmp_path, name=kind, pair_classes=kind == "classed")
    payload = build_payload(load_run(run))
    assert "has_seed_commands" not in payload
    assert all("seed_command" not in pair for pair in payload["pairs"])
    out = build(run, tmp_path / "hub")
    for name in ("hub-data.js", "hub.html"):
        text = (out / name).read_text(encoding="utf-8")
        for fact in SEED_FACTS:
            assert fact not in text, (name, fact)
    assert HINT_COPY not in (out / "hub.html").read_text(encoding="utf-8")


def test_run_without_cells_and_sections_has_no_command(tmp_path: Path) -> None:
    run = make_seed_run(tmp_path, name="nocells", with_room_sections=False)
    payload = build_payload(load_run(run))
    assert "has_seed_commands" not in payload
    assert all("seed_command" not in pair for pair in payload["pairs"])


def test_pair_with_a_record_without_cells_gets_no_command(seedable: Path) -> None:
    bare = "recs/C00001"

    def drop(item: dict[str, Any]) -> None:
        if item["id"] == bare:
            item.pop("room_cells", None)

    edit_records(seedable, drop)
    payload = build_payload(load_run(seedable))
    assert payload["has_seed_commands"] is True
    with_command = without = 0
    for pair in payload["pairs"]:
        touches = bare in (pair["left"]["id"], pair["right"]["id"])
        assert ("seed_command" in pair) is (not touches)
        with_command += "seed_command" in pair
        without += "seed_command" not in pair
    assert with_command and without


def test_hostile_pair_id_gets_no_command(seedable: Path, tmp_path: Path) -> None:
    def hostile(doc: dict[str, Any]) -> None:
        doc["pairs"][0]["pair_id"] = "pair-0123; echo hacked"
        doc["pairs"][1]["pair_id"] = "pair-0123456789ABCDEF0123"

    edit_json(seedable, OUTPUT_UNUSUAL, hostile)
    payload = build_payload(load_run(seedable))
    by_id = {pair["pair_id"]: pair for pair in payload["pairs"]}
    assert "seed_command" not in by_id["pair-0123; echo hacked"]
    assert "seed_command" not in by_id["pair-0123456789ABCDEF0123"]
    assert any("seed_command" in pair for pair in payload["pairs"])
    html = page_html(seedable, tmp_path / "hub")
    codes = re.findall(r"<code[^>]*>(.*?)</code>", html, re.DOTALL)
    assert codes
    assert not [code for code in codes if "hacked" in code or "ABCDEF" in code]


# --- 3. the no-script page --------------------------------------------------


def test_page_rows_and_hint(seedable: Path, tmp_path: Path) -> None:
    html = page_html(seedable, tmp_path / "hub")
    rows = html.count('class="hub-pair-row"')
    assert rows
    assert html.count('class="hub-pair-seed"') == rows
    assert html.count(LABEL_COPY) == rows
    assert html.count(HINT_COPY) == 1
    commands = re.findall(r'<code class="hub-mono">(eureka seed [^<]*)</code>', html)
    assert len(commands) == rows
    for command in commands:
        assert command.startswith("eureka seed RUN_FOLDER --pair pair-")
    # The hint comes before the first pair list.
    assert html.index(HINT_COPY) < html.index("data-engine-list")


def test_page_escapes_the_command(seedable: Path) -> None:
    payload = build_payload(load_run(seedable))
    records = {record["id"]: record for record in payload["records"]}
    pair = dict(payload["pairs"][0])
    pair["seed_command"] = 'eureka seed RUN_FOLDER --pair <b>&"x'
    row = page._pair_row(pair, records)  # type: ignore[arg-type]
    assert "<b>" not in row
    assert "&lt;b&gt;&amp;" in row
    assert row.count("hub-pair-seed") == 1


# --- 4. the copy deck -------------------------------------------------------


def test_deck_strings() -> None:
    assert DECK["B16.label"] == LABEL_COPY
    assert DECK["B16.hint"] == HINT_COPY
    for key in ("B16.label", "B16.hint"):
        value = DECK[key]
        assert "eureka" not in value.lower()
        assert "–" not in value and "—" not in value
    assert RUN_PLACEHOLDER in DECK["B16.hint"]


# --- 5. static script and style facts ---------------------------------------


def test_script_and_css_static_facts() -> None:
    script = BANK_JS.read_text(encoding="utf-8")
    for needle in ("seed_command", "hub-bank-seed", "B16.hint", "has_seed_commands"):
        assert needle in script, needle
    for banned in ("innerHTML", "clipboard", "fetch(", "XMLHttpRequest", "eval("):
        assert banned not in script, banned
    assert "hub-bank-labels hub-bank-seed" not in script
    assert "hub-bank-seed hub-bank-labels" not in script
    css = BANK_CSS.read_text(encoding="utf-8")
    # Phase 2.3.1 plan 06: the row is a named-area grid, so the seed row has a rule of its
    # own that spans every column. The browser test below proves the geometry.
    seed_rules = re.findall(r"^\.hub-bank-seed\s*\{([^}]*)\}", css, re.MULTILINE)
    assert len(seed_rules) == 1
    assert "grid-column: 1 / -1" in seed_rules[0]
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", css)


# --- 6. the real browser ----------------------------------------------------


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_bank_browser(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    run = make_seed_run(tmp_path, name="browser", n_records=12)
    commands = {
        pair["key"]: pair["seed_command"] for pair in build_payload(load_run(run))["pairs"]
    }
    out = build(run, tmp_path / "hub")
    steps: list[dict[str, Any]] = []
    for width in (360, 768, 1280):
        steps.append({"kind": "setViewport", "width": width, "height": 900})
        steps.append({"kind": "eval", "file": SEED_ROW, "as": str(width)})
    result = scenario(out, browser, steps=steps)
    print(json.dumps(result, sort_keys=True))
    for width, state in result.items():
        assert state["rows"], width
        assert len(state["rows"]) == len(commands)
        for row in state["rows"]:
            assert row["seed"] is True, (width, row)
            assert row["seedCount"] == 1
            assert row["command"] == commands[row["key"]]
            assert row["label"] == DECK["B16.label"]
            assert row["isLast"] is True
            assert row["hasLabelsClass"] is False
            assert row["seedTop"] >= row["othersBottom"] - 1, (width, row)
            assert row["seedRight"] <= row["rowRight"] + 1, (width, row)
            assert row["buttons"] == 1 and row["statusLabels"] == 1
        assert state["hint"] == 1
        assert state["hintText"] == DECK["B16.hint"]
        assert state["overflow"] <= 1, (width, state["overflow"])
        assert state["pwned"] == "undefined"


# --- 7. the hand-off to the owner's visual pass -----------------------------


def test_build_a_seedable_hub_for_the_visual_pass() -> None:
    target = os.environ.get(ENV_OUT)
    if not target:
        pytest.skip(f"set {ENV_OUT} to an empty folder to build the hub for the visual pass")
    base = Path(target)
    base.mkdir(parents=True, exist_ok=True)
    run = make_seed_run(base, name="run", n_records=12)
    hub = build(run, base / "hub")
    assert is_hub_folder(hub)
    print(f"seedable run: {run}")
    print(f"hub: {hub}")
