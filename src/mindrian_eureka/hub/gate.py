"""Deterministic authenticated hub encryption with an optional cipher dependency.

Only standard-library modules and light contracts load at import time. The
versioned derivation follows Plan 14; it is not a general password-vault API.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from ..run.contracts import UsageError
from .contracts import HUB_ENVELOPE_SCHEMA

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PBKDF2_ITERATIONS = 600_000
SALT_BYTES = 16
NONCE_BYTES = 12
KDF_NAME = "PBKDF2-SHA256"
CIPHER_NAME = "AES-256-GCM"
SALT_CONTEXT = b"eureka.hub.gate.salt.v1"
NONCE_CONTEXT = b"eureka.hub.gate.nonce.v1"
AAD_CONTEXT = HUB_ENVELOPE_SCHEMA.encode("ascii") + b"|"
_ERROR = "Gate data is invalid or the passphrase did not match."


def derive_salt(run_fingerprint: str) -> bytes:
    """Derive the format's 16-byte salt from a 32-byte run-manifest digest.

    Args:
        run_fingerprint: The manifest SHA-256 in hexadecimal.

    Returns:
        A deterministic salt. It links repeated builds of the same run.

    Raises:
        ValueError: The fingerprint is not a SHA-256 hexadecimal digest.
    """
    if not re.fullmatch(r"[0-9a-fA-F]{64}", run_fingerprint):
        raise ValueError("A run fingerprint must be a SHA-256 hexadecimal digest.")
    return hashlib.sha256(SALT_CONTEXT + bytes.fromhex(run_fingerprint)).digest()[:SALT_BYTES]


def derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive 32 key bytes using UTF-8 and PBKDF2-HMAC-SHA256.

    Args:
        passphrase: Nonempty passphrase, never logged.
        salt: Exactly 16 bytes from the format derivation.

    Returns:
        Key bytes, which must never be placed in an envelope or report.

    Raises:
        UsageError: The passphrase is empty.
        ValueError: The salt has the wrong length.
    """
    if not passphrase:
        raise UsageError("The passphrase is empty.", fix="Use a nonempty passphrase.")
    if len(salt) != SALT_BYTES:
        raise ValueError("The gate salt has the wrong length.")
    return hashlib.pbkdf2_hmac(
        "sha256", passphrase.encode("utf-8"), salt, PBKDF2_ITERATIONS, dklen=32
    )


def derive_nonce(key: bytes, salt: bytes, plaintext: bytes) -> bytes:
    """Derive a 12-byte nonce from the key, salt and plaintext digest.

    Args:
        key: The 32-byte derived cipher key.
        salt: The format salt.
        plaintext: Canonical payload bytes.

    Returns:
        The truncated HMAC. Identical inputs intentionally repeat ciphertext.
        The versioned contexts and AAD form one format and must change together.
    """
    message = NONCE_CONTEXT + salt + hashlib.sha256(plaintext).digest()
    return hmac.new(key, message, hashlib.sha256).digest()[:NONCE_BYTES]


def associated_data(iterations: int) -> bytes:
    """Bind the envelope schema and iteration count into the authentication tag."""
    return AAD_CONTEXT + str(iterations).encode("ascii")


def _cipher(key: bytes) -> AESGCM:
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        raise UsageError(
            "The optional hub-gate dependency is not installed.",
            fix="Run uv sync --extra hub-gate, or pip install cryptography for a plain install.",
        ) from None
    return AESGCM(key)


def _b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def encrypt_payload(
    plaintext: bytes, passphrase: str, run_fingerprint: str
) -> dict[str, Any]:
    """Encrypt payload bytes into a deterministic WebCrypto-compatible envelope.

    Args:
        plaintext: Canonical JSON payload bytes.
        passphrase: Nonempty passphrase, never returned or logged.
        run_fingerprint: Run manifest SHA-256 in hexadecimal.

    Returns:
        Schema, KDF parameters, cipher parameters and tagged ciphertext. No key.

    Raises:
        UsageError: Empty passphrase or missing optional dependency.
        ValueError: Invalid fingerprint.
    """
    salt = derive_salt(run_fingerprint)
    key = derive_key(passphrase, salt)
    nonce = derive_nonce(key, salt, plaintext)
    ciphertext = _cipher(key).encrypt(nonce, plaintext, associated_data(PBKDF2_ITERATIONS))
    return {
        "schema": HUB_ENVELOPE_SCHEMA,
        "kdf": {"name": KDF_NAME, "iterations": PBKDF2_ITERATIONS, "salt": _b64(salt)},
        "cipher": {"name": CIPHER_NAME, "nonce": _b64(nonce)},
        "ciphertext": _b64(ciphertext),
    }


def _decode(value: object) -> bytes:
    if not isinstance(value, str):
        raise ValueError(_ERROR)
    return base64.b64decode(value, validate=True)


def _parts(envelope: Mapping[str, Any]) -> tuple[bytes, bytes, bytes]:
    if set(envelope) != {"schema", "kdf", "cipher", "ciphertext"}:
        raise ValueError(_ERROR)
    kdf = envelope["kdf"]
    cipher = envelope["cipher"]
    if envelope["schema"] != HUB_ENVELOPE_SCHEMA or not isinstance(kdf, Mapping):
        raise ValueError(_ERROR)
    if not isinstance(cipher, Mapping):
        raise ValueError(_ERROR)
    if set(kdf) != {"name", "iterations", "salt"} or set(cipher) != {"name", "nonce"}:
        raise ValueError(_ERROR)
    if kdf["name"] != KDF_NAME or cipher["name"] != CIPHER_NAME:
        raise ValueError(_ERROR)
    # Fixed supported work factor: an edited envelope cannot request unbounded work.
    if type(kdf["iterations"]) is not int or kdf["iterations"] != PBKDF2_ITERATIONS:
        raise ValueError(_ERROR)
    salt = _decode(kdf["salt"])
    nonce = _decode(cipher["nonce"])
    ciphertext = _decode(envelope["ciphertext"])
    if len(salt) != SALT_BYTES or len(nonce) != NONCE_BYTES or len(ciphertext) < 16:
        raise ValueError(_ERROR)
    return salt, nonce, ciphertext


def decrypt_payload(envelope: Mapping[str, Any], passphrase: str) -> bytes:
    """Authenticate an envelope and return its plaintext without exposing secrets.

    Args:
        envelope: The supported envelope shape.
        passphrase: Nonempty passphrase, never included in errors.

    Returns:
        Authenticated plaintext bytes.

    Raises:
        UsageError: Empty passphrase or missing optional dependency.
        ValueError: Wrong passphrase or invalid/tampered envelope.
    """
    try:
        salt, nonce, ciphertext = _parts(envelope)
        key = derive_key(passphrase, salt)
        return _cipher(key).decrypt(nonce, ciphertext, associated_data(PBKDF2_ITERATIONS))
    except UsageError:
        raise
    except Exception:
        # Cipher, decoding and shape errors are deliberately indistinguishable here.
        raise ValueError(_ERROR) from None
