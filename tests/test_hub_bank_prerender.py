"""The no-script bank rows of the page stay plain (Phase 2.3.1, plan 06).

The script rows gain a title link, an Open link and a figure. The prerendered rows that the
no-script page shows are not touched: same class names, no figure, no page route, and the
pointer to the full list when the list is cut.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

from hub_support import make_run_folder
from mindrian_eureka.hub.contracts import NOSCRIPT_PAIRS_PER_ENGINE
from mindrian_eureka.hub.deck import DECK
from mindrian_eureka.hub.writer import HubRequest, build_hub
from mindrian_eureka.run.console import Console


def page(tmp_path: Path, **options: object) -> str:
    run = make_run_folder(tmp_path, **options)  # type: ignore[arg-type]
    out = tmp_path / "hub"
    build_hub(HubRequest(run, out), Console(stderr=io.StringIO()))
    return (out / "hub.html").read_text(encoding="utf-8")


def rows(html: str) -> list[str]:
    """The prerendered rows of the bank list (the graph list repeats the same rows)."""
    bank = html.split('id="graph-list"')[0]
    return re.findall(r'<li class="hub-pair-row"[^>]*>(.*?)</li>', bank, re.DOTALL)


def test_prerendered_rows_keep_their_classes_and_stay_plain(tmp_path: Path) -> None:
    html = page(tmp_path, n_records=40, pairs_per_engine=NOSCRIPT_PAIRS_PER_ENGINE + 10,
                pair_classes=True)
    found = rows(html)
    assert len(found) == 2 * NOSCRIPT_PAIRS_PER_ENGINE
    assert any("hub-pair-extras" in row for row in found)
    for row in found:
        assert "hub-pair-rank" in row and "hub-pair-record" in row
        assert "hub-pair-scores" in row and "hub-reading" in row
        assert "<svg" not in row
        assert "#/pair/" not in row
        assert "hub-bank-" not in row
    # One pointer under each cut engine list of the bank (the graph list repeats them).
    assert html.split('id="graph-list"')[0].count(DECK["B14"]) == 2


def test_seed_rows_of_the_no_script_page_are_unchanged(tmp_path: Path) -> None:
    from seed_support import make_seed_run

    run = make_seed_run(tmp_path, name="seedable", n_records=12)
    out = tmp_path / "hub"
    build_hub(HubRequest(run, out), Console(stderr=io.StringIO()))
    html = (out / "hub.html").read_text(encoding="utf-8")
    found = rows(html)
    assert found
    for row in found:
        assert row.count("hub-pair-seed") == 1
        assert "<svg" not in row and "#/pair/" not in row


def test_uncut_list_has_no_pointer(tmp_path: Path) -> None:
    html = page(tmp_path, pairs_per_engine=10)
    assert DECK["B14"] not in html
    assert len(rows(html)) == 20
