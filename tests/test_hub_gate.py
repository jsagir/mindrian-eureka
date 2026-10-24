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


@pytest.mark.parametrize("mutation", ["password", "ciphertext", "nonce", "iterations", "schema", "base64"])
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
