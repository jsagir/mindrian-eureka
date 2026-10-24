"""Shared contracts for `eureka run` and `eureka doctor`.

This module holds exit codes, error classes, fixed label texts, schema ids,
the record type and the text normalizer. It imports only the standard library,
so importing it never loads numpy, scikit-learn or torch.
"""

from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass

# --- Exit codes -------------------------------------------------------------

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2
EXIT_INTERRUPTED = 130


# --- Errors -----------------------------------------------------------------


class EurekaError(Exception):
    """Base class for errors that the command line shows to the user.

    Attributes:
        message: What went wrong, in plain English.
        fix: The exact action that fixes it, or None.
    """

    exit_code: int = EXIT_FAILURE

    def __init__(self, message: str, *, fix: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.fix = fix


class UsageError(EurekaError):
    """The user gave wrong arguments or bad input settings (exit code 2)."""

    exit_code = EXIT_USAGE


class RunError(EurekaError):
    """The run failed after the arguments were accepted (exit code 1)."""

    exit_code = EXIT_FAILURE


# --- Text constants ---------------------------------------------------------

LABEL = "candidate, not verified"
SUMMARY_LINE = "All results are candidates, not verified. They are leads for human review."

UNUSUAL_PAIRS_NAME = "Find Unusual Pairs Across a Research Collection"
WORDING_AND_MEANING_NAME = "Rank Unusual Pairs by Wording and Meaning"
UNUSUAL_PAIRS_CAPABILITY = "opportunity.find_cross_domain_pairs"
WORDING_AND_MEANING_CAPABILITY = "portfolio.find_hybrid_similarity_pairs"


# --- Schema ids -------------------------------------------------------------

PAIRS_SCHEMA = "eureka.run-pairs.v1"
MANIFEST_SCHEMA = "eureka.run-manifest.v1"
CORPUS_SCHEMA = "eureka.run-corpus.v1"
RUN_INFO_SCHEMA = "eureka.run-info.v1"
MAPPING_SCHEMA = "eureka.run-mapping.v1"


# --- Score meaning ----------------------------------------------------------

SCORE_MEANING: dict[str, str] = {
    "unusual_pairs": (
        "Each pair has a wording score and a meaning score. "
        "The wording score shows how alike the two records are in vocabulary structure "
        "and word overlap. "
        "The meaning score shows how close their ideas are. "
        "Both scores are put on a common scale. "
        "The rank follows how far the two scores disagree. "
        "A high rank means the records read differently from how close their ideas are, "
        "or the reverse. "
        "The score is a screening signal. "
        "It does not show novelty, evidence, demand or value."
    ),
    "wording_and_meaning": (
        "Each pair has a wording score and a meaning score on a 0 to 1 scale. "
        "The wording score shows how many words and word patterns the two records share. "
        "The meaning score shows how close their ideas are. "
        "The rank follows the size of the gap between them. "
        "A high rank means the records share words but not meaning, "
        "or share meaning but not words. "
        "The score is a screening signal. "
        "It does not show novelty, evidence, demand or value."
    ),
}


# --- Record -----------------------------------------------------------------


@dataclass(frozen=True)
class Record:
    """One record of the clean corpus.

    Attributes:
        id: The stable record id.
        title: The record title.
        text: The normalized body text.
        source_ref: A relative locator of the source. Never an absolute path.
        source_file: The relative path of the input file that holds the record.
        text_sha256: The sha256 of `text`, as lowercase hex.
    """

    id: str
    title: str
    text: str
    source_ref: str
    source_file: str
    text_sha256: str

    @property
    def model_text(self) -> str:
        """Return the text that both engines score: title, blank line, body, stripped."""
        return f"{self.title}\n\n{self.text}".strip()


# --- Helpers ----------------------------------------------------------------


def normalize_text(text: str) -> str:
    """Normalize line ends and Unicode form and strip the ends.

    Args:
        text: Any text.

    Returns:
        The text with CRLF and lone CR changed to LF, in NFC form, stripped.
    """
    unified = text.replace("\r\n", "\n").replace("\r", "\n")
    return unicodedata.normalize("NFC", unified).strip()


def sha256_bytes(data: bytes) -> str:
    """Return the sha256 of `data` as lowercase hex."""
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    """Return the sha256 of the UTF-8 bytes of `text` as lowercase hex."""
    return sha256_bytes(text.encode("utf-8"))
