"""Keep the fixed deck connected to literal, dynamic and payload-backed copy."""

from __future__ import annotations

import re
from pathlib import Path

from hub_support import make_run_folder
from mindrian_eureka.hub.deck import DECK
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run

ROOT = Path(__file__).resolve().parents[1]
AUTHORED = ROOT / "src/mindrian_eureka/hub/assets/authored"


def used_keys(text: str) -> set[str]:
    quoted = set(re.findall(r'''["']([A-Za-z][\w.]+)["']''', text))
    declared = set()
    for line in text.splitlines():
        if re.match(r"\s*(?:#|//)\s*deck keys:", line):
            declared.update(line.partition("deck keys:")[2].split())
    assert declared <= set(DECK), sorted(declared - set(DECK))
    return quoted | declared


def test_every_copy_key_is_used() -> None:
    files = [ROOT / "src/mindrian_eureka/hub/page.py", *sorted(AUTHORED.glob("*.js"))]
    used = set().union(*(used_keys(path.read_text()) for path in files))
    assert set(DECK) <= used, f"Unused copy keys: {sorted(set(DECK) - used)}"


def test_payload_backed_status_and_registered_engine_copy(tmp_path: Path) -> None:
    data = build_payload(load_run(make_run_folder(tmp_path)))
    assert data["label"] == DECK["G08"]
    for key, engine in data["engines"].items():
        assert engine["name"] == DECK["G15." + key]
        assert engine["short_name"] == DECK["G15." + key + ".short"]
    assert DECK["P06.source"] == "From the source"


def test_coverage_negative_control() -> None:
    text = '// deck keys: Gr03.record\nconst key = "Gr03.eureka";'
    assert {"Gr03.record", "Gr03.eureka"} <= used_keys(text)
    assert "Gr03.crossing" not in used_keys(text)
