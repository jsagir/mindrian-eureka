"""Limits shared by `eureka run`, the unusual-pairs runner and the wording-and-meaning adapter.

Keep every run limit in this one module so the engines and the command agree.
"""

from __future__ import annotations

from typing import Final

# Size of the stored JHTV pair file (docs/hsi-rs-jhtv-reproduction.md).
MAX_TOP_K: Final[int] = 200

# The value that reproduced the JHTV result (docs/rs-engine-parity.md section 6).
MAX_ARTIFACTS: Final[int] = 3000

# Ceiling for `--max-artifacts`. Memory grows with the square of the record count:
# about 1.7 GB at 2,117 records, ASSUMED about 3.4 GB at 3,000.
HARD_MAX_ARTIFACTS: Final[int] = 5000

# Limit per record text in hsi_engine.py.
MAX_RECORD_CHARS: Final[int] = 1_000_000

# Limit for the total text of one run in opportunity_pairs/runner.py.
MAX_TOTAL_TEXT_BYTES: Final[int] = 20 * 1024 * 1024

# Memory guard: each input file is read whole once so it can be hashed.
MAX_INPUT_FILE_BYTES: Final[int] = 256 * 1024 * 1024

# Drop threshold in hsi_reference.py. The corpus builder applies it,
# so both engines see the same records.
MIN_BODY_CHARS: Final[int] = 50
