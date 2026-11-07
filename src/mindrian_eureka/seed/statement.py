"""The statement draft of a bank entry (Phase 2.3, D-01).

The draft is built from run facts only. `opportunity.prepare_statement` is not called:
it needs dimension signals and a host rank that a run does not hold. The draft keeps the
same gate fields (`critic: pending`, `banked: false`) and the label.

Import rule: the standard library, `..run.contracts` and `.contracts`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ..run.contracts import (
    LABEL,
    PAIR_CLASS_CROSS,
    PAIR_CLASS_LICENSED_LICENSED,
    PAIR_CLASS_OPEN_OPEN,
)
from .contracts import STATEMENT_BASIS, STATEMENT_METHOD

_CLASS_SENTENCES = {
    PAIR_CLASS_CROSS: "One record is open and the other is licensed.",
    PAIR_CLASS_OPEN_OPEN: "Both records are open.",
    PAIR_CLASS_LICENSED_LICENSED: "Both records are licensed.",
}
_OPENING = "Hypothesis to review: {a} and {b} may belong in one room."
_READS = "The run reads this pair as: {readings}"
_CLOSING = "This is a lead for human review."


def display_name(record_id: str, title: str) -> str:
    """Return the title on one line, or the record id when the title is empty."""
    name = " ".join(title.split())
    return name if name else " ".join(record_id.split())


def build_statement(
    left: tuple[str, str],
    right: tuple[str, str],
    pair_class: str | None,
    readings: Sequence[str],
) -> dict[str, Any]:
    """Return the `statement` object of a bank entry.

    Args:
        left: The record id and title of the first record.
        right: The record id and title of the second record.
        pair_class: The pair class of the run, or None.
        readings: The distinct reading sentences of the engines, in engine order.

    Returns:
        The statement. It holds no number and no dash of its own.
    """
    name_a = display_name(*left)
    name_b = display_name(*right)
    joined = " ".join(readings)
    parts = [_OPENING.format(a=name_a, b=name_b), _READS.format(readings=joined)]
    if pair_class is not None:
        parts.append(_CLASS_SENTENCES[pair_class])
    parts.append(_CLOSING)
    fields: dict[str, str] = {"tech_a": name_a, "tech_b": name_b, "reading": joined}
    if pair_class is not None:
        fields["pair_class"] = pair_class
    return {
        "text": " ".join(parts),
        "fields": fields,
        "critic": "pending",
        "banked": False,
        "label": LABEL,
        "method": STATEMENT_METHOD,
        "basis": STATEMENT_BASIS,
    }
