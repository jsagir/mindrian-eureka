"""Constants of the room seed contract `eureka.room-seed.v1`.

This module holds every seed constant. Later seed modules import these names and never
retype them. The contract text is `docs/room-seed-contract.md`; the closed schema is
`data/schemas/room-seed.v1.json`.

Import rule: the standard library only.
"""

from __future__ import annotations

import re

SEED_SCHEMA = "eureka.room-seed.v1"
SEED_SUMMARY_SCHEMA = "eureka.seed-summary.v1"

OUTPUT_SEED = "seed.json"
EVIDENCE_DIR = "evidence"

SEED_KIND_PAIR = "pair"
SEED_KIND_CLUSTER = "cluster"

ROLE_PAIR_MEMBER = "pair_member"
ROLE_SPINE = "spine"
ROLE_NEIGHBOUR = "neighbour"

# The limit that the engine runner uses for a record excerpt.
EVIDENCE_EXCERPT_CHARS = 1600
MIN_DEGREE_DEFAULT = 3
DEFAULT_SEED_OUT_PREFIX = "eureka-seed"
RUN_PLACEHOLDER = "RUN_FOLDER"
PAIR_ID_PATTERN = re.compile(r"pair-[0-9a-f]{20}")

# Where a filled cell is held.
HELD_RECORD_TEXT = "record_text"
HELD_CARRIED = "carried"
HELD_EXPORT_ONLY = "export_only"

REASON_BLANK = "blank in this export"
REASON_NOT_IN_EXPORT = "not in this export; held in {source}"

REVIEW_STATUS_PROPOSED = "proposed"
STATEMENT_METHOD = "eureka.seed-statement.v1"
STATEMENT_BASIS = (
    "Built from run facts only. opportunity.prepare_statement was not called, because it "
    "needs dimension signals and a host rank that a run does not hold."
)
SCORE_NOTE = (
    "Scores are screening signals. They do not show novelty, evidence, demand or value."
)
MODEL_BOUNDARY = (
    "This seed was written offline by Eureka with no model. Working the room with Larry "
    "sends room content to the model provider. The partner decides."
)


def pair_command(pair_id: str) -> str:
    """Return the `eureka seed` command for one pair, with a placeholder for the run folder."""
    return f"eureka seed {RUN_PLACEHOLDER} --pair {pair_id}"
