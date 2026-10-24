"""Render escaped HTML for local opportunity hubs.

Import rule: standard library, `.contracts`, and `.deck` only. No numpy.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from html import escape
from urllib.parse import urlsplit

from .contracts import (
    ENGINE_KEYS,
    FACE_FILES,
    LOCKUP_FILE,
    NOSCRIPT_PAIRS_PER_ENGINE,
    NOSCRIPT_RECORDS,
    VIEW_NAMES,
    PairSide,
    Payload,
    PayloadPair,
    PayloadRecord,
    deep_link,
)
from .deck import DECK, fill

CONTENT_SECURITY_POLICY: str | None = (
    "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; "
    "font-src 'self'; connect-src 'none'"
)
STYLE_ORDER = (
    "tokens.css",
    "hub.css",
    "hub-bank.css",
    "hub-catalogue.css",
    "hub-panel.css",
    "hub-graph.css",
    "hub-gate.css",
)
# Runtime inventory for view, engine, column, cut-off and legend key loops.
# Payload-backed status and registered engine names are equality-checked by copy coverage.
# deck keys: B03.both B03.unusual_pairs B03.wording_and_meaning
# deck keys: B05.one.unusual_pairs B05.one.wording_and_meaning
# deck keys: C06.file C06.id C06.pairs C06.title G01.catalogue G01.graph G08
# deck keys: G09.bank.short G09.catalogue.long G09.catalogue.short G09.graph.long G09.graph.short
# deck keys: G11.hoods G11.records G11.unusual_pairs G11.wording_and_meaning
# deck keys: G15.unusual_pairs G15.unusual_pairs.short
# deck keys: G15.wording_and_meaning G15.wording_and_meaning.short
# deck keys: Gr03.crossing Gr03.eureka Gr03.record Gr03.selected
# deck keys: Gr03.unusual_pairs Gr03.wording_and_meaning P06.source

SCRIPT_ORDER = (
    "hub-copy.js",
    "hub-data.js",
    "hub-core.js",
    "hub-bank.js",
    "hub-catalogue.js",
    "hub-panel.js",
    "hub-graph.js",
    "hub-gate.js",
)
_VOID_TAGS = frozenset({"meta", "link", "img", "input"})


def _h(value: object) -> str:
    return escape(str(value), quote=True)


def _copy(key: str, **values: object) -> str:
    return _h(fill(DECK[key], **values))


def _local_url(value: str) -> str:
    if value.startswith("#"):
        return value
    parsed = urlsplit(value)
    if not value or value.startswith(("/", "\\")) or parsed.scheme or parsed.netloc:
        raise ValueError("Hub links must be relative local URLs")
    return value


def _el(tag: str, content: str = "", attrs: Mapping[str, object] | None = None) -> str:
    attributes = []
    for key, value in (attrs or {}).items():
        if value is None or value is False:
            continue
        if value is True:
            attributes.append(f" {key}")
        else:
            text = _local_url(str(value)) if key in ("href", "src") else str(value)
            attributes.append(f' {key}="{_h(text)}"')
    opening = f"<{tag}{''.join(attributes)}>"
    return opening if tag in _VOID_TAGS else opening + content + f"</{tag}>"


def _head(files: Collection[str], csp: str | None, *, gated: bool) -> str:
    parts = [_el("meta", attrs={"charset": "utf-8"})]
    if csp is not None:
        parts.append(_el("meta", attrs={"http-equiv": "Content-Security-Policy", "content": csp}))
    parts.extend(
        [
            _el(
                "meta", attrs={"name": "viewport", "content": "width=device-width, initial-scale=1"}
            ),
            _el("title", _copy("G01.locked" if gated else "G01.bank")),
        ]
    )
    for name, size in (
        ("assets/favicon.svg", None),
        *((f"assets/favicon-{size}.png", f"{size}x{size}") for size in (16, 32, 48, 180)),
    ):
        if name in files:
            parts.append(_el("link", attrs={"rel": "icon", "href": name, "sizes": size}))
    for name in STYLE_ORDER:
        if name in files and (gated or name != "hub-gate.css"):
            parts.append(_el("link", attrs={"rel": "stylesheet", "href": name}))
    if "hub-boot.js" in files:
        parts.append(_el("script", attrs={"src": "hub-boot.js"}))
    return _el("head", "\n".join(parts))


def _source_anchor(side: PairSide) -> str:
    name = fill(DECK["B08.source_name"], ID=side["id"], title=side["title"])
    return _el(
        "a",
        _el("bdi", _h(side["id"])),
        {
            "href": side["source_link"],
            "title": name,
            "aria-label": name,
        },
    )


def _pair_row(pair: PayloadPair, records: Mapping[str, PayloadRecord]) -> str:
    parts = [
        _el(
            "p",
            _copy("B08.rank", n=pair["rank"]) + " " + _copy(f"G15.{pair['engine']}.short"),
            {"class": "hub-pair-rank"},
        ),
        _el("span", _copy("P06.proposed"), {"class": "hub-role hub-role-proposed"}),
        _el("span", _h(pair.get("label", "")), {"class": "hub-label"}),
    ]
    for side in (pair["left"], pair["right"]):
        parts.append(
            _el("p", _source_anchor(side) + " " + _h(side["title"]), {"class": "hub-pair-record"})
        )
    scores = [
        _copy("B08.wording", x=pair["wording_text"]),
        _copy("B08.meaning", y=pair["meaning_text"]),
        _copy("B08.rank_score", z=pair["rank_score_text"]),
    ]
    parts.append(
        _el("div", "".join(_el("p", score) for score in scores), {"class": "hub-pair-scores"})
    )
    parts.append(_el("p", _h(pair["reading"]), {"class": "hub-reading"}))
    for side in (pair["left"], pair["right"]):
        record = records[side["id"]]
        if pair["flag_identical"] and record["identical_to"]:
            parts.append(
                _el(
                    "p",
                    _h(record["id"]) + ": " + _copy("P09.identical", ID=record["identical_to"][0]),
                    {"class": "hub-flag"},
                )
            )
        if pair["flag_no_text"] and record["no_text"]:
            parts.append(
                _el("p", _h(record["id"]) + ": " + _copy("P09.no_text"), {"class": "hub-flag"})
            )
    return _el(
        "li",
        "".join(parts),
        {
            "class": "hub-pair-row",
            "data-pair-key": pair["key"],
            "data-engine": pair["engine"],
        },
    )


def _engine_lists(payload: Payload) -> str:
    records = {record["id"]: record for record in payload["records"]}
    result: list[str] = []
    for key in ENGINE_KEYS:
        pairs = sorted(
            (pair for pair in payload["pairs"] if pair["engine"] == key and not pair["weak"]),
            key=lambda pair: (pair["rank"], pair["pair_id"]),
        )
        result.append(_el("h3", _copy(f"G15.{key}")))
        result.append(
            _el(
                "ol",
                "".join(_pair_row(pair, records) for pair in pairs[:NOSCRIPT_PAIRS_PER_ENGINE]),
                {"data-engine-list": key},
            )
        )
        if not pairs:
            result.extend(_el("p", _h(note)) for note in payload["engines"][key]["notes"])
        if len(pairs) > NOSCRIPT_PAIRS_PER_ENGINE:
            result.append(_el("p", _copy("B14"), {"class": "hub-noscript-pointer"}))
    return "".join(result)


def _cutoffs(payload: Payload) -> str:
    engines = payload["engines"]
    if all(engines[key]["floor"] is not None for key in ENGINE_KEYS):
        return _el(
            "p",
            _copy(
                "B05",
                floor_unusual_pairs=engines["unusual_pairs"]["floor_text"],
                floor_wording_and_meaning=engines["wording_and_meaning"]["floor_text"],
            ),
        )
    return "".join(
        _el(
            "p",
            _copy(f"B05.one.{key}", floor=engines[key]["floor_text"])
            if engines[key]["floor"] is not None
            else _copy("B06"),
        )
        for key in ENGINE_KEYS
    )


def _catalogue(payload: Payload) -> str:
    headings = "".join(
        _el("th", _copy(f"C06.{key}"), {"scope": "col"}) for key in ("id", "title", "file", "pairs")
    )
    rows: list[str] = []
    for record in payload["records"][:NOSCRIPT_RECORDS]:
        count = record["pair_count"]
        count_text = (
            _copy("C06.no_pairs")
            if count == 0
            else (_copy("C06.one_pair") if count == 1 else _copy("C06.n_pairs", n=count))
        )
        row = _el(
            "td",
            _el(
                "a",
                _el("bdi", _h(record["id"])),
                {
                    "href": record["source_link"],
                    "aria-label": fill(DECK["C07"], ID=record["id"]),
                },
            ),
        )
        row += _el("td", _h(record["title"])) + _el("td", _el("bdi", _h(record["source_file"])))
        row += _el("td", count_text)
        rows.append(
            _el("tr", row, {"id": deep_link(record["id"])[1:], "data-record-id": record["id"]})
        )
    table = _el(
        "table",
        _el("caption", _copy("C02"))
        + _el("thead", _el("tr", headings))
        + _el("tbody", "".join(rows)),
    )
    if len(payload["records"]) > NOSCRIPT_RECORDS:
        table += _el("p", _copy("C11"), {"class": "hub-noscript-pointer"})
    return table


def _views(payload: Payload) -> str:
    controls = _el(
        "details", _el("summary", _copy("B04.summary")) + _el("p", _copy("B04.body"))
    ) + _cutoffs(payload)
    bank = _el("h2", _copy("G09.bank.long")) + _el("p", _copy("B02"))
    bank += _el("div", controls, {"id": "bank-controls"})
    if not payload["pairs"]:
        bank += _el("h3", _copy("B10")) + _el("p", _copy("B11"))
    bank += _el("div", _engine_lists(payload), {"id": "bank-list"})
    graph = _el("h2", _copy("Gr01"), {"data-view-heading": True})
    graph += _el("p", _copy("Gr02")) + _el("p", _copy("Gr07"))
    if not payload["bridges"]:
        graph += _el("p", _copy("Gr09"), {"class": "hub-tour-empty"})
    graph += _el("div", _el("p", _copy("Gr12")), {"id": "graph-stage", "aria-label": DECK["Gr13"]})
    if any(not pair["weak"] for pair in payload["pairs"]):
        graph += _el("h3", _copy("Gr16"))
        graph += _el("div", _engine_lists(payload), {"id": "graph-list"})
    else:
        graph += _el("h3", _copy("Gr17")) + _el("p", _copy("Gr18"))
        graph += _el("div", attrs={"id": "graph-list"})
    graph += _el("p", _copy("Gr08", n=payload["graph"]["not_drawn"]))
    catalogue = _el("h2", _copy("C01"), {"data-view-heading": True})
    catalogue += _el("p", _copy("C02")) + _el("div", attrs={"id": "catalogue-controls"})
    catalogue += _el("div", _catalogue(payload), {"id": "catalogue-list"})
    return "".join(
        _el("section", content, {"id": name, "data-view": name})
        for name, content in zip(VIEW_NAMES, (bank, graph, catalogue), strict=True)
    )


def _counts(payload: Payload) -> str:
    counts = payload["counts"]
    values = (
        ("records", counts["records"]),
        ("unusual_pairs", counts["pairs"]["unusual_pairs"]),
        ("wording_and_meaning", counts["pairs"]["wording_and_meaning"]),
        ("hoods", counts["hoods"]),
    )
    return "".join(
        _el(
            "div",
            _el("strong", _h(value)) + _el("span", _copy(f"G11.{name}")),
            {"class": "hub-count"},
        )
        for name, value in values
    )


def _nav() -> str:
    return "".join(
        _el(
            "a",
            _copy(f"G09.{name}.long"),
            {
                "href": f"#{name}",
                "aria-label": DECK[f"G09.{name}.long"],
                "aria-current": "page" if name == "bank" else None,
            },
        )
        for name in VIEW_NAMES
    )


def _data_check(payload: Payload) -> str:
    check = payload["data_check"]
    removed = fill(DECK["D02.removed"], n=check["removed_count"], reason=check["removed_text"])
    if not check["removed_text"]:
        removed = removed.replace(". .", ".")
    return (
        _el("h2", _copy("D01"))
        + _el("p", _copy("D02.same", n=check["identical_records"]))
        + _el("p", _copy("D02.empty", n=check["no_text_records"]))
        + _el("p", _h(removed))
        + _el("p", _copy("D02.boilerplate"))
        + _el("p", _copy("D03"))
    )


def _finish(body: list[str], files: Collection[str], csp: str | None, *, gated: bool) -> bytes:
    parts = list(body)
    for name in SCRIPT_ORDER:
        if name in files and (gated or name != "hub-gate.js"):
            parts.append(_el("script", attrs={"src": name, "defer": True}))
    document = _el(
        "html",
        _head(files, csp, gated=gated)
        + "\n"
        + _el("body", "\n".join(parts), {"class": "mos-brand"}),
        {"lang": "en", "class": "no-js"},
    )
    return ("<!doctype html>\n" + document + "\n").encode("utf-8")


def _locked_page(files: Collection[str], csp: str | None) -> bytes:
    header = _el("img", attrs={"src": LOCKUP_FILE, "alt": DECK["G03.lockup_alt"]})
    header += _el("span", _copy("G03"))
    title = _el(
        "img",
        attrs={
            "id": "hub-face",
            "src": FACE_FILES["Boundary"],
            "alt": "",
            "aria-hidden": "true",
        },
    )
    title += _el("p", _copy("G04"), {"class": "hub-eyebrow"})
    title += _el("h1", _copy("L01"), {"id": "hub-title", "tabindex": "-1"})
    title += _el("p", _copy("L02"), {"id": "hub-meaning"})
    title += _el("p", attrs={"id": "hub-status"})
    form = _el("label", _copy("L03.label"), {"for": "hub-passphrase"})
    form += _el(
        "input",
        attrs={
            "id": "hub-passphrase",
            "type": "password",
            "autocomplete": "off",
            "autocapitalize": "off",
            "spellcheck": "false",
        },
    )
    form += _el(
        "button",
        _copy("L03.show"),
        {
            "id": "hub-passphrase-toggle",
            "type": "button",
            "aria-pressed": "false",
            "aria-controls": "hub-passphrase",
        },
    )
    form += _el("button", _copy("L03.unlock"), {"id": "hub-unlock", "type": "submit"})
    form += _el("p", attrs={"id": "hub-locked-status", "aria-live": "polite"})
    locked = _el("form", form, {"id": "hub-locked-form"}) + _el("p", _copy("L07"))
    views = []
    for name, containers in (
        ("bank", ("bank-controls", "bank-list")),
        ("graph", ("graph-stage", "graph-list")),
        ("catalogue", ("catalogue-controls", "catalogue-list")),
    ):
        views.append(
            _el(
                "section",
                "".join(_el("div", attrs={"id": item}) for item in containers),
                {"id": name, "data-view": name, "hidden": True},
            )
        )
    body = [
        _el("a", _copy("G02"), {"href": "#hub-results", "class": "hub-skip"}),
        _el("header", header, {"id": "hub-header"}),
        _el("div", title, {"id": "hub-title-band"}),
        _el("div", locked, {"id": "hub-locked", "class": "hub-panel"}),
        _el("div", attrs={"id": "hub-counts", "hidden": True}),
        _el("nav", attrs={"id": "hub-nav", "aria-label": DECK["G10"], "hidden": True}),
        _el("main", "".join(views), {"id": "hub-results", "hidden": True}),
        _el(
            "aside",
            _el("h2", attrs={"id": "hub-panel-title"}),
            {
                "id": "hub-panel",
                "aria-live": "polite",
                "aria-labelledby": "hub-panel-title",
                "hidden": True,
            },
        ),
        _el("section", attrs={"id": "hub-data-check", "hidden": True}),
        _el("footer", _el("p", _copy("G05")), {"id": "hub-footer"}),
        _el("noscript", _el("p", _copy("G13"))),
    ]
    return _finish(body, files, csp, gated=True)


def render_page(
    payload: Payload | None,
    *,
    files: Collection[str],
    csp: str | None = CONTENT_SECURITY_POLICY,
    gated: bool = False,
) -> bytes:
    """Render a local hub page using escaped source values and fixed copy.

    Args:
        payload: The validated hub payload, or None for a gated page.
        files: Output files available for relative style and script links.
        csp: The policy established by browser probes, or None to omit it.
        gated: Select the data-free locked form of the page.

    Returns:
        Stable UTF-8 HTML bytes ending in one LF.

    Raises:
        ValueError: The payload and gate mode disagree, or a source URL is not local.
    """
    if gated:
        if payload is not None:
            raise ValueError("A locked page must receive no payload")
        return _locked_page(files, csp)
    if payload is None:
        raise ValueError("An open page requires a payload")
    face = "Rest" if payload["pairs"] else "Limit"
    header = _el("img", attrs={"src": LOCKUP_FILE, "alt": DECK["G03.lockup_alt"]}) + _el(
        "span", _copy("G03")
    )
    title_band = _el(
        "img", attrs={"id": "hub-face", "src": FACE_FILES[face], "alt": "", "aria-hidden": "true"}
    )
    title_band += _el("p", _copy("G04"), {"class": "hub-eyebrow"})
    title_band += _el("h1", _copy("B01"), {"id": "hub-title", "tabindex": "-1"})
    title_band += _el("p", _copy("G07"), {"id": "hub-meaning"})
    status = "" if payload["pairs"] else _copy("B10") + " " + _copy("B11")
    title_band += _el("p", status, {"id": "hub-status"})
    panel = _el("h2", _copy("P01.heading"), {"id": "hub-panel-title"})
    panel += _el("p", _copy("P01.body"))
    panel += _el("img", attrs={"src": FACE_FILES["Rest"], "alt": "", "aria-hidden": "true"})
    body = [
        _el("a", _copy("G02"), {"href": "#hub-results", "class": "hub-skip"}),
        _el("header", header, {"id": "hub-header"}),
        _el("div", title_band, {"id": "hub-title-band"}),
        _el("div", _counts(payload), {"id": "hub-counts"}),
        _el("nav", _nav(), {"id": "hub-nav", "aria-label": DECK["G10"]}),
        _el("main", _views(payload), {"id": "hub-results"}),
        _el(
            "aside",
            panel,
            {"id": "hub-panel", "aria-live": "polite", "aria-labelledby": "hub-panel-title"},
        ),
        _el("section", _data_check(payload), {"id": "hub-data-check"}),
        _el(
            "footer",
            _el("p", _copy("G05"))
            + _el(
                "p",
                _copy(
                    "G14",
                    version=payload["tool_version"],
                    fingerprint=payload["run_fingerprint"][:12],
                    records=payload["counts"]["records"],
                ),
            ),
            {"id": "hub-footer"},
        ),
        _el("noscript", _el("p", _copy("G12"))),
    ]
    return _finish(body, files, csp, gated=False)
