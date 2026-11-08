"""Check local hub structure, escaping, provenance and privacy boundaries."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, replace
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from hub_support import make_run_folder
from mindrian_eureka.hub import page
from mindrian_eureka.hub.assets import static_assets
from mindrian_eureka.hub.contracts import FACE_FILES, LOCKUP_FILE, Payload, has_internal_name
from mindrian_eureka.hub.deck import DECK
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.run.contracts import LABEL

REPO = Path(__file__).resolve().parents[1]
FILES = (
    {item.output_path for item in static_assets()}
    | set(page.STYLE_ORDER)
    | set(page.SCRIPT_ORDER)
    | {"hub-boot.js"}
)
VOID = {"meta", "link", "img", "input", "br", "hr"}
CHROME = {
    "hub-header",
    "hub-header-action",
    "hub-page",
    "hub-title-band",
    "hub-face",
    "hub-title",
    "hub-meaning",
    "hub-status",
    "hub-counts",
    "hub-band",
    "hub-nav",
    "hub-results",
    "hub-panel",
    "hub-panel-title",
    "hub-data-check",
    "hub-footer",
    "bank-controls",
    "bank-list",
    "graph-stage",
    "graph-list",
    "catalogue-controls",
    "catalogue-list",
}


@dataclass
class Element:
    tag: str
    attrs: dict[str, str | None]
    text: str = ""
    children: list[Element] = field(default_factory=list)

    def descendants(self) -> list[Element]:
        return [child for item in self.children for child in (item, *item.descendants())]


class Document(HTMLParser):
    def __init__(self, content: bytes):
        super().__init__(convert_charrefs=True)
        self.nodes: list[Element] = []
        self.stack: list[Element] = []
        self.feed(content.decode("utf-8"))
        assert not self.stack

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Element(tag, dict(attrs))
        if self.stack:
            self.stack[-1].children.append(node)
        self.nodes.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        assert self.stack and self.stack[-1].tag == tag, (
            tag,
            self.stack[-1:] if self.stack else [],
        )
        self.stack.pop()

    def handle_data(self, data: str) -> None:
        for node in self.stack:
            node.text += data

    def by_id(self, name: str) -> Element:
        return next(node for node in self.nodes if node.attrs.get("id") == name)

    def tagged(self, name: str) -> list[Element]:
        return [node for node in self.nodes if node.tag == name]


@pytest.fixture
def payload(tmp_path: Path) -> Payload:
    return build_payload(load_run(make_run_folder(tmp_path)))


def _doc(payload: Payload, *, files: set[str] | None = None) -> Document:
    return Document(page.render_page(payload, files=FILES if files is None else files))


def _pair_rows(node: Element) -> list[Element]:
    return [child for child in node.descendants() if "data-pair-key" in child.attrs]


def _assert_pair_sources(document: Document) -> None:
    for section in ("bank", "graph"):
        for row in _pair_rows(document.by_id(section)):
            assert LABEL in row.text, row.attrs["data-pair-key"]
            anchors = [node for node in row.descendants() if node.tag == "a"]
            assert len(anchors) == 2
            assert all(anchor.attrs.get("href") for anchor in anchors)


def _assert_csp_constant() -> None:
    text = (REPO / "docs/brand/hub-probe-results.md").read_text()
    decision = next(
        line.partition(": ")[2] for line in text.splitlines() if line.startswith("CSP decision:")
    )
    expected = None if decision.lower() == "none" else decision
    assert page.CONTENT_SECURITY_POLICY == expected


def test_shell_landmarks_ids_outline_and_navigation(payload: Payload) -> None:
    doc = _doc(payload)
    assert len(doc.tagged("h1")) == 1
    levels = [
        int(node.tag[1]) for node in doc.nodes if node.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}
    ]
    assert levels[0] == 1
    assert all(after <= before + 1 for before, after in zip(levels, levels[1:], strict=False))
    assert all(doc.tagged(tag) for tag in ("header", "nav", "main", "aside", "footer"))
    ids = [node.attrs["id"] for node in doc.nodes if "id" in node.attrs]
    assert len(ids) == len(set(ids))
    assert CHROME <= set(ids)
    main = doc.by_id("hub-results")
    assert [node.attrs.get("id") for node in main.children] == ["bank", "graph", "catalogue"]
    assert any(node.attrs.get("href") == "#hub-results" for node in doc.tagged("a"))
    nav = doc.by_id("hub-nav")
    assert [node.attrs["href"] for node in nav.children] == ["#bank", "#graph", "#catalogue"]
    assert nav.children[0].attrs["aria-current"] == "page"
    face = doc.by_id("hub-face")
    assert face.attrs["alt"] == "" and face.attrs["aria-hidden"] == "true"
    assert face.attrs["src"] == FACE_FILES["Rest"]
    assert any(node.attrs.get("src") == LOCKUP_FILE for node in doc.tagged("img"))
    assert doc.tagged("html")[0].attrs["lang"] == "en"
    assert doc.tagged("title")[0].text == DECK["G01.bank"]


def test_relative_links_no_active_inline_content_and_csp(payload: Payload) -> None:
    doc = _doc(payload)
    for node in doc.nodes:
        assert node.tag != "style"
        assert not any(name == "style" or name.startswith("on") for name in node.attrs)
        for attribute in ("src", "href"):
            value = node.attrs.get(attribute)
            if value:
                assert not urlsplit(value).scheme and not value.startswith("/")
    scripts = doc.tagged("script")
    assert all(node.attrs.get("src") for node in scripts)
    assert [node.attrs["src"] for node in scripts if "defer" not in node.attrs] == ["hub-boot.js"]
    policy = [
        node
        for node in doc.tagged("meta")
        if node.attrs.get("http-equiv") == "Content-Security-Policy"
    ]
    assert len(policy) == 1 and policy[0].attrs["content"] == page.CONTENT_SECURITY_POLICY
    assert doc.tagged("head")[0].children[1] is policy[0]
    _assert_csp_constant()


def test_changed_csp_constant_fails_consistency_check(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(page, "CONTENT_SECURITY_POLICY", "default-src 'self'")
    with pytest.raises(AssertionError):
        _assert_csp_constant()


def test_only_existing_files_are_linked_in_order(payload: Payload) -> None:
    files = FILES - {"hub-graph.css"}
    doc = _doc(payload, files=files)
    styles = [
        node.attrs["href"] for node in doc.tagged("link") if node.attrs.get("rel") == "stylesheet"
    ]
    assert styles == [name for name in page.STYLE_ORDER if name in files and name != "hub-gate.css"]
    scripts = [node.attrs["src"] for node in doc.tagged("script") if "defer" in node.attrs]
    assert scripts == [name for name in page.SCRIPT_ORDER if name != "hub-gate.js"]
    no_csp = Document(page.render_page(payload, files=set(), csp=None))
    assert not no_csp.tagged("script")
    assert not any(
        node.attrs.get("http-equiv") == "Content-Security-Policy" for node in no_csp.nodes
    )


def test_hostile_text_cannot_create_markup(tmp_path: Path) -> None:
    payload = build_payload(load_run(make_run_folder(tmp_path, hostile=True)))
    payload["records"][3]["title"] += '<img src=x onerror="window.__pwned=1">'
    raw = page.render_page(payload, files=FILES)
    doc = Document(raw)
    assert b"&lt;script&gt;" in raw and b"&lt;img" in raw
    assert not any("onerror" in node.attrs for node in doc.nodes)
    assert (
        len(doc.tagged("script"))
        == len([name for name in page.SCRIPT_ORDER if name != "hub-gate.js"]) + 1
    )
    assert doc.by_id("record:bank").attrs["data-record-id"] == "bank"
    hostile_title = next(
        record["title"] for record in payload["records"] if "<script>" in record["title"]
    )
    assert any(hostile_title in node.text for node in doc.tagged("td"))
    assert all(
        not (node.attrs.get("href") or "").startswith("javascript:") for node in doc.tagged("a")
    )


def test_record_ids_cannot_collide_with_shell_or_escape_ids(tmp_path: Path) -> None:
    run = load_run(make_run_folder(tmp_path, n_records=4, zero_pairs=True))
    ids = ["bank-controls", "record:bank", "bank", "graph-stage"]
    records = tuple(
        replace(record, id=record_id) for record, record_id in zip(run.records, ids, strict=True)
    )
    payload = build_payload(replace(run, records=records))
    doc = _doc(payload)
    actual = [node.attrs["id"] for node in doc.nodes if "id" in node.attrs]
    assert len(actual) == len(set(actual))
    for record in payload["records"]:
        assert doc.by_id(record["catalogue_link"][1:]).attrs["data-record-id"] == record["id"]


def test_every_pair_has_label_and_two_sources_and_catalogue_has_source(payload: Payload) -> None:
    doc = _doc(payload)
    _assert_pair_sources(doc)
    rows = [node for node in doc.tagged("tr") if "data-record-id" in node.attrs]
    assert len(rows) == len(payload["records"])
    records = {record["id"]: record for record in payload["records"]}
    for row in rows:
        anchors = [node for node in row.descendants() if node.tag == "a"]
        assert len(anchors) == 1
        assert anchors[0].attrs["href"] == records[row.attrs["data-record-id"]]["source_link"]
        assert len([node for node in row.children if node.tag == "td"]) == 4


def test_a_row_without_label_fails_the_same_hub03_check(payload: Payload) -> None:
    altered = copy.deepcopy(payload)
    altered["pairs"][0]["label"] = ""
    with pytest.raises(AssertionError):
        _assert_pair_sources(_doc(altered))


@pytest.mark.parametrize(
    "target",
    [
        "javascript:alert(1)",
        "https://example.test",
        "//example.test",
        "/absolute",
        "data:text/html,bad",
    ],
)
def test_renderer_refuses_nonlocal_source_links(payload: Payload, target: str) -> None:
    payload["records"][0]["source_link"] = target
    with pytest.raises(ValueError, match="relative"):
        _doc(payload)


@pytest.mark.parametrize("count,shown,pointer", [(10, 10, False), (80, 50, True)])
def test_pair_prerender_limit(tmp_path: Path, count: int, shown: int, pointer: bool) -> None:
    payload = build_payload(load_run(make_run_folder(tmp_path, pairs_per_engine=(count, 0))))
    doc = _doc(payload)
    assert len(_pair_rows(doc.by_id("bank"))) == shown
    assert (DECK["B14"] in doc.by_id("bank").text) is pointer


def test_catalogue_prerender_limit(tmp_path: Path) -> None:
    payload = build_payload(load_run(make_run_folder(tmp_path, n_records=250)))
    doc = _doc(payload)
    assert len([node for node in doc.tagged("tr") if "data-record-id" in node.attrs]) == 200
    assert DECK["C11"] in doc.by_id("catalogue").text


def test_zero_pairs_and_one_engine_empty_states(tmp_path: Path) -> None:
    empty = build_payload(load_run(make_run_folder(tmp_path, zero_pairs=True)))
    doc = _doc(empty)
    assert doc.by_id("hub-face").attrs["src"] == FACE_FILES["Limit"]
    assert DECK["B10"] in doc.by_id("bank").text and DECK["B11"] in doc.by_id("bank").text
    assert not _pair_rows(doc.by_id("bank"))
    mixed = build_payload(load_run(make_run_folder(tmp_path / "mixed", pairs_per_engine=(10, 0))))
    mixed_doc = _doc(mixed)
    for key in ("unusual_pairs", "wording_and_meaning"):
        assert any(node.text == DECK[f"G15.{key}"] for node in mixed_doc.tagged("h3"))


def test_copy_and_empty_text_flags_render(tmp_path: Path) -> None:
    payload = build_payload(
        load_run(
            make_run_folder(tmp_path, n_records=8, pairs_per_engine=28, copies=2, empty_text=1)
        )
    )
    doc = _doc(payload)
    text = " ".join(row.text for row in _pair_rows(doc.by_id("bank")))
    assert "Identical text to" in text and DECK["P09.no_text"] in text


def test_fixed_copy_footer_noscript_and_stable_bytes(payload: Payload) -> None:
    first = page.render_page(payload, files=FILES)
    assert first == page.render_page(payload, files=FILES)
    assert first.endswith(b"\n") and not first.endswith(b"\n\n")
    assert not any(char in first.decode() for char in (chr(8211), chr(8212)))
    assert not has_internal_name(first.decode())
    doc = Document(first)
    footer = doc.by_id("hub-footer").text
    assert LABEL in footer and payload["run_fingerprint"][:12] in footer and DECK["G05"] in footer
    assert DECK["G12"] in doc.tagged("noscript")[0].text


def test_real_public_fixture_renders_a_well_formed_offline_page() -> None:
    payload = build_payload(load_run(REPO / "tests/fixtures/hub_public/run"))
    doc = _doc(payload)
    assert len(doc.tagged("h1")) == 1
    assert all(node.attrs.get("src") for node in doc.tagged("script"))
    _assert_pair_sources(doc)


@pytest.mark.parametrize("hostile", [False, True])
def test_locked_page_contains_no_collection_data(tmp_path: Path, hostile: bool) -> None:
    payload = build_payload(
        load_run(
            make_run_folder(
                tmp_path,
                n_records=9 if hostile else 31,
                hostile=hostile,
                seed_text="DISTINCT_PRIVATE_SOURCE_TEXT_7319 for the locked privacy test.",
            )
        )
    )
    raw = page.render_page(None, files=FILES, gated=True)
    doc = Document(raw)
    chrome_ids = {node.attrs.get("id") for node in doc.nodes}
    for record in payload["records"]:
        # Static shell names may equal hostile record IDs; data bindings must still be absent.
        if record["id"] not in chrome_ids:
            assert record["id"].encode() not in raw
        assert record["title"].encode() not in raw
        if len(record["text"]) >= 12:
            assert record["text"][:12].encode() not in raw
    assert not any("data-record-id" in node.attrs for node in doc.nodes)
    assert not any("data-pair-key" in node.attrs for node in doc.nodes)
    for value in (
        payload["run_fingerprint"],
        payload["run_fingerprint"][:12],
        payload["tool_version"],
    ):
        assert value.encode() not in raw
    for engine in payload["engines"].values():
        assert all(note.encode() not in raw for note in engine["notes"])
    for key in ("records", "unusual_pairs", "wording_and_meaning", "hoods"):
        assert DECK[f"G11.{key}"].encode() not in raw
    assert raw == page.render_page(None, files=FILES, gated=True)
    assert len(doc.tagged("h1")) == 1
    ids = [node.attrs["id"] for node in doc.nodes if "id" in node.attrs]
    assert len(ids) == len(set(ids))
    assert CHROME <= set(ids)
    assert doc.tagged("title")[0].text == DECK["G01.locked"]
    assert doc.by_id("hub-face").attrs["src"] == FACE_FILES["Boundary"]
    assert DECK["L01"] == doc.by_id("hub-title").text
    assert DECK["L02"] == doc.by_id("hub-meaning").text
    assert DECK["L07"] in doc.by_id("hub-locked").text
    assert DECK["G13"] in doc.tagged("noscript")[0].text
    assert doc.by_id("hub-footer").text == DECK["G05"]


def test_locked_form_attributes_and_hidden_empty_containers() -> None:
    doc = Document(page.render_page(None, files=FILES, gated=True))
    field = doc.by_id("hub-passphrase")
    for key, value in {
        "type": "password",
        "autocomplete": "off",
        "autocapitalize": "off",
        "spellcheck": "false",
    }.items():
        assert field.attrs[key] == value
    assert any(
        node.attrs.get("for") == "hub-passphrase" and node.text == DECK["L03.label"]
        for node in doc.tagged("label")
    )
    toggle = doc.by_id("hub-passphrase-toggle")
    assert toggle.attrs["type"] == "button" and toggle.attrs["aria-pressed"] == "false"
    assert toggle.attrs["aria-controls"] == "hub-passphrase"
    assert toggle.text == DECK["L03.show"]
    assert doc.by_id("hub-unlock").attrs["type"] == "submit"
    assert "action" not in doc.by_id("hub-locked-form").attrs
    assert doc.by_id("hub-locked-status").attrs["aria-live"] == "polite"
    for name in (
        "hub-counts",
        "hub-nav",
        "hub-results",
        "bank",
        "graph",
        "catalogue",
        "hub-panel",
        "hub-data-check",
    ):
        node = doc.by_id(name)
        assert "hidden" in node.attrs and not node.text
    assert all(node.tag != "style" and "style" not in node.attrs for node in doc.nodes)
    assert all(node.attrs.get("src") for node in doc.tagged("script"))
    for node in doc.nodes:
        assert not any(name.startswith("on") for name in node.attrs)
        for key in ("href", "src"):
            value = node.attrs.get(key)
            if value:
                assert not urlsplit(value).scheme and not value.startswith("/")
    assert any(node.attrs.get("http-equiv") == "Content-Security-Policy" for node in doc.nodes)
    assert any(node.attrs.get("href") == "hub-gate.css" for node in doc.tagged("link"))
    assert any(node.attrs.get("src") == "hub-gate.js" for node in doc.tagged("script"))


def test_gate_and_payload_modes_cannot_be_mixed(payload: Payload) -> None:
    with pytest.raises(ValueError, match="no payload"):
        page.render_page(payload, files=FILES, gated=True)
    with pytest.raises(ValueError, match="requires a payload"):
        page.render_page(None, files=FILES)


# Phase 2.3.1 plan 03 (D-01): the shell of the target, a sticky header with the nav inside,
# one page wrapper and a title band with an eyebrow and a display heading.


def _classes(node: Element) -> set[str]:
    return set((node.attrs.get("class") or "").split())


def _header_checks(doc: Document, *, locked: bool) -> None:
    header = doc.by_id("hub-header")
    assert header.tag == "header"
    # Plan 02.3.1-05: two lockups, the paper one and the book's reverse one; the theme shows one.
    assert [node.tag for node in header.children] == ["img", "img", "div", "div"]
    lockup, reverse, context, links = header.children
    assert lockup.attrs["src"] == LOCKUP_FILE and lockup.attrs["alt"] == DECK["G03.lockup_alt"]
    assert _classes(lockup) == {"hub-lockup", "hub-lockup--paper"}
    assert reverse.attrs["src"] == page.LOCKUP_REVERSE_FILE
    assert reverse.attrs["src"] == "assets/brand/mos-lockup-reverse-v2.svg"
    assert reverse.attrs["alt"] == DECK["G03.lockup_alt"]
    assert _classes(reverse) == {"hub-lockup", "hub-lockup--reverse"}
    for image in (lockup, reverse):
        assert not any(
            image in node.descendants() for node in header.descendants() if node.tag == "a"
        )
    assert _classes(context) == {"hub-header-context"}
    assert [_classes(node) for node in context.children] == [
        {"hub-header-label"}, {"hub-header-sub"}
    ]
    assert context.children[0].text == DECK["G03"] and context.children[1].text == DECK["G05"]
    assert _classes(links) == {"hub-header-links"}
    assert [node.tag for node in links.children] == ["nav", "a", "button"]
    nav, action, toggle = links.children
    assert nav.attrs["id"] == "hub-nav" and nav.attrs["aria-label"] == DECK["G10"]
    assert action.attrs["id"] == "hub-header-action"
    assert "hub-header-action" in _classes(action)
    assert action.attrs["href"] == "#hub-data-check" and action.text == DECK["D01"]
    # Plan 02.3.1-05: the theme toggle, present and not hidden on both pages (HUB-10).
    assert toggle.attrs["id"] == "hub-theme" and _classes(toggle) == {"hub-theme-toggle"}
    assert toggle.attrs["type"] == "button" and toggle.attrs["aria-pressed"] == "false"
    assert toggle.attrs["aria-label"] == DECK["G03.theme.name"] == "Dark mode"
    assert "hidden" not in toggle.attrs
    assert [node.tag for node in toggle.children] == ["span", "span"]
    dot, label = toggle.children
    assert _classes(dot) == {"hub-theme-dot"} and dot.attrs["aria-hidden"] == "true"
    assert dot.text == ""
    assert _classes(label) == {"hub-theme-label"} and label.text == DECK["G03.theme.light"]
    if locked:
        assert "hidden" in nav.attrs and not nav.children
        assert "hidden" in action.attrs
    else:
        assert "hidden" not in nav.attrs and "hidden" not in action.attrs
        assert [node.attrs["href"] for node in nav.children] == ["#bank", "#graph", "#catalogue"]


def _wrapper_checks(doc: Document) -> None:
    body = doc.tagged("body")[0]
    assert [(node.tag, node.attrs.get("id") or node.attrs.get("class")) for node in body.children
            if node.tag != "script"] == [
        ("a", "hub-skip"), ("header", "hub-header"), ("div", "hub-page"), ("noscript", None)
    ]
    wrapper = doc.by_id("hub-page")
    ids = [node.attrs.get("id") for node in wrapper.children]
    expected = ["hub-title-band", "hub-counts", "hub-band", "hub-results", "hub-panel",
                "hub-data-check", "hub-footer"]
    assert [item for item in ids if item in expected] == expected
    assert set(ids) - set(expected) <= {"hub-locked"}


def _shape(node: Element) -> list[tuple[str, str | None]]:
    return [
        (child.tag, child.attrs.get("id") or child.attrs.get("class")) for child in node.children
    ]


def _title_band_checks(doc: Document, heading: str, meaning: str) -> None:
    band = doc.by_id("hub-title-band")
    assert _shape(band) == [("div", "hub-title-row"), ("p", "hub-meaning"), ("p", "hub-status")]
    row = band.children[0]
    assert _shape(row) == [("div", "hub-title-main"), ("img", "hub-face")]
    main = row.children[0]
    assert _shape(main) == [("p", "hub-eyebrow"), ("h1", "hub-title")]
    eyebrow, title = main.children
    assert [node.tag for node in eyebrow.children] == ["span"]
    dot = eyebrow.children[0]
    assert _classes(dot) == {"hub-eyebrow-dot"} and dot.attrs["aria-hidden"] == "true"
    assert not dot.text and eyebrow.text == DECK["G04"]
    assert title.text == heading and title.attrs["tabindex"] == "-1"
    assert band.children[1].text == meaning
    assert len(doc.tagged("h1")) == 1


def test_header_structure(payload: Payload) -> None:
    _header_checks(_doc(payload), locked=False)


def test_wrapper_structure(payload: Payload) -> None:
    _wrapper_checks(_doc(payload))


def test_title_band_structure(payload: Payload) -> None:
    _title_band_checks(_doc(payload), DECK["B01"], DECK["G07"])


def test_locked_page_shell() -> None:
    doc = Document(page.render_page(None, files=FILES, gated=True))
    _header_checks(doc, locked=True)
    _wrapper_checks(doc)
    _title_band_checks(doc, DECK["L01"], DECK["L02"])
    wrapper = doc.by_id("hub-page")
    ids = [node.attrs.get("id") for node in wrapper.children]
    assert ids.index("hub-locked") == ids.index("hub-title-band") + 1
    for name in ("hub-counts", "hub-band", "hub-results", "hub-panel", "hub-data-check"):
        assert "hidden" in doc.by_id(name).attrs
    assert doc.by_id("hub-face").attrs["src"] == FACE_FILES["Boundary"]
