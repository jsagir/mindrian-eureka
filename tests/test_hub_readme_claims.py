"""Claim tests that tie the README sentences and numbers about the hub to the code (plan 09).

The hub section of `README.md`, the `hub/` line of `src/README.md` and the hub section of
`examples/public-example/README.md` describe the hub of Phase 2.3.1. Each claim that can be
tied to the code or to a build of the public fixture is tied here (T-02.3.1-32).
"""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any

import pytest
from mindrian_eureka.hub import figures, terms
from mindrian_eureka.hub.contracts import has_internal_name
from mindrian_eureka.hub.deck import DECK, fill
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
SRC_README = ROOT / "src/README.md"
EXAMPLE_README = ROOT / "examples/public-example/README.md"
AUTHORED = ROOT / "src/mindrian_eureka/hub/assets/authored"
PUBLIC_RUN = ROOT / "tests/fixtures/hub_public/run"
HUB_HEADING = "## Open the results as one page"
DASHES = (chr(8211), chr(8212))


def hub_section() -> str:
    text = README.read_text(encoding="utf-8")
    assert text.count(HUB_HEADING) == 1
    rest = text.split(HUB_HEADING, 1)[1]
    nxt = re.search(r"^## ", rest, re.M)
    return rest[: nxt.start()] if nxt else rest


@pytest.fixture(scope="module")
def public() -> dict[str, Any]:
    return dict(build_payload(load_run(PUBLIC_RUN)))


def test_hub_section_names_the_new_parts() -> None:
    section = hub_section()
    for phrase in ("sticky header", "Opportunity bank", "Connection graph", "Catalogue",
                   "finding row", "picture", "reading panel", "its own page"):
        assert phrase in section, phrase
    assert DECK["D01"] in section
    assert f'"{DECK["G17.label"]}"' in section
    assert f'"{DECK["G03.theme.light"]}"' in section and f'"{DECK["G03.theme.dark"]}"' in section


def test_theme_claim_matches_the_code() -> None:
    section = hub_section()
    for phrase in ("follows the system setting", "kept in your browser on this machine",
                   "blocks storage"):
        assert phrase in section, phrase
    key = re.search(r"`(hub-theme)`", section)
    assert key, "the README does not quote the storage key"
    boot = (AUTHORED / "hub-boot.js").read_text(encoding="utf-8")
    theme = (AUTHORED / "hub-theme.js").read_text(encoding="utf-8")
    assert key.group(1) in boot and key.group(1) in theme
    for path in AUTHORED.glob("*.js"):
        if path.name not in ("hub-boot.js", "hub-theme.js"):
            assert "localStorage" not in path.read_text(encoding="utf-8"), path.name
    for text in (boot, theme):
        inside = sum(block.count("localStorage")
                     for block in re.findall(r"try\s*\{(.*?)\}\s*catch", text, re.S))
        assert text.count("localStorage") >= 1
        assert inside == text.count("localStorage")


def test_pages_claim_matches_the_code() -> None:
    section = hub_section()
    core = (AUTHORED / "hub-core.js").read_text(encoding="utf-8")
    for route in ("#/pair/", "#/record/"):
        assert route in section, route
        assert route[1:] in core, route
    for key in ("ArrowLeft", "ArrowRight", "Escape"):
        assert key in section and key in core, key
    assert "its own page" in section
    assert DECK["G19.prev"] == "Previous" and "Previous" in section
    assert DECK["G19.next"] == "Next" and "Next" in section
    assert DECK["G19.back.bank"] in section
    assert DECK["G19.back.catalogue"] in section
    assert fill(DECK["G19.pos.pair"], n=3, k=63) in section


def test_words_claim_matches_the_rules() -> None:
    section = hub_section()
    words = re.search(r"the (\d+) most distinctive words of each record", section)
    assert words and int(words.group(1)) == terms.TOP_N
    shared = re.search(r"at most (\d+) words that both records share", section)
    assert shared and int(shared.group(1)) == terms.SHARED_MAX
    depth = re.search(r"the top (\d+) words of each record", section)
    assert depth and int(depth.group(1)) == terms.DEPTH
    assert "screening aid" in section and "not evidence" in section
    assert "docs/brand/hub-terms-rules.md" in section


def test_picture_claims_match_the_code(public: dict[str, Any]) -> None:
    section = hub_section()
    for phrase in ("SVG", "no image generator", "small picture for each pair",
                   "larger picture", "narrow screens", "screen readers"):
        assert phrase in section, phrase
    source = Path(figures.__file__).read_text(encoding="utf-8")
    for banned in ("PIL", "cairosvg", "requests", "urllib", "socket", "import random",
                   "import time"):
        assert banned not in source, banned
    pairs = public["figures"]["pairs"]
    keys = {pair["key"] for pair in public["pairs"]}
    assert set(pairs) == keys
    assert all("card" in item and "detail" in item for item in pairs.values())
    sentence = next(line for line in section.splitlines() if "small picture for each pair" in line)
    for number in re.findall(r"\b(\d+)\b", sentence):
        assert int(number) == len(keys), number
    switch = re.search(r"(\d+) px wide", section)
    assert switch, "the README does not name the switch width"
    css = (AUTHORED / "hub-pages.css").read_text(encoding="utf-8")
    assert f"@media (min-width: {switch.group(1)}px)" in css


def test_band_claim_matches_a_run(public: dict[str, Any]) -> None:
    section = hub_section()
    assert public["pattern"]["state"] == "single"
    filled = [fill(DECK[line["key"]], **line["values"]) for line in public["pattern"]["lines"]]
    sentence = next(line for line in section.splitlines() if "public example" in line
                    and DECK["G17.label"] in line)
    numbers = re.findall(r"\b(\d+)\b", sentence)
    assert numbers, "the band sentence quotes no number"
    for number in numbers:
        assert any(re.search(rf"\b{number}\b", line) for line in filled), number


def test_locked_claim(tmp_path: Path) -> None:
    pytest.importorskip("cryptography")
    from mindrian_eureka.hub.writer import HubRequest, build_hub
    from mindrian_eureka.run.console import Console

    section = hub_section()
    assert "inside the encrypted data" in section
    assert "built in the browser after the passphrase" in section
    out = tmp_path / "locked"
    build_hub(HubRequest(PUBLIC_RUN, out, password="synthetic test passphrase only"),
              Console(stderr=io.StringIO()))
    html = (out / "hub.html").read_text(encoding="utf-8")
    data = (out / "hub-data.js").read_text(encoding="utf-8")
    payload = dict(build_payload(load_run(PUBLIC_RUN)))
    first = next(iter(payload["terms"]["records"].values()))
    assert first, "the first record has words"
    for text in (html, data):
        assert "<svg" not in text
        assert "#/pair/" not in text and "#/record/" not in text
        for word in first:
            assert not re.search(rf"\b{re.escape(word)}\b", text), word


def test_src_readme_lists_the_modules() -> None:
    text = SRC_README.read_text(encoding="utf-8")
    for name in ("terms.py", "figures.py", "pattern.py"):
        assert f"`{name}`" in text, name
        assert (ROOT / "src/mindrian_eureka/hub" / name).is_file(), name
    hub_line = next(line for line in text.splitlines() if "`hub/`" in line)
    for name in ("terms.py", "figures.py", "pattern.py"):
        assert name in hub_line, name
    for name in re.findall(r"`([\w/]+\.py)`", text):
        candidates = [ROOT / "src/mindrian_eureka" / name, ROOT / "src/mindrian_eureka/hub" / name]
        assert any(path.is_file() for path in candidates), name


def test_example_readme_hub_steps() -> None:
    import contextlib

    from mindrian_eureka.cli import main

    text = EXAMPLE_README.read_text(encoding="utf-8")
    assert text.index("## What you should see") < text.index("## Open it as one page")
    section = text.split("## Open it as one page", 1)[1].split("\n## ", 1)[0]
    assert "uv run eureka hub my-run --out my-hub" in section
    assert "hub.html" in section
    for phrase in ("its own page", "candidate, not verified"):
        assert phrase in section, phrase
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.suppress(SystemExit):
        main(["hub", "--help"])
    help_text = buffer.getvalue()
    assert "run_dir" in help_text and "--out DIR" in help_text


def test_no_dash_no_internal_names_and_links_resolve() -> None:
    for path in (README, SRC_README, EXAMPLE_README):
        text = path.read_text(encoding="utf-8")
        assert not any(dash in text for dash in DASHES), path.name
        # The engine-code scan applies to the hub text of this plan. README.md names the old
        # engine code on purpose in its "Engine names" section; the example README names a
        # test file; the source README names the module files. Those older lines stay.
        if path == README:
            checked = hub_section()
        elif path == EXAMPLE_README:
            checked = text.split("## Open it as one page", 1)[1].split("\n## ", 1)[0]
        else:
            checked = re.sub(r"`[\w/]+\.py`", "`module`", text)
        assert not has_internal_name(checked), path.name
        for target in re.findall(r"\]\(([^)]+)\)", text):
            if target.startswith(("http:", "https:", "mailto:")):
                continue
            assert (path.parent / target.split("#", 1)[0]).exists(), f"{path.name}: {target}"
