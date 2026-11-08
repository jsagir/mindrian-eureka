"""Pin the look, the links, the figures and the header wiring of the graph, catalogue and panel.

Phase 2.3.1 plan 07. Every header-dependent size reads the measured header height. Colours are
the book tokens, so the stage follows the theme of plan 05 when its tokens exist.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import pytest
from hub_browser_support import require_browser
from mindrian_eureka.hub.deck import DECK, fill
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run
from test_hub_browser_core import CHECKS, METRICS, built_hub, scenario
from test_hub_browser_graph import positive_hub
from test_hub_browser_review import CONTRAST, PUBLIC, SPACING, public_hub

LOOK = str(CHECKS / "views-look.js")
INK = "rgb(17, 17, 17)"
PAPER = "rgb(247, 245, 238)"
COBALT = "rgb(31, 63, 191)"
SOFT = "rgb(75, 73, 67)"
LINE = "rgb(199, 198, 191)"
WHITE = "rgb(255, 255, 255)"
ENGINES = ["unusual_pairs", "wording_and_meaning"]
# The characters that encodeURIComponent keeps, so Python and the browser agree on a route.
URI_SAFE = "-_.!~*'()"


def look(name: str, **args):
    return {"kind": "eval", "file": LOOK, "as": name, "args": args}


def route_record(record_id: str) -> str:
    return "#/record/" + quote(record_id, safe=URI_SAFE)


def best_shown_pair(payload, record):
    pairs = {pair["key"]: pair for pair in payload["pairs"]}
    shown = [pairs[key] for key in record["pair_keys"] if not pairs[key]["weak"]]
    shown.sort(key=lambda pair: (pair["rank"], ENGINES.index(pair["engine"]), pair["key"]))
    return shown[0] if shown else None


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_header_variable_wiring(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    steps = []
    for width in (1024, 1280, 1600):
        steps += [{"kind": "setViewport", "width": width, "height": 900},
                  look(f"catalogue-{width}", view="catalogue"),
                  look(f"graph-{width}", view="graph", waitGraph=True),
                  look(f"panel-{width}", view="bank", pair=True),
                  look(f"clear-{width}", clear=True)]
    result = scenario(public_hub(tmp_path), browser, steps=steps)
    for width in (1024, 1280, 1600):
        catalogue = result[f"catalogue-{width}"]
        header_var = catalogue["headerVar"]
        assert header_var > 0 and header_var == catalogue["header"]["height"]
        assert catalogue["catalogue"]["headPosition"] == "sticky"
        assert catalogue["catalogue"]["headTop"] == f"{header_var:g}px"
        graph = result[f"graph-{width}"]
        assert graph["stage"]["mode"] == "3d"
        assert abs(graph["stage"]["box"]["height"] - (900 - graph["headerVar"])) < 0.51
        panel = result[f"panel-{width}"]
        assert panel["panel"]["open"] and panel["panel"]["position"] == "fixed"
        assert abs(panel["panel"]["bounds"]["top"] - (panel["headerVar"] + 16)) < 0.51
        assert panel["panel"]["bounds"]["top"] >= panel["header"]["bottom"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_graph_guide_look(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    steps = []
    for width in (768, 1280, 390):
        steps += [{"kind": "setViewport", "width": width, "height": 900},
                  look(str(width), view="graph", waitGraph=True)]
    steps.append(look("toggled", toggleGuide=True))
    result = scenario(public_hub(tmp_path), browser, webgl=False, steps=steps)
    for width in (768, 1280):
        guide = result[str(width)]["guide"]
        assert guide["borderTopWidth"] == "1px" and guide["borderTopStyle"] == "solid"
        assert guide["borderTopColor"] == INK
        assert guide["backgroundColor"] == PAPER
        assert guide["padding"] == "24px"
        assert guide["expanded"] == "true" and guide["bodyHidden"] is False
        assert guide["legendSizes"] and all(size == 16 for size in guide["legendSizes"])
        assert guide["paragraphSizes"] and all(size == 16 for size in guide["paragraphSizes"])
        assert guide["linkColors"] and all(color == COBALT for color in guide["linkColors"])
    phone = result["390"]["guide"]
    assert phone["expanded"] == "false" and phone["bodyHidden"] is True
    assert phone["toggleBox"]["height"] >= 44
    toggled = result["toggled"]["guide"]
    assert toggled["expanded"] == "true" and toggled["bodyHidden"] is False
    assert result["390"]["scrollWidth"] <= 390


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_graph_follows_the_theme(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    result = scenario(positive_hub(tmp_path), browser, steps=[
        look("light", view="graph", waitGraph=True),
        look("selected", record="synthetic-b-000"),
        look("dark", clear=True, theme="dark"),
        look("back", theme="light")])
    light = result["light"]["stage"]["colors"]
    assert result["light"]["stage"]["mode"] == "3d"
    assert light["background"].lower() == "#f7f5ee"
    assert light["bridge"].lower() == "#f2c200"
    assert light["links"] and all(color.lower() == "#1f3fbf" for color in light["links"])
    assert light["shells"] and all(shell == "111111" for shell in light["shells"])
    selected = result["selected"]["stage"]["colors"]
    assert any(color.lower() == "#d8d4c8" for color in selected["nodes"])
    assert any(color.lower() == "#d8d4c8" for color in selected["links"])
    tokens = result["dark"]["tokens"]
    if not tokens["hasTheme"]:
        pytest.skip("theme tokens missing")
    dark = result["dark"]["stage"]["colors"]
    assert tokens["theme"] == "dark"
    assert dark["background"].lower() == tokens["paper"].lower()
    assert dark["links"] and all(color.lower() == tokens["blue"].lower() for color in dark["links"])
    assert dark["bridge"].lower() == tokens["yellow"].lower()
    # The refresh does not move the camera.
    assert dark["position"] == selected["position"]
    back = result["back"]["stage"]["colors"]
    assert back["background"].lower() == "#f7f5ee"
    assert all(color.lower() == "#1f3fbf" for color in back["links"])


def test_catalogue_look(tmp_path: Path) -> None:
    require_browser()
    steps = []
    for width in (1280, 390):
        steps += [{"kind": "setViewport", "width": width, "height": 900},
                  look(str(width), view="catalogue"),
                  {"kind": "eval", "file": METRICS, "as": f"metrics-{width}"}]
    result = scenario(public_hub(tmp_path), steps=steps)
    wide = result["1280"]["catalogue"]
    assert "JetBrains Mono" in wide["th"]["fontFamily"]
    assert wide["th"]["fontSize"] == "13px" and wide["th"]["fontWeight"] == "600"
    assert wide["th"]["color"] == SOFT
    assert wide["th"]["borderBottomWidth"] == "1px" and wide["th"]["borderBottomColor"] == INK
    assert wide["rowCell"]["borderBottomWidth"] == "1px"
    assert wide["rowCell"]["borderBottomColor"] == LINE
    assert "Figtree" in wide["title"]["fontFamily"]
    assert wide["title"]["fontWeight"] == "700" and wide["title"]["fontSize"] == "18px"
    assert wide["title"]["color"] == INK and wide["title"]["backgroundColor"] == "rgba(0, 0, 0, 0)"
    assert wide["idLink"]["color"] == COBALT and "JetBrains Mono" in wide["idLink"]["fontFamily"]
    assert wide["idLink"]["fontSize"] == "13px"
    assert result["1280"]["scrollWidth"] <= 1280
    phone = result["390"]["catalogue"]
    assert phone["rows"]
    for row in phone["rows"]:
        assert row["idText"] and row["titleText"] and row["fileText"] and row["countText"]
        assert row["cellsVisible"][:3] == [True, True, True]
    assert result["390"]["scrollWidth"] <= 390
    for width in (1280, 390):
        assert result[f"metrics-{width}"]["minimum"] >= 13
        assert result[f"metrics-{width}"]["targets"] == []


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_catalogue_open_link_and_thumbnails(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    payload = build_payload(load_run(PUBLIC))
    result = scenario(public_hub(tmp_path), browser, steps=[
        look("rows", view="catalogue", more=1),
        {"kind": "click", "selector": "#catalogue-list tbody tr:first-child button"},
        look("opened")])
    rows = result["rows"]["catalogue"]["rows"]
    assert len(rows) == len(payload["records"]) == 36
    records = {record["id"]: record for record in payload["records"]}
    with_figure = 0
    for row in rows:
        record = records[row["id"]]
        assert row["openCount"] == 1
        assert row["open"]["text"] == fill(DECK["C07.open"], ID=row["id"])
        assert row["open"]["href"] == route_record(row["id"])
        assert row["open"]["box"]["height"] >= 44
        assert row["sourceLinks"] == [record["source_link"]]
        assert row["countText"]
        best = best_shown_pair(payload, record)
        if best is None:
            assert row["figureCount"] == 0 and row["expectedKey"] is None
            continue
        with_figure += 1
        assert row["figureCount"] == 1
        figure = row["figure"]
        assert figure["ariaHidden"] == "true" and figure["links"] == 0
        assert figure["pairKey"] == best["key"] == row["expectedKey"]
        assert figure["svgCount"] == 1 and figure["hasClass"]
        assert abs(figure["width"] - 96) < 0.51
        assert figure["serialised"] == row["expectedCard"]
    assert with_figure > 0
    opened = result["opened"]
    assert opened["panel"]["open"]
    assert opened["panel"]["selection"] == {"type": "record", "id": rows[0]["id"]}
    # A record in no shown pair has no thumbnail.
    sparse = scenario(built_hub(tmp_path / "sparse", n_records=40, pairs_per_engine=3), browser,
                      steps=[look("rows", view="catalogue")])["rows"]["catalogue"]["rows"]
    assert len(sparse) == 40
    assert sum(row["figureCount"] for row in sparse) == sum(
        1 for row in sparse if row["expectedKey"] is not None)
    assert any(row["figureCount"] == 0 for row in sparse)
    assert any(row["figureCount"] == 1 for row in sparse)
    # Hostile ids are percent-encoded in the route.
    hostile = scenario(built_hub(tmp_path / "hostile", hostile=True, n_records=40), browser,
                       steps=[look("rows", view="catalogue")])["rows"]["catalogue"]["rows"]
    ids = {row["id"] for row in hostile}
    assert {"bank", "hub-results", "__proto__"} <= ids
    for row in hostile:
        assert row["open"]["href"] == route_record(row["id"])
        assert row["open"]["text"] == fill(DECK["C07.open"], ID=row["id"])


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_panel_figure_and_open_link(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    payload = build_payload(load_run(PUBLIC))
    legend = payload["figures"]["legend"]
    result = scenario(public_hub(tmp_path), browser, steps=[
        look("pair", view="bank", pair=True),
        {"kind": "press", "selector": "#hub-panel details.hub-panel-legend summary",
         "key": "Enter"},
        look("legend"),
        look("record", recordIndex=0)])
    pair = result["pair"]
    assert pair["panel"]["open"] and pair["panel"]["focusId"] == "hub-panel-title"
    chosen = pair["selectedPair"]
    assert pair["panel"]["figureCount"] == 1
    figure = pair["panel"]["figure"]
    assert figure["containerAriaHidden"] is None and figure["ariaHidden"] is None
    assert figure["svgCount"] == 1 and figure["role"] == "img"
    assert figure["title"].strip() and figure["desc"].strip()
    assert figure["serialised"] == pair["panel"]["expectedCard"]
    assert figure["width"] > 200
    assert pair["panel"]["legendCount"] == 1
    assert pair["panel"]["legend"]["open"] is False
    assert pair["panel"]["legend"]["summary"] == legend["summary"]
    assert pair["panel"]["legend"]["body"] == [legend["card"]]
    assert pair["panel"]["legend"]["bodyVisible"] is False
    assert pair["panel"]["legend"]["summaryBox"]["height"] >= 44
    assert pair["panel"]["pageLinks"] == [{
        **pair["panel"]["pageLinks"][0], "text": DECK["P05.page"],
        "href": f'#/pair/{chosen["engine"]}/{chosen["rank"]}'}]
    assert pair["panel"]["pageLinks"][0]["box"]["height"] >= 44
    opened = result["legend"]["panel"]["legend"]
    assert opened["open"] is True and opened["bodyVisible"] is True
    record = result["record"]["panel"]
    first = payload["records"][0]
    assert record["selection"] == {"type": "record", "id": first["id"]}
    assert record["figureCount"] == 0 and record["legendCount"] == 0
    assert [link["href"] for link in record["pageLinks"]] == [route_record(first["id"])]
    assert record["pageLinks"][0]["text"] == DECK["P05.page"]


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_graph_pair_list_open_link(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    result = scenario(positive_hub(tmp_path), browser, webgl=False, steps=[
        look("rows", view="graph", waitGraph=True),
        {"kind": "click", "selector": ".hub-graph-pair button"},
        look("read")])
    rows = result["rows"]["graphRows"]
    assert len(rows) == 25
    for row in rows:
        assert row["openCount"] == 1 and row["readButton"]
        assert row["open"]["text"] == DECK["Gr16.open"]
        assert row["open"]["href"] == f'#/pair/{row["engine"]}/{row["rank"]}'
        assert row["open"]["box"]["height"] >= 44
        assert row["open"]["style"]["color"] == COBALT
        assert len(row["sourceLinks"]) == 2
    assert result["read"]["panel"]["open"]
    assert result["read"]["panel"]["selection"]["type"] == "pair"
    assert result["read"]["panel"]["selection"]["key"] == rows[0]["key"]


@pytest.mark.parametrize("width", [390, 1280])
def test_panel_look(tmp_path: Path, width: int) -> None:
    require_browser()
    steps = [look("light", view="bank", pair=True),
             {"kind": "eval", "file": METRICS, "as": "metrics-light"},
             {"kind": "eval", "file": CONTRAST, "as": "contrast-light"},
             # The theme of plan 05 transitions colours (the reframe token is 760 ms), so the
             # dark measurements wait for the settled values.
             look("dark", theme="dark"), {"kind": "wait", "ms": 1000},
             {"kind": "eval", "file": METRICS, "as": "metrics-dark"},
             {"kind": "eval", "file": CONTRAST, "as": "contrast-dark"},
             look("back", theme="light"), {"kind": "wait", "ms": 1000},
             {"kind": "eval", "file": SPACING, "as": "spacing"}]
    result = scenario(public_hub(tmp_path), viewport={"width": width, "height": 900}, steps=steps)
    panel = result["light"]["panel"]
    assert panel["open"]
    assert panel["background"] == WHITE
    assert panel["borderWidth"] == "1px" and panel["borderStyle"] == "solid"
    assert panel["borderColor"] == INK
    assert panel["evidence"] and all(
        item == {"width": "3px", "color": COBALT} for item in panel["evidence"])
    assert panel["sourceLinkColors"] and all(color == COBALT for color in panel["sourceLinkColors"])
    roles = {item["class"]: item for item in panel["roles"]}
    assert "repeating-linear-gradient" in roles["hub-role hub-role--proposed"]["image"]
    assert "repeating-linear-gradient" in roles["hub-role hub-role--inferred"]["image"]
    assert roles["hub-role hub-role--source"]["border"] == "2px"
    assert panel["minFont"] >= 13
    themes = ["light"]
    if result["dark"]["tokens"]["hasTheme"]:
        themes.append("dark")
    for theme in themes:
        assert result[f"metrics-{theme}"]["minimum"] >= 13
        assert result[f"metrics-{theme}"]["targets"] == []
        contrast = result[f"contrast-{theme}"]
        assert contrast["checked"] > 0
        assert contrast["failures"] == [] and contrast["yellow"] == [], (theme, contrast)
    assert result["spacing"]["clipped"] == [] and result["spacing"]["scrollWidth"] <= width
    if width < 1024:
        assert panel["bounds"]["height"] <= 900 * 0.62 + 1
    else:
        assert panel["bounds"]["width"] == 400


@pytest.mark.parametrize("browser", ["chromium", "firefox"])
def test_reduced_motion_and_no_network(tmp_path: Path, browser: str) -> None:
    require_browser(browser)
    result = scenario(public_hub(tmp_path), browser, reducedMotion=True, steps=[
        look("bank", view="bank", pair=True),
        look("graph", view="graph", waitGraph=True),
        look("catalogue", view="catalogue"),
        look("record", recordIndex=0)])
    for name in ("bank", "graph", "catalogue", "record"):
        assert result[name]["reduced"] is True
        assert result[name]["animations"] == 0
    assert result["graph"]["stage"]["mode"] == "3d"
    assert result["record"]["panel"]["open"]
