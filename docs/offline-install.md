# Offline install

## What this page is for

This page explains how to install and check Eureka on a machine that may have no internet, for example a secure enclave. Every result of Eureka is a candidate, not verified. These pages describe the setup only.

## Assumptions

These points are ASSUMED. They are not confirmed.

- ASSUMED: the machine may run Linux, macOS or Windows.
- ASSUMED: the machine may have no route to PyPI (the Python package index).
- ASSUMED: the machine can receive files by an approved transfer.

The real machine is not known yet. For that reason `eureka doctor` prints both a Linux or macOS command and a Windows command where they differ. The uv install commands and the Windows `icacls` line come from the uv and Windows documentation. They were not run on the real machine. Confirm them there.

## What to carry in

Fetch these items on a machine with internet. Carry them in by the approved transfer.

1. The `uv` program from a trusted release.
2. A folder of Python wheels, or a uv cache, for `uv sync --extra modern-encoder`.
3. The `all-MiniLM-L6-v2` model folder. Fetch it once with:
   `uv run hf download sentence-transformers/all-MiniLM-L6-v2 --local-dir all-MiniLM-L6-v2`
   The command syntax was checked against `hf download --help`.
4. The input files (CSV or Markdown) and the Eureka source folder.

## Steps

Run the steps in order. Where the two systems differ, both lines are given.

1. Put `uv` in a folder on `PATH`, then check it.
   - On Linux or macOS: `uv --version`
   - On Windows (PowerShell): `uv --version`
   - With internet instead, install it: on Linux or macOS `curl -LsSf https://astral.sh/uv/install.sh | sh`; on Windows `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`.
2. Install the libraries without a network call.
   - On Linux or macOS: `uv sync --extra modern-encoder --offline`
   - On Windows (PowerShell): `uv sync --extra modern-encoder --offline`
   - Without a uv cache, use the wheel folder: `uv pip install --no-index --find-links <wheel-folder> sentence-transformers`
3. Point Eureka to the model folder. Use the absolute path.
   - On Linux or macOS: `export MINDRIAN_EUREKA_RS_MODEL_PATH=/absolute/path/to/all-MiniLM-L6-v2`
   - On Windows (PowerShell): `$env:MINDRIAN_EUREKA_RS_MODEL_PATH = "C:\path\to\all-MiniLM-L6-v2"`
   - You can also pass `--model-path <folder>` to each command.
4. Run the check: `eureka doctor`
5. Test the input without a model load: `eureka run <folder> --dry-run`
6. Run it: `eureka run <folder>`

## What the doctor checks

`eureka doctor` checks Python 3.11 or newer, uv, the encoder libraries, the local model, the cache folder, the data folder and the offline variables. Add `--load-model` to load the model and encode one sentence. Add `--json` for a result that a program can read.

| Status | Meaning |
|--------|---------|
| PASS | The check is fine. |
| WARN | Something is not ideal. A run can still work. The fix is printed. |
| FAIL | A run cannot work or is not safe. The exact fix is printed. |

The exit code is 0 when no check is FAIL. The exit code is 1 when any check is FAIL. A missing model is always a FAIL, with every searched place listed. The doctor prints fix commands. It never runs them.

The doctor looks for the model in this fixed order: `--model-path`, `MINDRIAN_EUREKA_RS_MODEL_PATH`, `MINDRIAN_EUREKA_HSI_MODEL_PATH`, then the Hugging Face cache. A source that is set but invalid stops the search. It never falls through to another model.

## Privacy

- The run and the doctor make no network call and download no model.
- The run writes only the output folder, the embedding cache and the job data folder.
- On Linux and macOS the cache and data folders must be owner-only (mode 700). The doctor checks this and prints a `chmod` fix.
- On Windows the permission check is not done. The doctor gives a warning and prints an `icacls` command. This text is ASSUMED. Confirm it on the real machine.

## Candidate wording

Every result is "candidate, not verified". A ranked pair is a lead for human review. It does not show novelty, evidence or value. This page was not tested on the enclave.
