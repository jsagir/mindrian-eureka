# Contributing

Thanks for helping improve MindrianOS Eureka. This repository is private and contains methods, evaluations, and source-derived material with differing review status. Treat the repository as confidential and follow the project boundaries below.

## Before you change code

1. Read the [README](README.md), [architecture](docs/architecture.md), and [capability catalog](docs/capability-catalog.md).
2. Check [open decisions](docs/open-decisions.md) and the [engine source ledger](docs/engine-source-ledger.md) for constraints on the area you plan to change.
3. Keep changes focused. Preserve stable capability IDs unless a migration is explicitly part of the change.

## Adding or changing a capability

- Describe the user job and when to use it in plain language.
- Update the machine-readable catalog and capability manifest together. Keep maturity, inputs, network behavior, side effects, provenance, and limitations explicit.
- Version input and result contracts when their meaning or shape changes.
- Document what the method does not establish. Similarity is not novelty; a candidate is not a qualified opportunity; generated hypotheses are not evidence.
- Keep room access, user consent, external research, Theo calls, and portfolio writes in the MindrianOS host.
- Add only synthetic or explicitly approved evaluation data. Do not commit credentials, private room exports, or user data.
- Update the relevant engine guide and [using-capabilities guide](docs/using-capabilities.md) so CLI and MCP callers receive consistent instructions.

## Local development

Use Python 3.11 or newer and `uv`:

```bash
uv sync --extra mcp-server
uv run eureka capabilities
```

For the local semantic encoder, install `--extra modern-encoder` and configure a model already present on disk. Do not add model downloads or network access to a capability without an approved architecture change.

After `uv sync --extra modern-encoder`, run `eureka doctor`. It checks Python, uv, the encoder libraries, the local model, the cache folder, the data folder and the offline variables, and it prints the exact fix for each problem. For an install on a machine without internet, read [offline install](docs/offline-install.md).

### Checks

`pytest`, `mypy` and `ruff` are user-level tools (found on `PATH`). They are not project dependencies. A dev dependency group would change `uv.lock`, and the Docker image build uses `uv sync --frozen --no-dev`. The decision to add a dev group is made together with the next `uv lock` run that has network access.

Run the tests:

```bash
PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider
```

Check strict typing on the new modules:

```bash
mypy --strict --ignore-missing-imports --follow-imports=silent --python-executable "$(command -v python3)" src/mindrian_eureka/hub src/mindrian_eureka/run src/mindrian_eureka/doctor.py src/mindrian_eureka/models.py src/mindrian_eureka/limits.py
```

Check the lint rules:

```bash
ruff check src/mindrian_eureka/hub src/mindrian_eureka/run src/mindrian_eureka/doctor.py src/mindrian_eureka/models.py src/mindrian_eureka/limits.py tests/test_run_*.py tests/test_doctor.py tests/test_models.py tests/test_hub_*.py tests/hub_*.py
```

Browser tests need a Playwright install and otherwise skip; `EUREKA_REQUIRE_BROWSER=1` makes missing browser tools a failure.

Strict typing is required for the new modules only. Older modules (`cli.py`, `runner.py`, `hsi_engine.py`) are known to fail it. Do not widen the strict command to them in the same change.

Before opening a pull request, run the checks relevant to your change and describe their results. If a check cannot run, state why and identify what remains unverified. Never describe an unevaluated method as validated.

## Pull requests

Keep the pull request focused and include:

- the user job or engineering issue addressed;
- behavior and contract changes, including migration notes when needed;
- evaluation evidence and limitations;
- data, network, dependency, and source-license implications;
- commands run and their results.

Use the pull request template as a final review checklist. Do not include secrets or confidential user material in the title, description, logs, fixtures, or screenshots.
