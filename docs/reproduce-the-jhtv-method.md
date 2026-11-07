# Reproduce the JHTV method

This guide takes you from a fresh install to a ranked list of pairs on public data. It also says what you can and cannot reproduce from the JHTV run.

## Status of this guide

Status: internal only.

The release record [docs/rs-release-gate.md](rs-release-gate.md) has the decision no-go and the status draft for public distribution of the unusual-pairs engine. The gaps in its `reopen_when` list are G1, G2, G3 and G5. They are still open. They ask who wrote the original code, whether a paper exists, what terms came with the hand-over, and whether written permission to adapt or redistribute exists.

The public example uses public data, but it runs that engine. So the example and this guide are not for publication.

Sharing inside the project and with the approved partner follows section 9 of the record.

Do not publish this guide or the example.

This status follows the record. When the owner changes the record, this text changes.

## What this guide is for

This guide is for a reader who is not the author. You may know nothing about Eureka or the JHTV run.

You will do three things. You will run the method on public data. You will check the result by hash. You will learn what is reproducible and what is not.

Every result in this guide is a candidate, not verified. It is a lead for human review.

## What you need

- Python 3.11 or newer.
- `uv`, the Python package tool.
- A checkout of this repository.
- The local meaning model `all-MiniLM-L6-v2`, already on disk.
- No network after setup. Eureka downloads nothing when it runs.

[Offline install](offline-install.md) says how to place the model.

## Step 1. Install

Run this from the repository root.

```sh
uv sync --extra modern-encoder
```

It installs Eureka and the support for the local meaning model. A good result is a command that ends without an error.

## Step 2. Check the machine

```sh
uv run eureka doctor
```

The doctor checks Python, `uv`, the meaning model, the cache folder and the data folder. For each problem it prints the exact fix. Fix every problem before you go on.

## Step 3. Run the public example

The example is 36 title-and-abstract files from arXiv. The data is CC0 and the license record is [SOURCE.md](../tests/fixtures/hub_public/SOURCE.md).

```sh
uv run eureka run tests/fixtures/hub_public/input --out my-run --threads 1
```

The run reads 36 records and drops none. The unusual-pairs engine writes 63 pairs. The wording-and-meaning engine writes 200 pairs. A run took 10 to 22 seconds on the test machine (12 cores, no GPU) and peaked near 0.82 GB of memory.

The run writes `unusual-pairs.json`, `wording-and-meaning-pairs.json`, `ranked-pairs.md`, `corpus/records.jsonl`, `manifest.json` and `run-info.json` into `my-run`. It never writes into the input folder.

## Step 4. Check the hashes

A hash is a short fingerprint of a file. If one byte changes, the fingerprint changes.

```sh
uv run eureka check-example my-run
```

The command compares your run with the expected hashes in `examples/public-example/expected-hashes.json`. It prints 7 lines, one for each check.

- X1 run_folder: the folder holds `manifest.json` and the 4 output files.
- X2 inputs: the input files and the corpus agree with the expected hashes.
- X3 settings: the settings and the seeds agree.
- X4 model: the meaning model and its file hashes agree.
- X5 engine: the Eureka version and the engine record agree.
- X6 outputs: the 4 output files have the expected sha256.
- X7 label: the result files hold the label "candidate, not verified".

A good run ends with this line:

```
Result: MATCH. This run is identical to the shipped expected hashes.
```

A run that differs ends with this line:

```
Result: NO MATCH. This run differs from the shipped expected hashes.
```

The rule is exact equality. Lines that start with INFO show your platform and library versions. They explain a difference. They never excuse it.

## Step 5. Read the ranked pairs

Open `my-run/ranked-pairs.md`. It has two tables, one for each engine. Each table has these columns: Rank, Left record, Right record, Wording, Meaning, Rank score and Reading.

Here is the first row of the unusual-pairs table, shortened.

| Rank | Left record | Right record | Wording | Meaning | Rank score | Reading |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | The Difficulties of Learning Logic Programs with Cut | Decidable Reasoning in Terminological Knowledge Representation Systems | 0.0391 | 1.0133 | 3.7248 | Similar meaning, different wording. |

Read it from left to right. The two records have almost no wording in common (0.0391). Their ideas are close (1.0133). The two scores disagree a lot, so the pair ranks first.

The wording score shows how alike two records are in vocabulary and word overlap. The meaning score shows how close their ideas are. Both scores sit on a common scale. The rank follows how far the two scores disagree.

The score is a screening signal. It does not show novelty, evidence, demand or value.

The next step is human. Read both records. Decide whether the pair deserves follow-up. Every pair is a candidate, not verified.

## Step 6. Open the hub (optional)

```sh
uv run eureka hub my-run --out my-hub
```

Open `my-hub/hub.html` in a current browser. The page shows the ranked pairs, a connection graph and the list of records. It runs from local files and sends nothing over the internet. It needs no meaning model.

## Step 7. Run the method on your own folder

Put Markdown files, or CSV files with a mapping, in a folder. Then run Eureka on it.

```sh
uv run eureka run ./my-sources --out ./eureka-run
```

The run reads your folder and never writes into it. A CSV file needs to know which column holds the text. The [partner run guide](partner-run-guide.md) shows the mapping file.

To prove that a repeat run gives the same files, run twice into two folders and compare them.

```sh
uv run eureka run ./my-sources --out ./eureka-run
uv run eureka run ./my-sources --out ./eureka-run-2
diff -r --exclude=run-info.json eureka-run eureka-run-2
```

The `diff` command prints nothing when the two runs are identical. The file `run-info.json` holds times, so the command leaves it out. On the public example this check printed nothing on 2026-11-07.

Every result of your run is a candidate, not verified.

## How this maps to the JHTV run

The JHTV run was done in a partner room from 2026-10-18 to 2026-10-21 on a catalog of 2,117 technology records. A review on 2026-10-23 found it only partly reproducible. The exact JHTV commands are in the [reproduction record](hsi-rs-jhtv-reproduction.md).

| JHTV step | What it was | What Eureka does now | Can you reproduce it |
| --- | --- | --- | --- |
| Clean collection with stable IDs | A catalog of 2,117 technology records, each with an id | `eureka run` reads a folder of Markdown and CSV files and writes `corpus/records.jsonl`, one line for each record | Not the JHTV collection, which is private. The public example is a stand-in. |
| Unusual-pairs engine, top 200 | The engine "Find Unusual Pairs Across a Research Collection", run with a reference script on all 2,117 records | `eureka run` writes `unusual-pairs.json` with a reimplementation of the method | The method is reproducible on your own folder. The exact JHTV list is not claimed (see the section "What is not reproducible"). |
| Wording-and-meaning pairs engine, top 200 | The engine "Rank Unusual Pairs by Wording and Meaning", run with a reference script on the same records | `eureka run` writes `wording-and-meaning-pairs.json` | The method is reproducible on your own folder. The exact JHTV list is not claimed (see the section "What is not reproducible"). |
| Five graph services | Five graph services run on the partner room between 2026-10-18 and 2026-10-21. Request files were saved on 2026-10-19. | Not part of `eureka run` | Not covered by this guide |
| Graph-derive replay | A replay of 2026-10-21 over stored vectors, cited as 2,130 claims and 2,267,385 pairs | Not part of the public example | See the next section |
| Human review of the leads | The pair lists were framed as diligence leads in an assessment of 2026-10-18 | `ranked-pairs.md` and the hub page help a person read the pairs. Eureka does not judge them. | Yes, this step is the reading in Step 5. Every pair is a candidate, not verified. |

## What is reproducible

- The same input, settings, model and engine give the same four output files, byte for byte. Check it with Step 4 on the example and with the repeat run of Step 7 on your own folder.
- Every setting and seed of the run is written in `manifest.json`. You can read what a run used and run it again.
- The maintainer reproduced both JHTV result files on a private copy of the collection (record `ENG-03`, checked on 2026-10-23). The wording-and-meaning result matched: 200 pairs equal, 2239786 pairs scored, maximum score difference 0.0. The unusual-pairs result matched with a cap of 2117 or more: 200 pairs equal, maximum difference 0.0. A first run with the default cap of 2000 did not match. Both runs used the older reference scripts, not this package. You cannot repeat this without the private collection.
- On the public example, 4 checked setups on one machine gave the same 4 output files: 1 thread and 12 threads, an empty cache and the default cache, and the project environment and the system Python with older libraries. The [example README](../examples/public-example/README.md) has the table.

## The graph-derive replay

The JHTV work also cited one graph-derive replay. This block states what the project records about it, and nothing more.

<!-- replay-outcome:begin -->
Replay outcome: not recorded yet. Phase 3 has not produced its result, so this guide makes no claim about the replay. This is not a verified statement.
<!-- replay-outcome:end -->

## What is not reproducible

- The JHTV collection is private. A run on public data is not the JHTV result. Source: [reproduction record](hsi-rs-jhtv-reproduction.md), section 6.
- The unusual-pairs engine is a reimplementation of a method from research code. It is not verified bit-for-bit against that code. The repo path and the reference script build the meaning input by different rules. On the committed test fixtures the repo path shares 74 percent of the pairs with the reference script (rank correlation 0.62). On a 40-file JHTV sample the share is 42 percent. So the repo path does not reproduce the JHTV ranking at the meaning-signal level. Source: the section "Fidelity of the unusual-pairs engine" in the repository README.
- The wording-and-meaning engine changed on 2026-10-29. The vocabulary cap now keeps rare shared identifiers, and the two word-based signals are fused by equal spread. The JHTV result of 2026-10-18 came from the older reference script without these changes. No comparison on data of JHTV size was run. So today's `eureka run` is not claimed to give the JHTV lists. This is UNVERIFIED. Source: quick tasks 261029-184 and 261029-bfm.
- The model differs for the replay. The JHTV pair lists of 2026-10-18 used the meaning model `all-MiniLM-L6-v2`, as the example does. The graph-derive replay used a different model, `mdbr-leaf-ir`. That model is not on the disk of the test machine, and the example does not use it. Source: the [reproduction record](hsi-rs-jhtv-reproduction.md), sections 2 and 3, and `examples/public-example/expected-hashes.json`, key `example`.
- The five graph services of the JHTV run are not covered. Request files were saved on 2026-10-19. The exact command syntax is unconfirmed (UNVERIFIED). This guide does not cover the graph services. Source: `.planning/PROJECT.md`.
- Hash equality is shown only in the checked setups of the example README, all on one platform (linux-aarch64). On another platform, another operating system or another library version the bytes can differ. That case is UNVERIFIED. The check then prints INFO lines that show the difference. Source: the [example README](../examples/public-example/README.md).
- A score is a screening signal. It does not show novelty, evidence, demand or value. A high rank is a reason to read two records together. It is not a finding. Every result is a candidate, not verified.

## If your hashes do not match

The rule is exact equality. INFO lines explain a difference but never excuse it. A line X1 or X7 that fails means the folder is not a finished run, or a result file lost its label. Give the folder that `eureka run` wrote and do not edit it.

| Check line | Likely cause | Action |
| --- | --- | --- |
| X2 inputs | An input file changed, or you ran on another folder. | Run Eureka on the unchanged example input folder `tests/fixtures/hub_public/input`. |
| X3 settings | A flag or a setting differs, for example another `--top-k`. | Run with the default settings and the command in Step 3. |
| X4 model | Another meaning model, or another snapshot of the model. | Use `all-MiniLM-L6-v2` at snapshot `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. The output cannot match with another model. |
| X5 engine | Another Eureka version, or an edited engine file. | Use Eureka version 0.1.0 with the same engine files. |
| X6 outputs | The input, settings, model and engine match but the bytes differ. The usual cause is another platform or another library version. A result file edited after the run also fails here. | Read the INFO lines. Do not edit the run folder. Report the mismatch. |

To report a mismatch, send the INFO lines of `check-example` and the `environment` block of your `manifest.json`.

## Words you will meet

- **Record**: one document from your folder, such as one abstract or one CSV row.
- **Pair**: two records that Eureka compares.
- **Wording score**: how alike two records are in vocabulary and word overlap.
- **Meaning score**: how close the ideas of two records are, as a local meaning model reads them.
- **Rank**: the place of a pair in the list. The rank follows how far the wording score and the meaning score disagree.
- **Run folder**: the folder that `eureka run` writes. It holds the result files and the manifest.
- **Manifest**: the file `manifest.json`. It records the input hashes, the settings, the seeds, the model and the engine of a run.
- **Hash**: a fingerprint of a file. Equal files have equal hashes.
- **Model**: the program that turns text into numbers that stand for meaning. Here it is `all-MiniLM-L6-v2`.
- **Candidate, not verified**: the label on every result. A pair with this label is a lead for a person to read. It is not evidence.
