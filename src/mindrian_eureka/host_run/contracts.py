"""Request rules and refusal shape of the host pair screen run.

A host sends a bundle of artifacts. `normalize_request` checks the bundle against closed
rules and returns a `NormalizedRequest`, or raises `HostRunError` with a typed code.
No message holds the text of an artifact or a machine path.

This module is plain Python. It imports no numpy, pydantic or mcp.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from mindrian_eureka.limits import (
    MAX_ARTIFACTS,
    MAX_RECORD_CHARS,
    MAX_TOP_K,
    MAX_TOTAL_TEXT_BYTES,
)
from mindrian_eureka.run.contracts import LABEL, SUMMARY_LINE, normalize_text, sha256_text

__all__ = [
    "APPROVAL_REF_PATTERN",
    "ARTIFACT_KEYS",
    "CAPABILITY_ID",
    "LABEL",
    "PLAN_SCHEMA",
    "PLAN_TTL_SECONDS",
    "REASONS",
    "RECEIPT_RETENTION_SECONDS",
    "REQUEST_KEYS",
    "RESULT_SCHEMA",
    "SUMMARY_LINE",
    "Approval",
    "Artifact",
    "HostRunError",
    "NormalizedRequest",
    "normalize_request",
    "sanitized_record_part",
]

CAPABILITY_ID: Final[str] = "opportunity.run_pair_screen"
PLAN_SCHEMA: Final[str] = "eureka.pair-screen-plan.v1"
RESULT_SCHEMA: Final[str] = "eureka.pair-screen.v1"
PLAN_TTL_SECONDS: Final[int] = 86400
RECEIPT_RETENTION_SECONDS: Final[int] = 30 * 86400

# One to 128 characters. The first is a letter or digit. Use `fullmatch`.
APPROVAL_REF_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:#/-]{0,127}")
_DIGEST_PATTERN: Final[re.Pattern[str]] = re.compile(r"[a-f0-9]{64}")
_SHA256_PATTERN: Final[re.Pattern[str]] = re.compile(r"[a-fA-F0-9]{64}")
_KEY_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9_.-]{1,64}")
# The corpus builder rule for the id part of a record id (run/corpus.py).
_ID_UNSAFE: Final[re.Pattern[str]] = re.compile(r"[^A-Za-z0-9_.-]+")

REQUEST_KEYS: Final[frozenset[str]] = frozenset(
    {"objective", "scope_id", "snapshot_id", "artifacts", "top_k", "approval"}
)
_REQUIRED_KEYS: Final[tuple[str, ...]] = ("objective", "scope_id", "snapshot_id", "artifacts")
ARTIFACT_KEYS: Final[frozenset[str]] = frozenset(
    {"id", "source_ref", "title", "text", "corpus", "media_type", "sha256"}
)
_ARTIFACT_REQUIRED: Final[tuple[str, ...]] = ("id", "source_ref", "text")
_APPROVAL_KEYS: Final[frozenset[str]] = frozenset({"plan_digest", "approval_ref"})

_MAX_OBJECTIVE_CHARS: Final[int] = 5000
_MAX_SCOPE_CHARS: Final[int] = 256
_MAX_ID_CHARS: Final[int] = 256
_MAX_SOURCE_REF_CHARS: Final[int] = 2048
_MAX_TITLE_CHARS: Final[int] = 2000
_MAX_MEDIA_TYPE_CHARS: Final[int] = 128
_MIN_ARTIFACTS: Final[int] = 2
_MAX_NAMED_IDS: Final[int] = 3
_MAX_SHOWN_ID_CHARS: Final[int] = 80

REASONS: Final[frozenset[str]] = frozenset(
    {
        "bad_request",
        "too_many_artifacts",
        "bundle_too_large",
        "duplicate_artifact_id",
        "id_collision",
        "artifact_hash_mismatch",
        "external_corpus_refused",
        "approval_missing",
        "approval_bad_reference",
        "plan_unknown",
        "plan_expired",
        "plan_consumed",
        "plan_mismatch",
        "local_model_unavailable",
        "too_few_usable_records",
    }
)


class HostRunError(Exception):
    """A refusal of a host request, with a typed code.

    Attributes:
        code: A code from `REASONS`.
        message: One plain sentence for the fault. It holds no artifact text and no path.
        fix: One plain sentence that says what to change.
    """

    def __init__(self, code: str, message: str, fix: str) -> None:
        if code not in REASONS:
            raise ValueError(f"Unknown refusal code: {code}")
        super().__init__(message)
        self.code = code
        self.message = message
        self.fix = fix

    def as_refusal(self) -> dict[str, str]:
        """Return the refusal as a plain dictionary with the six fixed keys."""
        return {
            "status": "refused",
            "reason": self.code,
            "message": self.message,
            "fix": self.fix,
            "label": LABEL,
            "room_write": "not_performed",
        }


@dataclass(frozen=True)
class Artifact:
    """One checked artifact of a host bundle.

    Attributes:
        id: The host artifact id, as sent.
        source_ref: The host source reference, as sent.
        title: The title, or an empty string.
        text: The text, as sent.
        text_sha256: The sha256 of the UTF-8 bytes of `text`, lowercase hex.
    """

    id: str
    source_ref: str
    title: str
    text: str
    text_sha256: str


@dataclass(frozen=True)
class Approval:
    """The approval block of a start request.

    Attributes:
        plan_digest: The digest of the plan, 64 lowercase hex characters.
        approval_ref: An audit reference. The engine cannot verify it.
    """

    plan_digest: str
    approval_ref: str


@dataclass(frozen=True)
class NormalizedRequest:
    """A host request that passed every rule.

    Attributes:
        objective: The objective sentence.
        scope_id: The scope id of the host.
        snapshot_id: The snapshot id of the host.
        top_k: The number of pairs to keep for each engine.
        artifacts: The artifacts, sorted by raw id.
        approval: The approval block, or None when the request has none.
    """

    objective: str
    scope_id: str
    snapshot_id: str
    top_k: int
    artifacts: tuple[Artifact, ...]
    approval: Approval | None


def sanitized_record_part(artifact_id: str) -> str:
    """Return the id part that the corpus builder derives from a CSV id cell.

    Args:
        artifact_id: A host artifact id.

    Returns:
        The id after text normalization, with each run of unsafe characters
        changed to one underscore. The corpus builder uses the same rule.
    """
    return _ID_UNSAFE.sub("_", normalize_text(artifact_id))


def _shown(value: str) -> str:
    """Return an id in a short form that is safe to put in a message."""
    flat = value.replace("\n", " ").replace("\r", " ")
    if len(flat) > _MAX_SHOWN_ID_CHARS:
        return flat[:_MAX_SHOWN_ID_CHARS] + "..."
    return flat


def _bad(message: str, fix: str) -> HostRunError:
    return HostRunError("bad_request", message, fix)


def _check_utf8(value: str, label: str) -> None:
    """Refuse a string that cannot be encoded as UTF-8, such as a lone surrogate."""
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise _bad(
            f"The {label} cannot be encoded as UTF-8.",
            f"Remove the invalid characters from the {label}.",
        ) from exc


def _text_field(raw: Mapping[str, Any], key: str, limit: int) -> str:
    value = raw[key]
    if not isinstance(value, str):
        raise _bad(f"The field {key} must be a string.", f"Send {key} as a string.")
    _check_utf8(value, f"field {key}")
    if not value.strip():
        raise _bad(f"The field {key} is empty.", f"Send a {key} with at least 1 character.")
    if len(value) > limit:
        raise _bad(
            f"The field {key} is longer than {limit} characters.",
            f"Send a {key} of {limit} characters or fewer.",
        )
    return value


def _check_keys(raw: Mapping[Any, Any]) -> None:
    unknown = [key for key in raw if key not in REQUEST_KEYS]
    if not unknown:
        return
    names = []
    for key in unknown[:_MAX_NAMED_IDS]:
        if isinstance(key, str) and _KEY_NAME_PATTERN.fullmatch(key):
            names.append(key)
        else:
            names.append("(unreadable key)")
    raise _bad(
        f"The request holds a key that is not allowed: {', '.join(names)}.",
        "Send only these keys: " + ", ".join(sorted(REQUEST_KEYS)) + ".",
    )


def _check_top_k(raw: Mapping[str, Any]) -> int:
    if "top_k" not in raw:
        return MAX_TOP_K
    value = raw["top_k"]
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= MAX_TOP_K:
        raise _bad(
            f"The field top_k must be a whole number from 1 to {MAX_TOP_K}.",
            f"Send top_k from 1 to {MAX_TOP_K}, or leave it out.",
        )
    return value


def _check_artifact(position: int, item: Any) -> Artifact:
    where = f"artifact {position + 1}"
    if not isinstance(item, dict):
        raise _bad(f"The {where} must be an object.", "Send each artifact as an object.")
    unknown = [key for key in item if key not in ARTIFACT_KEYS]
    if unknown:
        raise _bad(
            f"The {where} holds a key that is not allowed.",
            "Send only these keys: " + ", ".join(sorted(ARTIFACT_KEYS)) + ".",
        )
    for key in _ARTIFACT_REQUIRED:
        if key not in item:
            raise _bad(f"The {where} has no {key}.", f"Add {key} to each artifact.")
    artifact_id = item["id"]
    source_ref = item["source_ref"]
    text = item["text"]
    title = item.get("title", "")
    for key, value in (("id", artifact_id), ("source_ref", source_ref), ("text", text)):
        if not isinstance(value, str) or not value.strip():
            raise _bad(
                f"The {key} of {where} must be a string with at least 1 character.",
                f"Send a non-empty {key} for each artifact.",
            )
    if not isinstance(title, str):
        raise _bad(f"The title of {where} must be a string.", "Send title as a string.")
    for key, value in (("id", artifact_id), ("source_ref", source_ref), ("title", title)):
        _check_utf8(value, f"{key} of {where}")
    if len(artifact_id) > _MAX_ID_CHARS:
        raise _bad(
            f"The id of {where} is longer than {_MAX_ID_CHARS} characters.",
            f"Use an id of {_MAX_ID_CHARS} characters or fewer.",
        )
    if len(source_ref) > _MAX_SOURCE_REF_CHARS:
        raise _bad(
            f"The source_ref of {where} is longer than {_MAX_SOURCE_REF_CHARS} characters.",
            f"Use a source_ref of {_MAX_SOURCE_REF_CHARS} characters or fewer.",
        )
    if len(title) > _MAX_TITLE_CHARS:
        raise _bad(
            f"The title of {where} is longer than {_MAX_TITLE_CHARS} characters.",
            f"Use a title of {_MAX_TITLE_CHARS} characters or fewer.",
        )
    media_type = item.get("media_type")
    if media_type is not None and (
        not isinstance(media_type, str) or len(media_type) > _MAX_MEDIA_TYPE_CHARS
    ):
        raise _bad(
            f"The media_type of {where} is not valid.",
            f"Send media_type as a string of {_MAX_MEDIA_TYPE_CHARS} characters or fewer.",
        )
    if len(text) > MAX_RECORD_CHARS:
        raise HostRunError(
            "bundle_too_large",
            f"The text of {where} is longer than {MAX_RECORD_CHARS} characters.",
            f"Shorten the text to {MAX_RECORD_CHARS} characters or split the artifact.",
        )
    corpus = item.get("corpus", "room")
    if corpus != "room":
        raise HostRunError(
            "external_corpus_refused",
            f"The {where} is not from the room corpus.",
            "Send room artifacts only. Set corpus to room, or leave it out.",
        )
    try:
        digest = sha256_text(text)
    except UnicodeEncodeError as exc:
        raise _bad(
            f"The text of {where} cannot be encoded as UTF-8.",
            "Remove the invalid characters from the text.",
        ) from exc
    given = item.get("sha256")
    if given is not None:
        if not isinstance(given, str) or not _SHA256_PATTERN.fullmatch(given):
            raise _bad(
                f"The sha256 of {where} is not 64 hex characters.",
                "Send sha256 as 64 hex characters, or leave it out.",
            )
        if given.lower() != digest:
            raise HostRunError(
                "artifact_hash_mismatch",
                f"The sha256 of artifact {_shown(artifact_id)} does not match its text.",
                "Send the sha256 of the UTF-8 text, or leave sha256 out.",
            )
    return Artifact(
        id=artifact_id, source_ref=source_ref, title=title, text=text, text_sha256=digest
    )


def _check_unique_ids(artifacts: list[Artifact]) -> None:
    seen: set[str] = set()
    repeated: list[str] = []
    for artifact in artifacts:
        if artifact.id in seen and artifact.id not in repeated:
            repeated.append(artifact.id)
        seen.add(artifact.id)
    if repeated:
        names = ", ".join(_shown(name) for name in repeated[:_MAX_NAMED_IDS])
        raise HostRunError(
            "duplicate_artifact_id",
            f"These artifact ids appear more than once: {names}.",
            "Give each artifact a unique id.",
        )
    owners: dict[str, str] = {}
    for artifact in artifacts:
        part = sanitized_record_part(artifact.id)
        if not part.strip("."):
            raise _bad(
                f"The id {_shown(artifact.id)} has no usable characters.",
                "Use an id with letters, digits, underscore, dot or hyphen.",
            )
        other = owners.get(part)
        if other is not None:
            raise HostRunError(
                "id_collision",
                f"The ids {_shown(other)} and {_shown(artifact.id)} give the same record id.",
                "Rename one id so that the two differ in letters or digits.",
            )
        owners[part] = artifact.id


def _check_approval(value: Any) -> Approval | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise _bad("The field approval must be an object.", "Send approval as an object.")
    if set(value) != _APPROVAL_KEYS:
        raise _bad(
            "The field approval must hold exactly plan_digest and approval_ref.",
            "Send approval with the keys plan_digest and approval_ref only.",
        )
    digest = value["plan_digest"]
    reference = value["approval_ref"]
    if not isinstance(digest, str) or not _DIGEST_PATTERN.fullmatch(digest):
        raise HostRunError(
            "approval_bad_reference",
            "The plan_digest is not 64 lowercase hex characters.",
            "Send the plan_digest that the plan tool returned.",
        )
    if not isinstance(reference, str) or not APPROVAL_REF_PATTERN.fullmatch(reference):
        raise HostRunError(
            "approval_bad_reference",
            "The approval_ref is not valid.",
            "Send 1 to 128 characters: letters, digits and _ . : # / - only.",
        )
    return Approval(plan_digest=digest, approval_ref=reference)


def normalize_request(raw: Any) -> NormalizedRequest:
    """Check a host request and return it in normal form.

    Args:
        raw: The request as a host sent it.

    Returns:
        The checked request. Artifacts are sorted by raw id.

    Raises:
        HostRunError: A rule is broken. The code says which rule.
    """
    if not isinstance(raw, dict):
        raise _bad("The request must be an object.", "Send the request as an object.")
    _check_keys(raw)
    for key in _REQUIRED_KEYS:
        if key not in raw:
            raise _bad(f"The request has no {key}.", f"Add {key} to the request.")
    objective = _text_field(raw, "objective", _MAX_OBJECTIVE_CHARS)
    scope_id = _text_field(raw, "scope_id", _MAX_SCOPE_CHARS)
    snapshot_id = _text_field(raw, "snapshot_id", _MAX_SCOPE_CHARS)
    top_k = _check_top_k(raw)

    items = raw["artifacts"]
    if not isinstance(items, list):
        raise _bad("The field artifacts must be a list.", "Send artifacts as a list.")
    if len(items) > MAX_ARTIFACTS:
        raise HostRunError(
            "too_many_artifacts",
            f"The request holds more than {MAX_ARTIFACTS} artifacts.",
            f"Split the room into snapshots of {MAX_ARTIFACTS} artifacts or fewer.",
        )
    if len(items) < _MIN_ARTIFACTS:
        raise _bad(
            f"The request needs at least {_MIN_ARTIFACTS} artifacts.",
            f"Send {_MIN_ARTIFACTS} or more artifacts.",
        )
    artifacts = [_check_artifact(position, item) for position, item in enumerate(items)]
    _check_unique_ids(artifacts)
    total = sum(len(artifact.text.encode("utf-8")) for artifact in artifacts)
    if total > MAX_TOTAL_TEXT_BYTES:
        raise HostRunError(
            "bundle_too_large",
            f"The text of the bundle is larger than {MAX_TOTAL_TEXT_BYTES // (1024 * 1024)} MiB.",
            "Send fewer or shorter artifacts, or split the room into snapshots.",
        )
    approval = _check_approval(raw.get("approval"))
    return NormalizedRequest(
        objective=objective,
        scope_id=scope_id,
        snapshot_id=snapshot_id,
        top_k=top_k,
        artifacts=tuple(sorted(artifacts, key=lambda artifact: artifact.id)),
        approval=approval,
    )
