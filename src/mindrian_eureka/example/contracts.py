"""Constants of the public example check and its expected-hash file.

This module holds every constant of the check. Later modules import these names and never
retype them.

Import rule: the standard library only.
"""

from __future__ import annotations

EXPECTED_SCHEMA = "eureka.example-expected-hashes.v1"
REPORT_SCHEMA = "eureka.example-check.v1"

OUTPUT_FILES: tuple[str, ...] = (
    "corpus/records.jsonl",
    "ranked-pairs.md",
    "unusual-pairs.json",
    "wording-and-meaning-pairs.json",
)
PAIR_FILES: tuple[str, ...] = (
    "ranked-pairs.md",
    "unusual-pairs.json",
    "wording-and-meaning-pairs.json",
)
MANIFEST_NAME = "manifest.json"

MAX_JSON_BYTES = 20_000_000

# --- The shipped example ----------------------------------------------------

EXAMPLE_ID = "public-arxiv-36"
EXAMPLE_INPUT = "tests/fixtures/hub_public/input"
EXAMPLE_LICENSE_RECORD = "tests/fixtures/hub_public/SOURCE.md"
EXAMPLE_LICENSE = "CC0 1.0 Universal"
EXAMPLE_RECORDS = 36
EXAMPLE_MODEL_NOTE = (
    "This example uses the meaning model all-MiniLM-L6-v2. "
    "The earlier JHTV replay used the model mdbr-leaf-ir, which this example does not use."
)
EXAMPLE_COMMAND = "uv run eureka run tests/fixtures/hub_public/input --out <run-folder> --threads 1"
EXAMPLE_DIR = "examples/public-example"
EXPECTED_NAME = "expected-hashes.json"
REFERENCE_RUN_NAME = "reference-run"

ENGINE_SOURCE_FILES: tuple[str, ...] = (
    "src/mindrian_eureka/hsi_reference.py",
    "src/mindrian_eureka/opportunity_pairs/algorithm.py",
)

# --- Checks -----------------------------------------------------------------

CHECK_RUN_FOLDER = ("X1", "run_folder")
CHECK_INPUTS = ("X2", "inputs")
CHECK_SETTINGS = ("X3", "settings")
CHECK_MODEL = ("X4", "model")
CHECK_ENGINE = ("X5", "engine")
CHECK_OUTPUTS = ("X6", "outputs")
CHECK_LABEL = ("X7", "label")

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
RESULT_MATCH_ID = "match"
RESULT_NO_MATCH_ID = "no_match"

RESULT_MATCH = "Result: MATCH. This run is identical to the shipped expected hashes."
RESULT_NO_MATCH = "Result: NO MATCH. This run differs from the shipped expected hashes."

NOT_REPRODUCED_TEXT = (
    "The input, settings, model and engine match, but the outputs differ. "
    "This run is not reproduced on this machine. "
    "The usual cause is another platform or another library version; read the INFO lines."
)

# --- Runs that are not CPU-exact ----------------------------------------------
#
# The class names repeat the constants of `mindrian_eureka.encoder_spec`. This module does not
# import that module, because of the import rule of this package. A test compares the two copies.

ENCODER_KEY = "encoder"
DETERMINISM_CPU_EXACT = "cpu-exact"
DETERMINISM_GPU_APPROX = "gpu-approx"
OVERLAP_FILES: tuple[str, ...] = ("unusual-pairs.json", "wording-and-meaning-pairs.json")

# The share of reference pair ids that a gpu-approx run must also list. Only the recorded result
# of the GPU spike may set this number (plan 05-08 names the record docs/encoder-spike-results.md).
# While it is None, a gpu-approx run is never a MATCH.
GPU_APPROX_MIN_OVERLAP: float | None = None

NO_THRESHOLD_TEXT = "no overlap threshold has been measured yet"

GPU_APPROX_NOTE = (
    "This run used a non-exact encoder setup of class gpu-approx. "
    "The bytes of the pair files are not compared. "
    "The ranking overlap with the shipped reference run decides. "
    'Every result is "candidate, not verified".'
)
