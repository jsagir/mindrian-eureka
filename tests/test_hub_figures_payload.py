"""Tests of the words and the figures in the hub payload (Phase 2.3.1 plan 04).

The payload carries `terms` (plan 02) and `figures` (plan 04). `verify_payload` checks
both. A locked hub keeps them inside the encrypted data only (HUB-04).
"""

from __future__ import annotations

import copy
import io
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from hub_scan import scan_dashes, scan_for_network, scan_internal_names
from hub_support import HOSTILE_IMAGE, make_run_folder
from mindrian_eureka.hub.contracts import ENGINE_UNUSUAL, ENGINE_WORDING, js_assignment
from mindrian_eureka.hub.deck import DECK
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.hub.terms import build_terms
from mindrian_eureka.hub.verify import verify_payload
from mindrian_eureka.hub.writer import HubRequest, build_hub
from mindrian_eureka.run.console import Console
from mindrian_eureka.run.output import OUTPUT_WORDING
from mindrian_eureka.run.project import (
    READING_AGREE,
    READING_MEANING_HIGHER,
    READING_WORDING_HIGHER,
)

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_RUN = ROOT / "tests/fixtures/hub_public/run"
PASS = "synthetic figures test passphrase"
KINDS = {
    READING_MEANING_HIGHER: "meaning",
    READING_WORDING_HIGHER: "wording",
    READING_AGREE: "agree",
}


def _build(run: Path, out: Path, password: str | None = None) -> None:
    build_hub(HubRequest(run, out, password=password), Console(stderr=io.StringIO()))


def _assignment(path: Path, name: str) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data: dict[str, Any] = json.loads(text.removeprefix(f"window.{name} = ").rstrip(";\n"))
    return data


@pytest.fixture(scope="module")
def public() -> dict[str, Any]:
    return dict(build_payload(load_run(PUBLIC_RUN)))


def test_payload_has_terms_and_figures(public: dict[str, Any]) -> None:
    from mindrian_eureka.hub.figures import build_figures

    run = load_run(PUBLIC_RUN)
    for pair in public["pairs"]:
        assert pair["reading_kind"] == KINDS[pair["reading"]], pair["key"]
    triples = [
        (pair["pair_id"], pair["left"]["id"], pair["right"]["id"]) for pair in public["pairs"]
    ]
    assert public["terms"] == build_terms(list(run.records), triples)
    without = {key: value for key, value in public.items() if key != "figures"}
    assert public["figures"] == build_figures(without)
    assert set(public["figures"]["pairs"]) == {pair["key"] for pair in public["pairs"]}
    doc = json.loads((PUBLIC_RUN / OUTPUT_WORDING).read_text(encoding="utf-8"))
    raw = {item["pair_id"]: item["scores"].get("second_signal") for item in doc["pairs"]}
    seen_true = seen_false = 0
    for pair in public["pairs"]:
        if pair["engine"] == ENGINE_UNUSUAL:
            assert "confirmed" not in pair
            continue
        signal = raw[pair["pair_id"]]
        if isinstance(signal, dict) and isinstance(signal.get("confirmed"), bool):
            assert pair["confirmed"] is signal["confirmed"], pair["key"]
            seen_true += signal["confirmed"]
            seen_false += not signal["confirmed"]
        else:
            assert "confirmed" not in pair
    assert seen_true > 0 and seen_false > 0


def _mutations() -> list[tuple[str, Callable[[dict[str, Any]], None]]]:
    from mindrian_eureka.hub.figures import CARD_HARD_MAX_BYTES, CARD_MAX_BYTES, DETAIL_MAX_BYTES

    def first_key(payload: dict[str, Any]) -> str:
        return str(payload["pairs"][0]["key"])

    def figure(payload: dict[str, Any], kind: str) -> str:
        return str(payload["figures"]["pairs"][first_key(payload)][kind])

    def set_figure(payload: dict[str, Any], kind: str, value: Any) -> None:
        payload["figures"]["pairs"][first_key(payload)][kind] = value

    def pad(svg: str, size: int) -> str:
        return svg[: -len("</svg>")] + " " * (size - len(svg.encode()) + 1) + "</svg>"

    def over_card(payload: dict[str, Any]) -> None:
        set_figure(payload, "card", pad(figure(payload, "card"), CARD_MAX_BYTES))

    def over_hard(payload: dict[str, Any]) -> None:
        set_figure(payload, "card", pad(figure(payload, "card"), CARD_HARD_MAX_BYTES))

    def over_detail(payload: dict[str, Any]) -> None:
        set_figure(payload, "detail", pad(figure(payload, "detail"), DETAIL_MAX_BYTES))

    def image(payload: dict[str, Any]) -> None:
        set_figure(
            payload, "card", figure(payload, "card").replace("</svg>", '<image href="x"/></svg>')
        )

    def href(payload: dict[str, Any]) -> None:
        set_figure(
            payload, "detail", figure(payload, "detail").replace("<rect ", '<rect href="x" ', 1)
        )

    def onload(payload: dict[str, Any]) -> None:
        set_figure(
            payload, "card", figure(payload, "card").replace("<svg ", '<svg onload="x()" ', 1)
        )

    def ghost_key(payload: dict[str, Any]) -> None:
        payload["figures"]["pairs"]["ghost:pair"] = dict(
            payload["figures"]["pairs"][first_key(payload)]
        )

    def missing_key(payload: dict[str, Any]) -> None:
        del payload["figures"]["pairs"][first_key(payload)]

    def missing_card(payload: dict[str, Any]) -> None:
        del payload["figures"]["pairs"][first_key(payload)]["card"]

    def missing_detail(payload: dict[str, Any]) -> None:
        del payload["figures"]["pairs"][first_key(payload)]["detail"]

    def not_a_string(payload: dict[str, Any]) -> None:
        set_figure(payload, "card", 5)

    def legend_dash(payload: dict[str, Any]) -> None:
        payload["figures"]["legend"]["caption"] += " " + chr(8211)

    def label_dash(payload: dict[str, Any]) -> None:
        payload["figures"]["labels"]["meaning"] = "MEAN" + chr(8211) + "ING"

    def missing_legend(payload: dict[str, Any]) -> None:
        del payload["figures"]["legend"]["summary"]

    def missing_label(payload: dict[str, Any]) -> None:
        del payload["figures"]["labels"]["none_shared"]

    def extra_figures_key(payload: dict[str, Any]) -> None:
        payload["figures"]["extra"] = "x"

    def extra_terms_key(payload: dict[str, Any]) -> None:
        payload["terms"]["extra"] = {}

    def six_record_words(payload: dict[str, Any]) -> None:
        rid = payload["records"][0]["id"]
        payload["terms"]["records"][rid] = ["alpha", "beta", "gamma", "delta", "theta", "omega"]

    def seven_pair_words(payload: dict[str, Any]) -> None:
        pid = payload["pairs"][0]["pair_id"]
        payload["terms"]["pairs"][pid] = [
            "alpha",
            "beta",
            "gamma",
            "delta",
            "theta",
            "omega",
            "zeta",
        ]

    def capital(payload: dict[str, Any]) -> None:
        payload["terms"]["records"][payload["records"][0]["id"]] = ["Network"]

    def digit(payload: dict[str, Any]) -> None:
        payload["terms"]["records"][payload["records"][0]["id"]] = ["net1"]

    def other_char(payload: dict[str, Any]) -> None:
        payload["terms"]["records"][payload["records"][0]["id"]] = ["net_work"]

    def short_word(payload: dict[str, Any]) -> None:
        payload["terms"]["records"][payload["records"][0]["id"]] = ["net"]

    def unknown_record(payload: dict[str, Any]) -> None:
        payload["terms"]["records"]["ghost-record"] = ["alpha"]

    def unknown_pair(payload: dict[str, Any]) -> None:
        payload["terms"]["pairs"]["ghost-pair"] = ["alpha"]

    def confirmed_text(payload: dict[str, Any]) -> None:
        wording = next(pair for pair in payload["pairs"] if pair["engine"] == ENGINE_WORDING)
        wording["confirmed"] = "yes"

    def reading_kind(payload: dict[str, Any]) -> None:
        payload["pairs"][0]["reading_kind"] = "other"

    return [
        ("image", image),
        ("href", href),
        ("onload", onload),
        ("card over the cap", over_card),
        ("card over the hard ceiling", over_hard),
        ("detail over the cap", over_detail),
        ("ghost pair key", ghost_key),
        ("missing pair key", missing_key),
        ("missing card", missing_card),
        ("missing detail", missing_detail),
        ("not a string", not_a_string),
        ("legend dash", legend_dash),
        ("label dash", label_dash),
        ("missing legend key", missing_legend),
        ("missing label key", missing_label),
        ("extra figures key", extra_figures_key),
        ("extra terms key", extra_terms_key),
        ("six record words", six_record_words),
        ("seven pair words", seven_pair_words),
        ("capital letter", capital),
        ("digit", digit),
        ("other character", other_char),
        ("short word", short_word),
        ("unknown record id", unknown_record),
        ("unknown pair id", unknown_pair),
        ("confirmed not a bool", confirmed_text),
        ("reading kind", reading_kind),
    ]


def test_verify_accepts_and_rejects(public: dict[str, Any]) -> None:
    assert verify_payload(public) == []  # type: ignore[arg-type]
    first_key = public["pairs"][0]["key"]
    for name, mutate in _mutations():
        mutated = copy.deepcopy(public)
        mutate(mutated)
        problems = verify_payload(mutated)  # type: ignore[arg-type]
        assert problems, name
        if name in {
            "image",
            "href",
            "onload",
            "card over the cap",
            "card over the hard ceiling",
            "detail over the cap",
            "missing card",
            "missing detail",
            "not a string",
        }:
            assert any(first_key in problem for problem in problems), (name, problems)
    bare = copy.deepcopy(public)
    del bare["terms"]
    del bare["figures"]
    assert verify_payload(bare) == []  # type: ignore[arg-type]


def test_locked_build_holds_no_word_and_no_figure_in_clear(tmp_path: Path) -> None:
    pytest.importorskip("cryptography")
    from mindrian_eureka.hub import gate

    locked, open_dir = tmp_path / "locked", tmp_path / "open"
    _build(PUBLIC_RUN, locked, PASS)
    _build(PUBLIC_RUN, open_dir)
    clear = _assignment(open_dir / "hub-data.js", "HUB")
    files = [(locked / "hub.html").read_bytes(), (locked / "hub-data.js").read_bytes()]
    first_record = sorted(clear["records"], key=lambda record: record["id"])[0]
    for raw in files:
        assert b"<svg" not in raw
        assert b"\\u003csvg" not in raw
        assert b"hub-figure" not in raw
        for text in clear["figures"]["legend"].values():
            assert text.encode() not in raw
        for word in clear["terms"]["records"][first_record["id"]]:
            assert word.encode() not in raw, word
        for record in clear["records"]:
            assert record["title"].encode() not in raw
    envelope = _assignment(locked / "hub-data.js", "HUB_ENVELOPE")
    decrypted = json.loads(gate.decrypt_payload(envelope, PASS))
    assert decrypted["terms"] == clear["terms"]
    assert decrypted["figures"] == clear["figures"]
    assert len(clear["terms"]["records"][first_record["id"]]) >= 1


def test_built_folder_scans_clean(tmp_path: Path) -> None:
    hostile_run = make_run_folder(tmp_path, name="hostile", hostile=True)
    for run, name in ((PUBLIC_RUN, "public"), (hostile_run, "hostile-hub")):
        out = tmp_path / name
        _build(run, out)
        assert scan_for_network(out) == [], name
        assert scan_dashes(out) == [], name
        assert scan_internal_names(out) == [], name
        data = _assignment(out / "hub-data.js", "HUB")
        assert "figures" in data and "terms" in data


def test_hostile_run_figures_hold_no_markup(tmp_path: Path) -> None:
    from mindrian_eureka.hub.figures import figure_problems

    payload = build_payload(load_run(make_run_folder(tmp_path, hostile=True)))
    assert payload["pairs"], "the hostile run has pairs"
    for key, figures in payload["figures"]["pairs"].items():
        for svg in (figures["card"], figures["detail"]):
            assert "<script" not in svg, key
            assert "onerror=" not in svg, key
            assert HOSTILE_IMAGE not in svg, key
            assert figure_problems(svg) == [], key


def test_scale_cost_is_measured(tmp_path: Path) -> None:
    from mindrian_eureka.hub.figures import CARD_MAX_BYTES, DETAIL_MAX_BYTES
    from test_hub_scale import build_scale_run

    run, out, summary, seconds = build_scale_run(tmp_path)
    payload = build_payload(load_run(run))
    keys = {pair["key"] for pair in payload["pairs"]}
    figures = payload["figures"]["pairs"]
    assert set(figures) == keys
    count = sum(len(item) for item in figures.values())
    assert count == 2 * len(keys)
    total = 0
    for key, item in figures.items():
        card = len(item["card"].encode())
        detail = len(item["detail"].encode())
        assert card <= CARD_MAX_BYTES, key
        assert detail <= DETAIL_MAX_BYTES, key
        total += card + detail
    assert total <= len(keys) * (CARD_MAX_BYTES + DETAIL_MAX_BYTES)
    with_all = len(js_assignment("HUB", payload))
    slim = {k: v for k, v in payload.items() if k not in {"figures", "terms"}}
    without = len(js_assignment("HUB", slim))
    print(
        json.dumps(
            {
                "pairs": len(keys),
                "figure_bytes": total,
                "hub_data_bytes": with_all,
                "hub_data_bytes_without_figures_and_terms": without,
                "hub_data_bytes_on_disk": (out / "hub-data.js").stat().st_size,
                "build_seconds": round(seconds, 3),
                "records": summary.records,
            }
        )
    )


def test_deck_is_untouched() -> None:
    assert not any(key.startswith("G18.") for key in DECK)
    assert "G15.wording_and_meaning" in DECK
