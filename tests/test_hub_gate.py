"""All passphrases in this module are synthetic test strings, never credentials."""

from __future__ import annotations

import base64
import builtins
import copy
import random
import subprocess
import sys
from pathlib import Path

import pytest
from mindrian_eureka.hub import gate
from mindrian_eureka.run.contracts import UsageError

PASS = "synthetic gate test passphrase"
FINGERPRINT = "1" * 64
PLAINTEXT = b'{"synthetic":"not a finding"}\n'
EXPECTED = {'cipher': {'name': 'AES-256-GCM', 'nonce': 'p3l1eOUowOEIvJXW'},
 'ciphertext': 'TL4lT7fvhaPznez39kG1m/AzD7Zt++Uyw8SybM3b3AlrOwhlBs1z3ww+IY5jkw==',
 'kdf': {'iterations': 600000,
         'name': 'PBKDF2-SHA256',
         'salt': '64bbrC1nfs8pDIAqDErUDQ=='},
 'schema': 'eureka.hub-envelope.v1'}


def crypto() -> None:
    pytest.importorskip("cryptography")


def test_known_answer_and_round_trip() -> None:
    crypto()
    assert gate.encrypt_payload(PLAINTEXT, PASS, FINGERPRINT) == EXPECTED
    assert gate.decrypt_payload(EXPECTED, PASS) == PLAINTEXT
    assert PASS not in repr(EXPECTED)


def test_derivation_and_input_changes() -> None:
    crypto()
    salt = gate.derive_salt(FINGERPRINT)
    key = gate.derive_key(PASS, salt)
    assert len(salt) == 16 and len(key) == 32
    assert gate.PBKDF2_ITERATIONS == 600000
    assert gate.associated_data(600000) == b"eureka.hub-envelope.v1|600000"
    assert len(gate.derive_nonce(key, salt, PLAINTEXT)) == 12
    assert gate.encrypt_payload(PLAINTEXT, PASS, FINGERPRINT) == EXPECTED
    for data, password, fingerprint in ((PLAINTEXT + b"x", PASS, FINGERPRINT),
                                        (PLAINTEXT, PASS + "x", FINGERPRINT),
                                        (PLAINTEXT, PASS, "2" * 64)):
        actual = gate.encrypt_payload(data, password, fingerprint)
        assert actual["ciphertext"] != EXPECTED["ciphertext"]


def test_thousand_plaintexts_have_distinct_nonces() -> None:
    salt = gate.derive_salt(FINGERPRINT)
    key = gate.derive_key(PASS, salt)
    rng = random.Random(17)
    messages = [index.to_bytes(4, "big") + rng.randbytes(32) for index in range(1000)]
    assert len({gate.derive_nonce(key, salt, message) for message in messages}) == 1000


@pytest.mark.parametrize(
    "mutation", ["password", "ciphertext", "nonce", "iterations", "schema", "base64"]
)
def test_tampering_has_plain_error_without_passphrase(mutation: str) -> None:
    crypto()
    envelope = copy.deepcopy(EXPECTED)
    password = PASS
    if mutation == "password":
        password = PASS + " wrong"
    elif mutation == "ciphertext":
        data = base64.b64decode(envelope["ciphertext"])
        envelope["ciphertext"] = base64.b64encode(bytes([data[0] ^ 1]) + data[1:]).decode()
    elif mutation == "nonce":
        data = base64.b64decode(envelope["cipher"]["nonce"])
        envelope["cipher"]["nonce"] = base64.b64encode(bytes([data[0] ^ 1]) + data[1:]).decode()
    elif mutation == "iterations":
        envelope["kdf"]["iterations"] += 1
    elif mutation == "schema":
        envelope["schema"] = "changed"
    else:
        envelope["ciphertext"] = "invalid!"
    with pytest.raises(ValueError) as caught:
        gate.decrypt_payload(envelope, password)
    assert PASS not in str(caught.value) and password not in str(caught.value)


def test_empty_passphrase_is_usage_error() -> None:
    with pytest.raises(UsageError):
        gate.encrypt_payload(PLAINTEXT, "", FINGERPRINT)


def test_optional_import_and_missing_library(monkeypatch: pytest.MonkeyPatch) -> None:
    subprocess.run([sys.executable, "-c", "import sys; import mindrian_eureka.hub.gate; "
                    "assert 'cryptography' not in sys.modules"], check=True)
    original = builtins.__import__
    def blocked(name, *args, **kwargs):
        if name.startswith("cryptography"):
            raise ImportError("test dependency unavailable")
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", blocked)
    with pytest.raises(UsageError) as caught:
        gate.encrypt_payload(PLAINTEXT, PASS, FINGERPRINT)
    assert "uv sync --extra hub-gate" in caught.value.fix
    assert "pip install cryptography" in caught.value.fix
    assert PASS not in str(caught.value)


def test_source_has_no_forbidden_dash_or_short_code() -> None:
    import re
    source = Path(gate.__file__).read_text()
    assert not any(char in source for char in (chr(0x2013), chr(0x2014)))
    assert not re.search(r"\b(R[S]|H[S]I)\b", source)


def test_gated_build_is_private_and_byte_identical(tmp_path: Path, no_network, capsys) -> None:
    import io
    import json

    from hub_scan import scan_dashes, scan_for_network, scan_internal_names
    from hub_support import make_run_folder
    from mindrian_eureka.hub.reader import load_run
    from mindrian_eureka.hub.writer import HubRequest, build_hub
    from mindrian_eureka.run.console import Console
    from test_hub_writer import tree

    crypto()
    run = make_run_folder(tmp_path, seed_text="Synthetic locked-fixture-only marker for privacy.")
    records = load_run(run).records
    first, second = tmp_path / "first", tmp_path / "second"
    errors = io.StringIO()
    request = HubRequest(run, first, password=PASS)
    summary = build_hub(request, Console(stderr=errors))
    build_hub(HubRequest(run, second, password=PASS), Console(stderr=errors))
    assert tree(first) == tree(second)
    manifest = json.loads((first / "hub-manifest.json").read_bytes())
    assert manifest["gated"] is True and "counts" not in manifest
    assert summary.gated and summary.to_json_dict()["gated"] is True
    assert "Gate: on." in summary.lines()
    assert PASS not in repr(request) and PASS not in repr(summary)
    fingerprint = load_run(run).manifest_sha256
    for name, raw in tree(first).items():
        assert PASS.encode() not in raw
        if name.startswith(("assets/fonts/", "vendor/")):
            continue
        for record in records:
            assert record.id.encode() not in raw
            assert record.title.encode() not in raw
            assert record.text[:12].encode() not in raw
        if name == "hub-manifest.json":
            # This required opaque provenance hash is public metadata, not clear record data.
            assert manifest["run"]["manifest_sha256"] == fingerprint
        else:
            assert fingerprint.encode() not in raw
    envelope = json.loads((first / "hub-data.js").read_text()
                          .removeprefix("window.HUB_ENVELOPE = ").rstrip(";\n"))
    decrypted = json.loads(gate.decrypt_payload(envelope, PASS))
    assert decrypted["records"][0]["id"] == records[0].id
    assert scan_for_network(first) == []
    assert scan_dashes(first) == []
    assert scan_internal_names(first) == []
    assert no_network == []
    assert PASS not in errors.getvalue() and PASS not in repr(capsys.readouterr())


def test_gated_plaintext_guard_short_warning_and_ungated_optional(tmp_path, monkeypatch) -> None:
    import io

    from hub_support import make_run_folder
    from mindrian_eureka.hub import writer
    from mindrian_eureka.hub.writer import HubRequest, build_hub
    from mindrian_eureka.run.console import Console
    from mindrian_eureka.run.contracts import RunError

    crypto()
    run = make_run_folder(tmp_path)
    errors = io.StringIO()
    out = tmp_path / "short"
    build_hub(HubRequest(run, out, password="test-short"), Console(stderr=errors))
    assert "The passphrase is short." in errors.getvalue()
    assert "test-short" not in errors.getvalue()
    original = writer.build_payload
    def broken(*args, **kwargs):
        payload = original(*args, **kwargs)
        payload["records"][0]["label"] = ""
        return payload
    with monkeypatch.context() as patch:
        patch.setattr(writer, "build_payload", broken)
        with pytest.raises(RunError, match="Hub data check failed"):
            build_hub(HubRequest(run, tmp_path / "bad", password=PASS), Console())
        assert not (tmp_path / "bad").exists()
    original_import = builtins.__import__
    def blocked(name, *args, **kwargs):
        if name.startswith("cryptography"):
            raise ImportError("test cipher unavailable")
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", blocked)
    plain = tmp_path / "plain"
    summary = build_hub(HubRequest(run, plain), Console(quiet=True))
    assert not summary.gated
    assert (plain / "hub-data.js").read_text().startswith("window.HUB = ")
    assert (plain / "hub.html").read_bytes() != (out / "hub.html").read_bytes()


@pytest.mark.parametrize("name,value", [("MISSING_GATE_TEST", None), ("EMPTY_GATE_TEST", ""),
                                       ("invalid-name", PASS)])
def test_password_environment_errors(tmp_path, monkeypatch, capsys, name, value) -> None:
    from mindrian_eureka.cli import main
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)
    assert main(["hub", str(tmp_path / "run"), "--out", str(tmp_path / "hub"),
                 "--password-env", name]) == 2
    output = capsys.readouterr()
    assert PASS not in output.err + output.out
    if value is None or value == "":
        assert name in output.err
        assert "Set the variable in your shell" in output.err


def test_command_uses_only_named_environment_variable(tmp_path, monkeypatch, capsys) -> None:
    import json

    from hub_support import make_run_folder
    from mindrian_eureka.cli import main
    from test_run_cli import help_text
    crypto()
    run = make_run_folder(tmp_path)
    monkeypatch.setenv("EUREKA_SYNTHETIC_GATE_TEST", PASS)
    out = tmp_path / "hub"
    assert main(["hub", str(run), "--out", str(out), "--password-env",
                 "EUREKA_SYNTHETIC_GATE_TEST", "--json"]) == 0
    output = capsys.readouterr()
    assert PASS not in output.out + output.err
    assert json.loads(output.out)["gated"] is True
    help_output = help_text(capsys, "hub")
    assert "--password-env" in help_output and "does not protect a computer" in help_output
    with pytest.raises(SystemExit) as caught:
        main(["hub", str(run), "--password", "not-a-credential-test-argument"])
    assert caught.value.code == 2


def test_envelope_scan_requires_passive_data_and_checks_links(tmp_path: Path) -> None:
    from hub_scan import scan_for_network
    from mindrian_eureka.hub.contracts import js_assignment
    data = tmp_path / "hub-data.js"
    data.write_bytes(js_assignment("HUB_ENVELOPE", {"ciphertext": "//opaque/bytes/"}))
    assert scan_for_network(tmp_path) == []
    with data.open("a") as stream:
        stream.write('fetch("./must-fail");')
    assert scan_for_network(tmp_path)
    data.write_text('window.HUB = {"x": NaN};\n')
    assert scan_for_network(tmp_path)
    data.write_bytes(js_assignment("HUB", {"records": [{"source_link": "https://host/x"}]}))
    assert scan_for_network(tmp_path)
    data.write_bytes(js_assignment("HUB", {"records": [
        {"source_link": "#local", "text": "https://source-text.invalid is quoted data"}]}))
    assert scan_for_network(tmp_path) == []


def test_locked_markup_does_not_depend_on_source_strings(tmp_path: Path) -> None:
    import io
    import json

    from hub_support import make_run_folder
    from mindrian_eureka.hub.writer import HubRequest, build_hub
    from mindrian_eureka.run.console import Console
    crypto()
    normal = make_run_folder(tmp_path / "normal", n_records=18)
    hostile = make_run_folder(tmp_path / "hostile", hostile=True)
    first, second = tmp_path / "first", tmp_path / "second"
    for run, out in ((normal, first), (hostile, second)):
        build_hub(HubRequest(run, out, password=PASS), Console(stderr=io.StringIO()))
    assert (first / "hub.html").read_bytes() == (second / "hub.html").read_bytes()
    assert b"data-record-id" not in (second / "hub.html").read_bytes()
    assert b"data-pair-key" not in (second / "hub.html").read_bytes()
    envelope = json.loads((second / "hub-data.js").read_text()
                          .removeprefix("window.HUB_ENVELOPE = ").rstrip(";\n"))
    assert set(envelope) == {"schema", "kdf", "cipher", "ciphertext"}
