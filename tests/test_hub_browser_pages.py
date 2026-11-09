"""The pair and record pages of the hub in Chromium and Firefox (Phase 2.3.1 plan 08, HUB-11).

Routes, the Back knob rule, Previous and Next with position, the arrow keys and Escape, focus
and title, the page content, the real-text twin of the detail figure and its switch at 768 px,
the text fit with the vendored fonts, the 44 px targets, the 13 px floor, both themes, reduced
motion, and hostile data. The 24 checks of the owner's prototype of 2026-11-08 are ported here
or owned by the plan the 08 plan names. Public fixture data and synthetic runs only.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

import pytest
from hub_browser_support import file_url, require_browser
from hub_support import tree_hash
from mindrian_eureka.hub.deck import DECK, fill
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.hub.verify import verify_payload
from test_hub_browser_core import CHECKS, built_hub, scenario
from test_hub_browser_review import CONTRAST, PUBLIC, public_hub
from test_hub_public_example import build
from test_hub_public_example import payload as payload_of_build

PAGES = str(CHECKS / "pages-state.js")
FIT = str(CHECKS / "pages-fit.js")
ENGINES = ("unusual_pairs", "wording_and_meaning")
# The characters that encodeURIComponent keeps, so Python and the browser agree on a route.
URI_SAFE = "-_.!~*'()"
WIDTHS = (320, 390, 768, 1280, 1600)
PAYLOAD_KEYS = {
    "schema",
    "label",
    "tool_version",
    "run_fingerprint",
    "config",
    "counts",
    "engines",
    "records",
    "pairs",
    "hoods",
    "bridges",
    "data_check",
    "graph",
    "pattern",
    "terms",
    "figures",
}
BROWSERS = ["chromium", "firefox"]


def pages(name: str, **args):
    return {"kind": "eval", "file": PAGES, "as": name, "args": args}


def fit(name: str):
    return {"kind": "eval", "file": FIT, "as": name}


def click(selector: str):
    return {"kind": "click", "selector": selector}


def viewport(width: int, height: int = 900):
    return {"kind": "setViewport", "width": width, "height": height}


def public_payload():
    return build_payload(load_run(PUBLIC))


def engine_list(payload, engine: str) -> list:
    return sorted((p for p in payload["pairs"] if p["engine"] == engine), key=lambda p: p["rank"])


def pair_by_rank(payload, engine: str, rank: int):
    return next(p for p in payload["pairs"] if p["engine"] == engine and p["rank"] == rank)


def pair_route(pair) -> str:
    return f"#/pair/{pair['engine']}/{pair['rank']}"


def record_route(record_id: str) -> str:
    return "#/record/" + quote(record_id, safe=URI_SAFE)


def row_link(engine: str, rank: int) -> str:
    return f'#bank-list li[data-engine="{engine}"][data-rank="{rank}"] a.hub-bank-open-link'


def record_of(payload, record_id: str):
    return next(r for r in payload["records"] if r["id"] == record_id)


def canonical(svg: str) -> bytes:
    return ET.tostring(ET.fromstring(svg))


def pair_title(payload, pair) -> str:
    return fill(
        DECK["G19.doc.pair"], n=pair["rank"], x=pair["left"]["title"], y=pair["right"]["title"]
    )


def heading_text(pair) -> str:
    return pair["left"]["title"] + " " + DECK["G19.and"] + " " + pair["right"]["title"]


def other_engine_pair(payload, pair):
    other = ENGINES[1 - ENGINES.index(pair["engine"])]
    return next(
        (p for p in payload["pairs"] if p["engine"] == other and p["pair_id"] == pair["pair_id"]),
        None,
    )


def assert_page_mode(state: dict, kind: str) -> None:
    assert state["onPage"] and state["visible"]["site"], state["visible"]
    assert state["page"]["kind"] == kind
    for part in ("bank", "graph", "catalogue", "titleBand", "counts", "band"):
        assert not state["visible"][part], (part, state["visible"])
    assert (
        state["visible"]["header"] and state["visible"]["footer"] and state["visible"]["dataCheck"]
    )
    assert len(state["h1s"]) == 1, state["h1s"]


def assert_view_mode(state: dict, view: str) -> None:
    assert state["page"] is None and not state["onPage"]
    assert state["visible"][view] and not state["visible"]["site"], state["visible"]
    assert state["view"] == view


# --- Routes, knobs and keys -------------------------------------------------


@pytest.mark.parametrize("browser", BROWSERS)
def test_open_pair_from_bank_row_title(tmp_path: Path, browser: str) -> None:
    """Prototype checks 1 to 3: home by default, a row click opens the pair, focus on the h1."""
    require_browser(browser)
    payload = public_payload()
    pair = pair_by_rank(payload, "unusual_pairs", 3)
    result = scenario(
        public_hub(tmp_path),
        browser,
        steps=[pages("load"), click(row_link("unusual_pairs", 3)), pages("pair", waitPage="page")],
    )
    load = result["load"]
    assert load["h1Count"] == 1 and load["page"] is None
    assert_view_mode(load, "bank")
    state = result["pair"]
    assert state["hash"] == "#/pair/unusual_pairs/3"
    assert state["page"] == {"kind": "pair", "key": pair["key"]}
    assert_page_mode(state, "pair")
    assert state["h1s"] == [heading_text(pair)]
    assert state["focus"]["isPageHeading"], state["focus"]
    assert state["title"] == pair_title(payload, pair)
    assert state["notice"] == ""
    assert state["current"] == [{"href": "#bank", "value": "true"}]


@pytest.mark.parametrize("browser", BROWSERS)
def test_previous_next_position_and_ends(tmp_path: Path, browser: str) -> None:
    """Prototype checks 4 to 7, 9 and 10: Next, Previous, the arrow keys, no link at the ends."""
    require_browser(browser)
    payload = public_payload()
    out = public_hub(tmp_path)
    steps = []
    expected = {}
    for engine in ENGINES:
        ordered = engine_list(payload, engine)
        third, fourth = ordered[2], ordered[3]
        first, last = ordered[0], ordered[-1]
        steps += [
            pages(f"{engine}-3", hash=pair_route(third), waitPage="page"),
            click('#hub-site nav.hub-knobs a[rel="next"]'),
            pages(f"{engine}-next", waitHash=pair_route(fourth)),
            click('#hub-site nav.hub-knobs a[rel="prev"]'),
            pages(f"{engine}-prev", waitHash=pair_route(third)),
            pages(f"{engine}-right", key="ArrowRight", waitHash=pair_route(fourth)),
            pages(f"{engine}-left", key="ArrowLeft", waitHash=pair_route(third)),
            pages(f"{engine}-first", hash=pair_route(first), waitPage="page"),
            pages(f"{engine}-first-left", key="ArrowLeft"),
            pages(f"{engine}-last", hash=pair_route(last), waitPage="page"),
            pages(f"{engine}-last-right", key="ArrowRight"),
        ]
        expected[engine] = (ordered, third, fourth, first, last)
    records = payload["records"]
    steps += [
        pages("record-first", hash=record_route(records[0]["id"]), waitPage="page"),
        pages("record-first-left", key="ArrowLeft"),
        pages("record-right", key="ArrowRight", waitHash=record_route(records[1]["id"])),
        pages("record-left", key="ArrowLeft", waitHash=record_route(records[0]["id"])),
        pages("record-last", hash=record_route(records[-1]["id"]), waitPage="page"),
        pages("record-last-right", key="ArrowRight"),
    ]
    result = scenario(out, browser, steps=steps)
    for engine, (ordered, third, fourth, first, last) in expected.items():
        k = len(ordered)
        third_state = result[f"{engine}-3"]
        assert third_state["knobs"]["position"] == fill(DECK["G19.pos.pair"], n=3, k=k)
        assert third_state["knobs"]["label"] == DECK["G19.knobs.pair"]
        assert third_state["knobs"]["prev"]["href"] == pair_route(ordered[1])
        assert third_state["knobs"]["next"]["href"] == pair_route(fourth)
        assert third_state["knobs"]["prev"]["label"] == DECK["G19.prev.pair"]
        assert third_state["knobs"]["next"]["label"] == DECK["G19.next.pair"]
        assert third_state["knobs"]["prev"]["text"] == DECK["G19.prev"]
        assert third_state["knobs"]["next"]["text"] == DECK["G19.next"]
        assert third_state["knobsBottom"]["position"] == third_state["knobs"]["position"]
        assert result[f"{engine}-next"]["hash"] == pair_route(fourth)
        assert result[f"{engine}-next"]["knobs"]["position"] == fill(DECK["G19.pos.pair"], n=4, k=k)
        assert result[f"{engine}-next"]["focus"]["isPageHeading"]
        assert result[f"{engine}-prev"]["hash"] == pair_route(third)
        assert result[f"{engine}-right"]["hash"] == pair_route(fourth)
        assert result[f"{engine}-left"]["hash"] == pair_route(third)
        first_state = result[f"{engine}-first"]
        assert first_state["knobs"]["prev"] is None
        off = first_state["knobs"]["prevOff"]
        assert off["text"] == DECK["G19.prev"] and off["ariaHidden"] == "true"
        assert off["href"] is None and off["tabindex"] is None and off["role"] is None
        assert first_state["knobs"]["next"] is not None
        assert first_state["knobs"]["position"] == fill(DECK["G19.pos.pair"], n=1, k=k)
        assert result[f"{engine}-first-left"]["hash"] == pair_route(first)
        last_state = result[f"{engine}-last"]
        assert last_state["knobs"]["next"] is None
        off = last_state["knobs"]["nextOff"]
        assert off["text"] == DECK["G19.next"] and off["ariaHidden"] == "true"
        assert off["href"] is None and off["tabindex"] is None
        assert last_state["knobs"]["prev"] is not None
        assert last_state["knobs"]["position"] == fill(DECK["G19.pos.pair"], n=k, k=k)
        assert result[f"{engine}-last-right"]["hash"] == pair_route(last)
    n = len(records)
    first_record = result["record-first"]
    assert first_record["knobs"]["position"] == fill(DECK["G19.pos.record"], n=1, k=n)
    assert first_record["knobs"]["label"] == DECK["G19.knobs.record"]
    assert (
        first_record["knobs"]["prev"] is None
        and first_record["knobs"]["prevOff"]["ariaHidden"] == "true"
    )
    assert first_record["knobs"]["next"]["href"] == record_route(records[1]["id"])
    assert first_record["knobs"]["next"]["label"] == DECK["G19.next.record"]
    assert result["record-first-left"]["hash"] == record_route(records[0]["id"])
    assert result["record-right"]["hash"] == record_route(records[1]["id"])
    assert result["record-right"]["knobs"]["position"] == fill(DECK["G19.pos.record"], n=2, k=n)
    assert result["record-right"]["knobs"]["prev"]["label"] == DECK["G19.prev.record"]
    assert result["record-left"]["hash"] == record_route(records[0]["id"])
    last_record = result["record-last"]
    assert (
        last_record["knobs"]["next"] is None
        and last_record["knobs"]["nextOff"]["ariaHidden"] == "true"
    )
    assert last_record["knobs"]["position"] == fill(DECK["G19.pos.record"], n=n, k=n)
    assert result["record-last-right"]["hash"] == record_route(records[-1]["id"])


@pytest.mark.parametrize("browser", BROWSERS)
def test_back_knob_rule(tmp_path: Path, browser: str) -> None:
    """Prototype checks 8, 11 and 12: the Back knob returns to the parent and keeps history sane."""
    require_browser(browser)
    payload = public_payload()
    out = public_hub(tmp_path)
    third = pair_by_rank(payload, "unusual_pairs", 3)
    fourth = pair_by_rank(payload, "unusual_pairs", 4)
    back = "#hub-site nav.hub-knobs a.hub-knob--back"
    # (a) The previous page is the parent: history.back(), nothing pushed.
    # (b) The previous page is a neighbour: the link is followed, one entry is added.
    result = scenario(
        out,
        browser,
        steps=[
            pages("load"),
            click(row_link("unusual_pairs", 3)),
            pages("a-open", waitPage="page"),
            click(back),
            pages("a-back", waitPage="view"),
            click(row_link("unusual_pairs", 3)),
            pages("b-open", waitPage="page"),
            click('#hub-site nav.hub-knobs a[rel="next"]'),
            pages("b-next", waitHash=pair_route(fourth)),
            click(back),
            pages("b-back", waitPage="view"),
        ],
    )
    load, opened, returned = result["load"], result["a-open"], result["a-back"]
    assert opened["page"]["key"] == third["key"] and opened["nav"]["previous"] == "bank"
    assert_view_mode(returned, "bank")
    assert returned["hash"] == load["hash"]
    assert returned["historyLength"] == opened["historyLength"]
    assert result["b-next"]["page"]["key"] == fourth["key"]
    assert result["b-next"]["nav"]["previous"] != "bank"
    assert_view_mode(result["b-back"], "bank")
    assert result["b-back"]["hash"] == "#/"
    assert result["b-back"]["historyLength"] == result["b-next"]["historyLength"] + 1
    # (c) A direct link: no previous page in this document; the knob follows its link; the hub
    # stays.
    direct = scenario(
        out,
        browser,
        url=file_url(out / "hub.html", "/pair/unusual_pairs/3"),
        steps=[pages("c-load"), click(back), pages("c-back", waitPage="view")],
    )
    assert direct["c-load"]["page"]["key"] == third["key"]
    assert direct["c-load"]["nav"]["previous"] is None
    assert direct["c-load"]["focus"]["isPageHeading"] is False
    assert_view_mode(direct["c-back"], "bank")
    assert direct["c-back"]["hash"] == "#/"
    assert direct["c-back"]["path"].endswith("/hub.html")
    # (d) A record from the catalogue goes back by history; a record from a pair goes to the
    # catalogue by its link (the parent rule).
    result = scenario(
        out,
        browser,
        steps=[
            click('#hub-nav a[href="#catalogue"]'),
            pages("d-cat", waitPage="view"),
            click("#catalogue-list tbody tr a.hub-catalogue-open"),
            pages("d-open", waitPage="page"),
            click(back),
            pages("d-back", waitPage="view"),
            pages("d-pair", hash=pair_route(third), waitPage="page"),
            click("#hub-site article.hub-site-record h3 a"),
            pages("d-record", waitHash=record_route(third["left"]["id"])),
            click(back),
            pages("d-back2", waitPage="view"),
        ],
    )
    assert result["d-open"]["page"]["kind"] == "record"
    assert result["d-open"]["knobs"]["back"]["dataBack"] == "catalogue"
    assert result["d-open"]["knobs"]["back"]["href"] == "#/catalogue"
    assert_view_mode(result["d-back"], "catalogue")
    assert result["d-back"]["historyLength"] == result["d-open"]["historyLength"]
    assert result["d-record"]["page"] == {"kind": "record", "key": third["left"]["id"]}
    assert_view_mode(result["d-back2"], "catalogue")
    assert result["d-back2"]["hash"] == "#/catalogue"
    assert result["d-back2"]["historyLength"] == result["d-record"]["historyLength"] + 1


@pytest.mark.parametrize("browser", BROWSERS)
def test_return_keeps_place(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    out = built_hub(tmp_path, n_records=40, pairs_per_engine=40)
    back = "#hub-site nav.hub-knobs a.hub-knob--back"
    bank_link = "#bank-list li:nth-child(12) a.hub-bank-open-link"
    catalogue_link = "#catalogue-list tbody tr:nth-child(12) a.hub-catalogue-open"
    result = scenario(
        out,
        browser,
        steps=[
            viewport(1280),
            pages("start", scrollTo="#bank-list li:nth-child(12)", focus=bank_link),
            click(bank_link),
            pages("open", waitPage="page"),
            click(back),
            pages("back", waitPage="view"),
            click('#hub-nav a[href="#catalogue"]'),
            pages("cat", waitPage="view"),
            pages(
                "cat-start", scrollTo="#catalogue-list tbody tr:nth-child(12)", focus=catalogue_link
            ),
            click(catalogue_link),
            pages("cat-open", waitPage="page"),
            click(back),
            pages("cat-back", waitPage="view"),
            pages("direct", hash="#/pair/unusual_pairs/2", waitPage="page"),
            click(back),
            pages("direct-back", waitPage="view"),
        ],
    )
    start, returned = result["start"], result["back"]
    assert (
        start["scrollY"] > 200
        and start["focus"]["href"] == "#/pair/unusual_pairs/12"
        or start["focus"]["href"].startswith("#/pair/")
    )
    assert result["open"]["scrollY"] == 0 and result["open"]["focus"]["isPageHeading"]
    assert_view_mode(returned, "bank")
    assert abs(returned["scrollY"] - start["scrollY"]) <= 2, (returned["scrollY"], start["scrollY"])
    assert returned["focus"]["href"] == start["focus"]["href"]
    cat_start, cat_back = result["cat-start"], result["cat-back"]
    assert cat_start["focus"]["href"].startswith("#/record/")
    assert_view_mode(cat_back, "catalogue")
    assert abs(cat_back["scrollY"] - cat_start["scrollY"]) <= 2, (
        cat_back["scrollY"],
        cat_start["scrollY"],
    )
    assert cat_back["focus"]["href"] == cat_start["focus"]["href"]
    # The opener is gone (a hash set by script has none): the focus is on the view heading.
    assert result["direct-back"]["focus"]["id"] == "hub-title"


@pytest.mark.parametrize("browser", BROWSERS)
def test_escape_order(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    payload = public_payload()
    third = pair_by_rank(payload, "unusual_pairs", 3)
    result = scenario(
        public_hub(tmp_path),
        browser,
        steps=[
            click("#bank-list .hub-bank-read"),
            pages("panel"),
            pages("esc-panel", key="Escape"),
            pages("pair", hash=pair_route(third), waitPage="page"),
            pages("esc-page", key="Escape", waitPage="view"),
            click('#hub-nav a[href="#catalogue"]'),
            {"kind": "focus", "selector": "#catalogue-search"},
            pages("esc-field", key="Escape"),
            pages("pair2", hash=pair_route(third), waitPage="page"),
            pages("alt", key="ArrowRight", alt=True),
            pages("ctrl", key="ArrowRight", ctrl=True),
            pages("meta", key="ArrowLeft", meta=True),
            pages("field", key="ArrowRight", keyTarget="#catalogue-search"),
        ],
    )
    assert result["panel"]["panelOpen"] is True
    assert result["esc-panel"]["panelOpen"] is False
    assert (
        result["esc-panel"]["hash"] == result["panel"]["hash"]
        and result["esc-panel"]["page"] is None
    )
    assert result["pair"]["page"]["key"] == third["key"]
    assert_view_mode(result["esc-page"], "bank")
    assert result["esc-field"]["view"] == "catalogue" and result["esc-field"]["page"] is None
    for name in ("alt", "ctrl", "meta", "field"):
        assert result[name]["hash"] == pair_route(third), name
        assert result[name]["page"]["key"] == third["key"], name


@pytest.mark.parametrize("browser", BROWSERS)
def test_unknown_and_hostile_routes(tmp_path: Path, browser: str) -> None:
    """Prototype check 21: an unknown route keeps the page that was shown and says so."""
    require_browser(browser)
    payload = public_payload()
    bad = [
        "#/nope",
        "#/pair/unusual_pairs/9999",
        "#/pair/__proto__/1",
        "#/pair/constructor/1",
        "#/pair/unusual_pairs/01",
        "#/pair/unusual_pairs/1x",
        "#/pair/unusual_pairs",
        "#/record/nosuchrecord",
        "#/record/%E0%A4%A",
        "#/record/",
    ]
    third = pair_by_rank(payload, "unusual_pairs", 3)
    fourth = pair_by_rank(payload, "unusual_pairs", 4)
    steps = [pages(f"bad-{index}", hash=value) for index, value in enumerate(bad)]
    steps += [
        pages("page", hash=pair_route(third), waitPage="page"),
        pages("page-nope", hash="#/nope"),
        pages("page-valid", hash=pair_route(fourth), waitHash=pair_route(fourth)),
    ]
    result = scenario(public_hub(tmp_path), browser, steps=steps)
    for index, value in enumerate(bad):
        state = result[f"bad-{index}"]
        assert state["notice"] == fill(DECK["E05"], ID=value[1:]), (value, state["notice"])
        assert state["page"] is None and state["visible"]["bank"], value
        assert not state["visible"]["site"]
    assert result["page"]["notice"] == ""
    assert (
        result["page-nope"]["page"]["key"] == third["key"]
        and result["page-nope"]["visible"]["site"]
    )
    assert result["page-nope"]["notice"] == fill(DECK["E05"], ID="/nope")
    assert (
        result["page-valid"]["page"]["key"] == fourth["key"]
        and result["page-valid"]["notice"] == ""
    )
    # The hostile run: ids that are shell names or a prototype key open as pages, as text.
    out = built_hub(tmp_path, hostile=True)
    hostile = build_payload(load_run(tmp_path / "run"))
    steps = []
    for record_id in ("bank", "hub-results", "__proto__"):
        steps.append(
            pages(
                record_id,
                hash=record_route(record_id),
                waitHash=record_route(record_id),
                content=True,
            )
        )
    steps += [
        pages("legacy-record", hash="#doc003"),
        pages("legacy-bank", hash="#record:bank"),
        pages("legacy-graph", hash="#graph"),
        pages("legacy-catalogue", hash="#catalogue"),
    ]
    result = scenario(out, browser, steps=steps)
    for record_id in ("bank", "hub-results", "__proto__"):
        state = result[record_id]
        record = record_of(hostile, record_id)
        assert state["page"] == {"kind": "record", "key": record_id}
        assert state["h1s"] == [record["title"]], state["h1s"]
        assert state["content"]["h1"] == record["title"]
        assert state["pwned"] is False
        counts = state["siteCounts"]
        assert counts["script"] == 0 and counts["img"] == 0 and counts["iframe"] == 0
        assert counts["svg"] == counts["svgFigure"]
    assert result["legacy-record"]["selection"] == {"type": "record", "id": "doc003"}
    assert result["legacy-record"]["page"] is None
    assert result["legacy-bank"]["selection"] == {"type": "record", "id": "bank"}
    assert result["legacy-graph"]["view"] == "graph" and result["legacy-graph"]["page"] is None
    assert (
        result["legacy-catalogue"]["view"] == "catalogue"
        and result["legacy-catalogue"]["page"] is None
    )


@pytest.mark.parametrize("browser", BROWSERS)
def test_open_links_from_other_views(tmp_path: Path, browser: str) -> None:
    """Prototype checks 14 and 15, adapted: every graph pair row has one Open link that opens
    the pair page; the catalogue and the panel open pages too; the nav leaves page mode."""
    require_browser(browser)
    payload = public_payload()
    first_id = sorted(record["id"] for record in payload["records"])[0]
    result = scenario(
        public_hub(tmp_path),
        browser,
        steps=[
            click('#hub-nav a[href="#catalogue"]'),
            click("#catalogue-list tbody tr a.hub-catalogue-open"),
            pages("cat-open", waitPage="page"),
            pages("graph", hash="#/graph", waitPage="view"),
            click("#graph-list a.hub-graph-open"),
            pages("graph-open", waitPage="page"),
            pages("bank", hash="#/", waitPage="view"),
            click("#bank-list .hub-bank-read"),
            pages("panel"),
            click("#hub-panel a.hub-panel-page"),
            pages("panel-open", waitPage="page"),
            pages("catalogue", hash="#/catalogue", waitPage="view"),
            click("#catalogue-list tbody tr button"),
            pages("panel-record"),
            click("#hub-panel a.hub-panel-page"),
            pages("panel-record-open", waitPage="page"),
            click('#hub-nav a[href="#bank"]'),
            pages("nav", waitPage="view"),
            pages("browser-back", back=True, waitPage="page"),
        ],
    )
    assert result["cat-open"]["hash"] == record_route(first_id)
    assert result["cat-open"]["page"] == {"kind": "record", "key": first_id}
    graph = result["graph"]
    assert graph["view"] == "graph" and graph["graphList"]["rows"] > 0
    assert graph["graphList"]["rows"] == graph["graphList"]["openLinks"]
    assert re.fullmatch(
        r"#/pair/(unusual_pairs|wording_and_meaning)/[1-9][0-9]*", result["graph-open"]["hash"]
    )
    assert result["graph-open"]["page"]["kind"] == "pair"
    assert result["panel"]["panelOpen"] is True
    opened = result["panel-open"]
    assert opened["page"]["kind"] == "pair" and opened["panelOpen"] is False
    assert opened["focus"]["isPageHeading"] and not opened["visible"]["panel"]
    assert result["panel-record"]["panelOpen"] is True
    record_opened = result["panel-record-open"]
    assert record_opened["page"]["kind"] == "record" and record_opened["panelOpen"] is False
    assert record_opened["focus"]["isPageHeading"]
    assert_view_mode(result["nav"], "bank")
    assert result["nav"]["hash"] == "#/"
    assert result["browser-back"]["hash"] == record_opened["hash"]
    assert result["browser-back"]["page"] == record_opened["page"]


# --- Content ----------------------------------------------------------------


def assert_pair_content(state: dict, payload, pair) -> None:
    figures = payload["figures"]
    content = state["content"]
    assert state["crumbLabel"] == DECK["G19.crumb.label"]
    assert state["crumbs"][0] == {
        "text": DECK["G19.crumb.bank"],
        "href": "#/",
        "current": None,
        "isLink": True,
    }
    last = state["crumbs"][-1]
    assert last["text"] == fill(DECK["G19.crumb.pair"], n=pair["rank"])
    assert last["current"] == "page" and not last["isLink"]
    assert state["knobs"]["back"]["text"] == DECK["G19.back.bank"]
    assert state["knobs"]["back"]["dataBack"] == "bank" and state["knobs"]["back"]["href"] == "#/"
    engine = payload["engines"][pair["engine"]]
    assert content["eyebrow"].startswith(
        fill(DECK["G19.pair.eyebrow"], n=pair["rank"], engine=engine["short_name"])
    )
    assert content["eyebrowDotHidden"] == "true" and content["eyebrowRole"] == DECK["P06.proposed"]
    assert content["h1"] == heading_text(pair) and content["h1Tabindex"] == "-1"
    assert content["chip"] == pair["label"]
    assert [item["text"] for item in content["numerals"]] == [
        pair["meaning_text"],
        pair["wording_text"],
    ]
    assert [item["caption"] for item in content["numerals"]] == [
        DECK["B08.caption.meaning"],
        DECK["B08.caption.wording"],
    ]
    assert "hub-bank-numeral--meaning" in content["numerals"][0]["classes"]
    assert "hub-bank-numeral--wording" in content["numerals"][1]["classes"]
    assert content["rankScore"] == fill(DECK["B08.rank_score"], z=pair["rank_score_text"])
    assert content["reading"] == pair["reading"]
    assert content["useLabel"] == DECK["B08.use.label"]
    assert content["use"] == DECK["B08.use.label"] + " " + DECK["B08.use." + pair["reading_kind"]]
    assert (
        content["meaningHeading"] == DECK["P03.meaning"] and content["meaningLine"] == DECK["G16"]
    )
    assert content["meaningDetails"] == [
        {"summary": engine["name"], "body": engine["score_meaning"]}
    ]
    assert content["recordsHeading"] == DECK["P03.two"]
    block = content["figureBlock"]
    assert block is not None and block["wrapHidden"] == "true"
    assert canonical(block["svg"]) == canonical(figures["pairs"][pair["key"]]["detail"])
    assert block["caption"] == figures["legend"]["caption"]
    assert block["legendOpen"] is False
    assert block["legendSummary"] == figures["legend"]["summary"]
    assert block["legendBody"] == figures["legend"]["detail"]
    assert len(content["records"]) == 2
    for card, side in zip(content["records"], (pair["left"], pair["right"]), strict=True):
        record = record_of(payload, side["id"])
        assert card["sourceHref"] == side["source_link"] and card["sourceText"] == side["id"]
        assert card["sourceLabel"] == fill(
            DECK["B08.source_name"], ID=side["id"], title=side["title"]
        )
        assert card["titleHref"] == record_route(side["id"]) and card["title"] == side["title"]
        words = record["text"].split()
        if len(words) > 60:
            assert card["excerpt"] == " ".join(words[:60]) + DECK["G19.more"]
        else:
            assert card["excerpt"] == " ".join(words)
        assert card["read"]["text"] == DECK["G19.record.read"]
        assert card["read"]["href"] == record_route(side["id"])
    other = other_engine_pair(payload, pair)
    if other is None:
        assert content["also"] is None
    else:
        short = payload["engines"][other["engine"]]["short_name"]
        assert content["also"]["text"] == fill(DECK["G19.pair.also"], engine=short, n=other["rank"])
        assert content["also"]["href"] == pair_route(other)
    assert state["knobNavCount"] == 2


@pytest.mark.parametrize("browser", BROWSERS)
def test_pair_page_content(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    payload = public_payload()
    third = pair_by_rank(payload, "unusual_pairs", 3)
    both = next(
        p for p in engine_list(payload, "wording_and_meaning") if other_engine_pair(payload, p)
    )
    alone = next(
        p for p in engine_list(payload, "wording_and_meaning") if not other_engine_pair(payload, p)
    )
    result = scenario(
        public_hub(tmp_path),
        browser,
        steps=[
            pages("third", hash=pair_route(third), waitPage="page", content=True),
            pages("both", hash=pair_route(both), waitPage="page", content=True),
            pages("alone", hash=pair_route(alone), waitPage="page", content=True),
            pages(
                "bare",
                deleteKeys=["figures", "terms"],
                hash=pair_route(third),
                waitPage="page",
                content=True,
            ),
        ],
    )
    assert_pair_content(result["third"], payload, third)
    assert_pair_content(result["both"], payload, both)
    assert result["both"]["content"]["also"] is not None
    assert_pair_content(result["alone"], payload, alone)
    assert result["alone"]["content"]["also"] is None
    bare = result["bare"]
    assert bare["page"]["key"] == third["key"]
    assert bare["content"]["figureBlock"] is None and bare["content"]["twin"] is None
    assert bare["content"]["h1"] == heading_text(third)
    assert len(bare["content"]["numerals"]) == 2 and len(bare["content"]["records"]) == 2
    assert bare["siteCounts"]["svg"] == 0
    # A weak pair carries the same hidden wording as its bank row.
    out = built_hub(tmp_path / "weak")
    synthetic = build_payload(load_run(tmp_path / "weak" / "run"))
    weak = next((p for p in synthetic["pairs"] if p["weak"]), None)
    assert weak is not None, "the synthetic run has a weak pair"
    state = scenario(
        out, browser, steps=[pages("weak", hash=pair_route(weak), waitPage="page", content=True)]
    )["weak"]
    assert state["content"]["hiddenLabel"] == DECK["P06.hidden"]
    assert state["content"]["chip"] == weak["label"]


def twin_holds(twin_text: str, needle: str) -> bool:
    return needle.lower() in twin_text.lower()


@pytest.mark.parametrize("browser", BROWSERS)
def test_twin_text_and_visibility(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    payload = public_payload()
    terms, figures = payload["terms"], payload["figures"]
    first = pair_by_rank(payload, "unusual_pairs", 1)
    shared = next(p for p in payload["pairs"] if len(terms["pairs"].get(p["pair_id"], [])) >= 2)
    steps = [
        pages("first", hash=pair_route(first), waitPage="page", content=True),
        pages("shared", hash=pair_route(shared), waitPage="page", content=True),
    ]
    for width in (390, 767, 768, 1280, 1600):
        steps += [viewport(width), pages(f"w{width}", content=True, metrics=True)]
    result = scenario(public_hub(tmp_path), browser, steps=steps)
    for name, pair in (("first", first), ("shared", shared)):
        content = result[name]["content"]
        twin, block = content["twin"], content["figureBlock"]
        assert twin is not None and twin["ariaHidden"] is None
        assert twin["heading"] == DECK["G19.twin.heading"]
        text = twin["text"]
        for side in (pair["left"], pair["right"]):
            assert twin_holds(text, side["title"])
            for word in terms["records"][side["id"]]:
                assert twin_holds(text, word), word
        shared_words = terms["pairs"].get(pair["pair_id"], [])
        if shared_words:
            assert twin_holds(text, ", ".join(shared_words))
        else:
            assert twin_holds(text, figures["labels"]["none_shared"])
        for label in figures["labels"].values():
            if label != figures["labels"]["none_shared"] or not shared_words:
                assert twin_holds(text, label), label
        assert twin_holds(text, pair["meaning_text"]) and twin_holds(text, pair["wording_text"])
        assert block["desc"] and twin_holds(text, block["desc"])
        assert twin["desc"] == block["desc"]
        for drawn in block["texts"]:
            value = drawn[:-3] if drawn.endswith("...") else drawn
            if re.fullmatch(r"\d+\.\d\d", value):
                # The drawing rounds the score to 2 decimals; the twin shows the payload text.
                assert any(
                    abs(float(value) - float(number)) < 0.005 + 1e-9
                    for number in (pair["meaning_text"], pair["wording_text"])
                ), value
                continue
            assert twin_holds(text, value), value
    for width in (390, 767):
        state = result[f"w{width}"]
        twin, block = state["content"]["twin"], state["content"]["figureBlock"]
        assert twin["display"] != "none" and twin["box"]["rects"] > 0 and twin["box"]["width"] > 1
        assert block["wrapDisplay"] == "none"
    for width in (768, 1280, 1600):
        state = result[f"w{width}"]
        twin, block = state["content"]["twin"], state["content"]["figureBlock"]
        assert block["wrapDisplay"] == "block" and block["svgBox"]["width"] >= 600, (
            width,
            block["svgBox"],
        )
        assert twin["display"] != "none" and twin["visibility"] != "hidden"
        assert twin["box"]["width"] <= 1 and twin["box"]["height"] <= 1, (width, twin["box"])
        assert twin["clipPath"] == "inset(50%)" and twin["position"] == "absolute"


def test_detail_text_fits_in_a_real_browser(tmp_path: Path) -> None:
    require_browser()
    payload = public_payload()
    terms = payload["terms"]
    longest = max(
        payload["pairs"], key=lambda p: len(p["left"]["title"]) + len(p["right"]["title"])
    )
    none_shared = next(p for p in payload["pairs"] if not terms["pairs"].get(p["pair_id"]))
    six = max(payload["pairs"], key=lambda p: len(terms["pairs"].get(p["pair_id"], [])))
    first = payload["pairs"][0]
    cases = {"longest": longest, "none": none_shared, "six": six, "first": first}
    steps = [viewport(1280)]
    for name, pair in cases.items():
        steps += [pages(name, hash=pair_route(pair), waitPage="page"), fit(name + "-fit")]
    result = scenario(public_hub(tmp_path), steps=steps)
    scale_out = built_hub(tmp_path, n_records=40, pairs_per_engine=40)
    scale = build_payload(load_run(tmp_path / "run"))
    scale_longest = max(
        scale["pairs"], key=lambda p: len(p["left"]["title"]) + len(p["right"]["title"])
    )
    scale_result = scenario(
        scale_out,
        steps=[
            viewport(1280),
            pages("scale-first", hash=pair_route(scale["pairs"][0]), waitPage="page"),
            fit("scale-first-fit"),
            pages("scale-longest", hash=pair_route(scale_longest), waitPage="page"),
            fit("scale-longest-fit"),
        ],
    )
    measured = {
        name: value for name, value in {**result, **scale_result}.items() if name.endswith("-fit")
    }
    advances: dict[str, list[float]] = {}
    ratios = []
    for name, data in measured.items():
        assert data["found"], name
        assert all(data["fonts"].values()), (name, data["fonts"])
        assert data["rendered"] >= 600
        for item in data["items"]:
            assert item["insideCanvas"], (name, item["text"], item["box"])
            assert item["insideContainer"], (
                name,
                item["kind"],
                item["text"],
                item["box"],
                item["container"],
            )
        assert data["overlaps"] == [], (name, data["overlaps"])
        ratios.append(data["maxRatio"])
        for face, stats in data["advances"].items():
            advances.setdefault(face, []).extend([stats["min"], stats["max"]])
    summary = {
        "max_width_ratio": max(ratios),
        "advance": {
            face: {"min": min(values), "max": max(values)} for face, values in advances.items()
        },
    }
    print("DETAIL FIT " + json.dumps(summary, sort_keys=True))


@pytest.mark.parametrize("browser", BROWSERS)
def test_record_page_content(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    payload = public_payload()
    record = payload["records"][0]
    pairs = {pair["key"]: pair for pair in payload["pairs"]}
    state = scenario(
        public_hub(tmp_path),
        browser,
        steps=[pages("record", hash=record_route(record["id"]), waitPage="page", content=True)],
    )["record"]
    content = state["content"]
    assert state["crumbs"][0] == {
        "text": DECK["G19.crumb.catalogue"],
        "href": "#/catalogue",
        "current": None,
        "isLink": True,
    }
    assert state["crumbs"][-1]["text"] == record["id"] and state["crumbs"][-1]["current"] == "page"
    assert state["knobs"]["back"]["text"] == DECK["G19.back.catalogue"]
    assert state["knobs"]["back"]["dataBack"] == "catalogue"
    assert state["knobs"]["position"] == fill(
        DECK["G19.pos.record"], n=1, k=len(payload["records"])
    )
    assert state["title"] == fill(DECK["G19.doc.record"], title=record["title"])
    assert content["eyebrow"] == DECK["G19.record.eyebrow"] and content["h1"] == record["title"]
    assert content["chip"] == record["label"]
    source = content["source"]
    assert record["id"] in source["text"] and record["source_file"] in source["text"]
    assert record["source_ref"] in source["text"]
    assert DECK["P04.file"] in source["text"] and DECK["P04.ref"] in source["text"]
    assert source["linkHref"] == record["source_link"] and source["linkText"] == DECK["P05.open"]
    assert source["linkCount"] == 1 and "JetBrains" in source["mono"]
    assert content["textHeading"] == DECK["P03.text"]
    assert content["paragraphs"] and max(len(p.split()) for p in content["paragraphs"]) <= 100
    assert " ".join(" ".join(content["paragraphs"]).split()) == " ".join(record["text"].split())
    assert content["wordsHeading"] == DECK["G19.record.words"]
    assert (
        content["words"] == payload["terms"]["records"][record["id"]] and content["noWords"] is None
    )
    assert content["pairsHeading"] == fill(DECK["P03.pairs"], n=len(record["pair_keys"]))
    assert len(content["pairs"]) == len(record["pair_keys"]) and content["noPairs"] is None
    for item, key in zip(content["pairs"], record["pair_keys"], strict=True):
        pair = pairs[key]
        partner = pair["right"] if pair["left"]["id"] == record["id"] else pair["left"]
        assert item["thumbHidden"] == "true" and abs(item["thumbBox"]["width"] - 96) < 1
        assert canonical(item["thumbSvg"]) == canonical(payload["figures"]["pairs"][key]["card"])
        assert item["pairLink"]["href"] == pair_route(pair)
        assert item["pairLink"]["text"] == fill(DECK["B08.rank"], n=pair["rank"])
        assert item["engine"] == payload["engines"][pair["engine"]]["short_name"]
        assert (
            item["partner"]["href"] == record_route(partner["id"])
            and item["partner"]["text"] == partner["title"]
        )
        assert [n["text"] for n in item["numerals"]] == [pair["meaning_text"], pair["wording_text"]]
        assert [n["caption"] for n in item["numerals"]] == [
            DECK["B08.caption.meaning"],
            DECK["B08.caption.wording"],
        ]
    assert content["flags"] == []
    # A hostile run with copies and an empty record: the data-check lines show, no words shows.
    out = built_hub(tmp_path, hostile=True, copies=2, empty_text=1)
    hostile = build_payload(load_run(tmp_path / "run"))
    copy = next(r for r in hostile["records"] if r["identical_to"])
    empty = next(r for r in hostile["records"] if r["no_text"])
    result = scenario(
        out,
        browser,
        steps=[
            pages("copy", hash=record_route(copy["id"]), waitPage="page", content=True),
            pages("empty", hash=record_route(empty["id"]), waitPage="page", content=True),
        ],
    )
    assert (
        fill(DECK["P09.identical"], ID=copy["identical_to"][0])
        in result["copy"]["content"]["flags"]
    )
    assert DECK["P09.no_text"] in result["empty"]["content"]["flags"]
    assert (
        result["empty"]["content"]["words"] == []
        and result["empty"]["content"]["noWords"] == DECK["G19.record.no_words"]
    )
    # A record in no pair.
    out = built_hub(tmp_path / "few", n_records=30, pairs_per_engine=2)
    few = build_payload(load_run(tmp_path / "few" / "run"))
    lonely = next(r for r in few["records"] if not r["pair_keys"])
    state = scenario(
        out,
        browser,
        steps=[pages("lonely", hash=record_route(lonely["id"]), waitPage="page", content=True)],
    )["lonely"]
    assert (
        state["content"]["pairs"] == []
        and state["content"]["noPairs"] == DECK["G19.record.no_pairs"]
    )


# --- Look, targets, themes, motion ------------------------------------------


def test_targets_text_size_and_themes(tmp_path: Path) -> None:
    """Prototype check 24: the knobs are 44 px; and the 13 px floor and both themes."""
    require_browser()
    payload = public_payload()
    first = pair_by_rank(payload, "unusual_pairs", 1)
    record = payload["records"][0]
    out = public_hub(tmp_path)
    steps = []
    for width in WIDTHS:
        steps += [
            viewport(width),
            pages(f"pair-{width}", hash=pair_route(first), waitPage="page", metrics=True),
            pages(
                f"record-{width}", hash=record_route(record["id"]), waitPage="page", metrics=True
            ),
        ]
    result = scenario(out, steps=steps)
    for name, state in result.items():
        metrics = state["metrics"]
        assert metrics["scrollWidth"] <= metrics["innerWidth"], name
        assert metrics["small"] == [] and metrics["minimum"] >= 13, (name, metrics["small"])
        assert metrics["targets"], name
        for target in metrics["targets"]:
            assert target["height"] >= 43.9, (name, target)
            if target["isKnob"]:
                assert target["width"] >= 43.9, (name, target)
        assert (
            metrics["ring"]["outlineWidth"] == "3px" and metrics["ring"]["outlineStyle"] == "solid"
        ), (name, metrics["ring"])
        assert state["knobs"]["prevOff"] is not None, name
    for theme in ("light", "dark"):
        steps = []
        for width in (390, 1280):
            steps += [
                viewport(width),
                pages(
                    f"pair-{width}",
                    theme=theme,
                    hash=pair_route(first),
                    waitPage="page",
                    settle=400,
                ),
                {"kind": "eval", "file": CONTRAST, "as": f"pair-{width}-contrast"},
                pages(
                    f"record-{width}", hash=record_route(record["id"]), waitPage="page", settle=400
                ),
                {"kind": "eval", "file": CONTRAST, "as": f"record-{width}-contrast"},
            ]
        result = scenario(out, steps=steps)
        for name, measured in result.items():
            if name.endswith("-contrast"):
                assert measured["checked"] > 0
                assert measured["failures"] == [] and measured["yellow"] == [], (
                    theme,
                    name,
                    measured["failures"],
                )
    system = scenario(
        out,
        colorScheme="dark",
        steps=[
            viewport(1280),
            pages("pair", hash=pair_route(first), waitPage="page", settle=400),
            {"kind": "eval", "file": CONTRAST, "as": "contrast"},
        ],
    )
    assert system["contrast"]["failures"] == [] and system["contrast"]["yellow"] == []


@pytest.mark.parametrize("browser", BROWSERS)
def test_reduced_motion_and_scroll(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    payload = public_payload()
    third = pair_by_rank(payload, "unusual_pairs", 3)
    result = scenario(
        public_hub(tmp_path),
        browser,
        reducedMotion=True,
        steps=[
            pages("start", scroll=600),
            pages("page", hash=pair_route(third), waitPage="page", metrics=True),
        ],
    )
    assert result["start"]["scrollY"] >= 500 and result["start"]["reduced"] is True
    state = result["page"]
    assert state["animations"] == 0 and state["scrollY"] == 0
    assert state["metrics"]["knobTransition"] == "0s"


def test_routes_are_local_and_deterministic(tmp_path: Path) -> None:
    first, second = build(tmp_path, "one"), build(tmp_path, "two")
    assert tree_hash(first) == tree_hash(second)
    data = payload_of_build(first)
    assert verify_payload(data) == []
    assert set(data) == PAYLOAD_KEYS
