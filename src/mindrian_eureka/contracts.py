"""Load and enforce the capability contracts shipped in the package."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


DATA_DIR = Path(__file__).resolve().parent / "data"
CATALOG_PATH = DATA_DIR / "capability-catalog.v1.json"


class ContractError(ValueError):
    """A request violates a published capability input schema."""


class ResultContractError(RuntimeError):
    """An engine result violates its published output schema."""


def catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def capability_record(capability_id: str) -> dict[str, Any] | None:
    return next((row for row in catalog().get("capabilities", [])
                 if row.get("id") == capability_id), None)


def schema_for(capability_id: str, direction: str) -> dict[str, Any] | None:
    if direction not in {"input", "output"}:
        raise ValueError("direction must be input or output")
    capability = capability_record(capability_id)
    if capability is None:
        return None
    relative = capability.get(f"{direction}_schema")
    if not relative:
        return None
    root = DATA_DIR.resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ContractError(f"{capability_id} has an invalid {direction} schema path")
    document = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(document)
    return document


def validate_request(capability_id: str, request: dict[str, Any]) -> None:
    """Enforce the published schema when present; legacy internal validators remain authoritative otherwise."""
    schema = schema_for(capability_id, "input")
    if schema is None:
        return
    _validate(capability_id, schema, request, ContractError, "request")


def validate_result(capability_id: str, result: dict[str, Any]) -> None:
    schema = schema_for(capability_id, "output")
    if schema is None:
        return
    _validate(capability_id, schema, result, ResultContractError, "result")


def _validate(capability_id: str, schema: dict[str, Any], value: Any,
              error_type: type[Exception], kind: str) -> None:
    errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda error: list(error.absolute_path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        raise error_type(f"{capability_id} {kind} {location}: {error.message}")
