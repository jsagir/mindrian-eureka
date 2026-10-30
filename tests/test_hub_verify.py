"""Contract checks for hub payloads."""

from __future__ import annotations

from pathlib import Path

from hub_support import make_run_folder
from mindrian_eureka.hub.model import build_payload
from mindrian_eureka.hub.reader import load_run
from mindrian_eureka.hub.verify import verify_payload


def _payload(tmp_path: Path):
    return build_payload(load_run(make_run_folder(tmp_path)))


def test_clean_payload_has_no_problems(tmp_path: Path) -> None:
    assert verify_payload(_payload(tmp_path)) == []


def test_missing_pair_label_names_the_pair_key(tmp_path: Path) -> None:
    payload = _payload(tmp_path)
    pair = payload["pairs"][0]
    key = pair["key"]
    del pair["label"]
    assert any(key in problem for problem in verify_payload(payload))


def test_verifier_rejects_missing_and_remote_links(tmp_path: Path) -> None:
    payload = _payload(tmp_path)
    payload["records"][0]["source_link"] = ""
    payload["pairs"][0]["left"]["source_link"] = "javascript:alert(1)"
    payload["pairs"][0]["right"]["source_link"] = "https://example.test/record"
    problems = verify_payload(payload)
    assert any("record" in problem and "source link" in problem for problem in problems)
    assert any("javascript:" in problem for problem in problems)
    assert any("https:" in problem for problem in problems)


def test_verifier_flags_dashes_and_internal_names_in_hub_copy(tmp_path: Path) -> None:
    payload = _payload(tmp_path)
    payload["engines"]["unusual_pairs"]["notes"] = ["A note with an em dash " + chr(0x2014)]
    payload["pairs"][0]["reading"] = "Internal hsi_reference.py name."
    problems = verify_payload(payload)
    assert any("dash" in problem for problem in problems)
    assert any("internal" in problem for problem in problems)


def test_verifier_does_not_scan_collection_title(tmp_path: Path) -> None:
    payload = _payload(tmp_path)
    payload["records"][0]["title"] = "Collection title " + chr(0x2014) + " remains data"
    assert verify_payload(payload) == []


def test_verifier_reports_missing_payload_key(tmp_path: Path) -> None:
    payload = _payload(tmp_path)
    del payload["graph"]
    assert any("graph" in problem and "key" in problem for problem in verify_payload(payload))
