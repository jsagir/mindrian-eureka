# Public example: 36 arXiv abstracts

A small run of Eureka on public data, with the files you need to check that your run gives the same result. Every pair in the result is a candidate, not verified.

## Status

Internal only. Do not publish this example or link it from a public page.

The release record [docs/rs-release-gate.md](../../docs/rs-release-gate.md) has the decision no-go and the status draft for public distribution of the unusual-pairs engine. The gaps named in its `reopen_when` list are still open. The data is public (CC0), but the example runs that engine, so the example is not for publication. Sharing inside the project and with the approved partner follows section 9 of the record.

This status follows the record. When the owner changes the record, this text changes.

## What the data is

The input is 36 title-and-abstract files from arXiv, 6 files in each of 6 subject groups: computer science, biology, physics, mathematics, economics and statistics. The files are in `tests/fixtures/hub_public/input`.

The license is CC0 1.0 for arXiv metadata. The quoted statement, the URL and the retrieval date are in [tests/fixtures/hub_public/SOURCE.md](../../tests/fixtures/hub_public/SOURCE.md). The files hold no authors and no full papers. The papers' claims are not endorsed here.

## Run it

Run these 4 commands from the repository root, in this order.

```sh
uv sync --extra modern-encoder
uv run eureka doctor
uv run eureka run tests/fixtures/hub_public/input --out my-run --threads 1
uv run eureka check-example my-run
```

The meaning model must already be on disk. Nothing is downloaded. See [docs/offline-install.md](../../docs/offline-install.md).

The example uses the meaning model `all-MiniLM-L6-v2`. The earlier JHTV replay used the model `mdbr-leaf-ir`, which this example does not use. The model note in the `example` key of `expected-hashes.json` records both names. The `model` and `settings` keys name the model of this example.

## What you should see

The run reads 36 records and drops none. No cap is hit. The unusual-pairs engine writes 63 pairs. The wording-and-meaning engine writes 200 pairs. On the test machine (12 cores, no GPU, 17 GB of memory) a run takes about 15 seconds and peaks near 0.82 GB of memory.

The check prints one PASS line for each of 7 checks. The last lines are:

```
Result: MATCH. This run is identical to the shipped expected hashes.
All results are candidates, not verified. They are leads for human review.
```

Every pair is a candidate, not verified. The pairs are leads for human review. They are not evidence and not a claim of novelty. The label `candidate, not verified` stays on every result file.

## Where it was checked

| Setup | Platform | Python | Threads | Cache | Same as reference |
|---|---|---|---|---|---|
| A1: reference run, project environment | linux-aarch64 | 3.12.12 | 1 | empty | yes (this is the reference) |
| A2: repeat of A1 | linux-aarch64 | 3.12.12 | 1 | default | yes |
| B: all 12 threads | linux-aarch64 | 3.12.12 | 12 | default | yes |
| C: system Python, older numpy 2.2.6, torch 2.11.0, sentence-transformers 5.3.0 | linux-aarch64 | 3.12.3 | 1 | default | yes |

The hashes are exact. Another platform or another library version can give other bytes. The check then prints INFO lines that show the difference. No match is claimed for a setup that is not in the table.

## Files in this folder

- `expected-hashes.json` holds the expected values. The `inputs` keys hold the sha256 of each input file. The `settings`, `seeds` and `model` keys hold the run settings and the sha256 of each model file. The `engine` and `engine_sources` keys hold the engine identity and the sha256 of the engine source files. The `outputs` key holds the sha256 of the 4 output files. The `reference_environment` key holds the platform and library versions of the reference run.
- `reference-run/` holds the 4 expected output files and the manifest of the reference run. A reader can run `diff -r` between a run and this folder to see the difference. The file `run-info.json` is not copied, because it holds times and local paths.

## Notes for the maintainer

Rebuild the expected file with `scripts/make-example-hashes`. Do it when the drift-guard test `test_engine_identity_is_current` fails, which means an engine file changed. Give absolute paths for the run folder and for `--out`. Run the real-model test first, replace the reference run if the outputs changed, and record why in the commit message.

The older frozen run in `tests/fixtures/hub_public/run` is for the hub tests. It is not the reference of this example. It was made on 2026-10-24, before the quick tasks 261029-184 (vocabulary cap, wording params hash 7affae3c94c6bed9 in the frozen run) and 261029-bfm (equal-spread lexical fusion, wording params hash bea4c100c2013300 now). A run today gives other bytes than that frozen run.

The opt-in real-model test:

```sh
EUREKA_EXAMPLE_REAL_RUN=1 uv run --offline --with pytest python -m pytest tests/test_public_example_fresh.py -q -p no:cacheprovider
```

Never edit or regenerate a file under `tests/fixtures`.
