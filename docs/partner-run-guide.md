# Partner run guide

## What this page is for

This page takes a partner such as JHTV from a folder of carried-in files to a hub page on one offline machine. It covers the export CSV, the mapping file, the optional text side-car, the run, the hub and the MindrianOS hookup. The data never leaves the machine. Every result of Eureka is a candidate, not verified.

## Assumptions

These points are ASSUMED. They are not confirmed on the partner machine.

- ASSUMED: the machine may run Linux, macOS or Windows.
- ASSUMED: the machine has no route to the internet or to the Python package index.
- ASSUMED: the machine can receive files by an approved transfer.
- ASSUMED: the export is one CSV file with one row per technology and a `case_number` column.

The carry-in list and the install steps are in [offline install](offline-install.md). This page does not repeat them.

## 1. What to carry in

1. The `uv` program from a trusted release.
2. The Python wheels, or a uv cache, for `uv sync --extra modern-encoder --extra hub-gate --offline`.
3. The `all-MiniLM-L6-v2` model folder.
4. The Eureka source folder at the agreed commit.
5. The export CSV in its own input folder, with nothing else in that folder.
6. The mapping file `examples/mappings/technology-audit-export.json`. It ships inside the source folder.
7. The side-car file, if one exists. Keep it outside the input folder. See section 3.

Follow the steps of [offline install](offline-install.md) to put `uv`, the libraries and the model in place.

## 2. Check the machine

Run `uv run eureka doctor` from the Eureka source folder.

A PASS on every line means a run can work. A FAIL line prints the exact fix under it. The doctor prints fix commands and never runs them. A missing model is always a FAIL, with every searched place listed. Add `--load-model` to load the model and encode one sentence as a last check.

## 3. The mapping file and the side-car file

The mapping file tells the run which CSV columns hold the record id, the title and the text. For this export the text is the abstract, the 7 inventor answers and the topics, each answer under its question as a label. People columns, money columns and outcome columns never enter the text.

The outcome rule in the mapping marks a record `licensed` when any of these 6 triggers holds: `licensed_to_jh_startup` is Y, `licensed_externally` is Y, `licenses` is above 0, `options` is above 0, `had_corporate_research` is Y, or `status` is `Inactive- Licensed`; every other record is `open`. The carried columns are the outcome flags, counts and dates plus `status`; the run copies these cells next to every pair as they are, without parsing.

The side-car file fills records whose own text is thin. It is a CSV whose first column is the record id and whose `text` column holds the text, or a JSON object of id to text. The example is `examples/mappings/text-sidecar.example.csv`. The run adds side-car text to a record only when the own text of that record is under 50 characters, and it adds the text after the own text. It never replaces own text. A record filled this way is marked `text_source: sidecar` in the corpus file.

## 4. Run

Run this command from the Eureka source folder. Replace the 3 placeholders.

```sh
uv run eureka run <folder> --out <run-folder> --mapping examples/mappings/technology-audit-export.json --text-sidecar <side-car file>
```

Leave out `--text-sidecar <side-car file>` when no side-car exists. The run reads the input folder and never writes into it. It writes these files into the run folder: `unusual-pairs.json`, `wording-and-meaning-pairs.json`, `ranked-pairs.md`, `corpus/records.jsonl`, `manifest.json` and `run-info.json`. The manifest records the sha256 of every input file, of the mapping and of the side-car, so a second run on the same files can be checked against the first. Add `--dry-run` first to read and check the input without a model load.

## 5. Open the hub

Run this command on the finished run folder. Replace the 2 placeholders.

```sh
uv run eureka hub <run-folder> --out <hub-folder>
```

Then open `hub.html` in the hub folder with a current browser. The page loads local files only and sends nothing over the internet. Add `--source-dir <folder>` to link each record to its source file. Add `--password-env <NAME>` to store the page data encrypted with the passphrase held in that environment variable; this needs the `hub-gate` extra from section 1.

## 6. Read the result

The run prints one coverage line when a side-car was given:

`Text coverage: <records total> records, <with own text> with own text, <filled from the side-car> filled from the side-car, <still thin> still thin and dropped`

The first number is every record in the export. The second number is the records whose own text was long enough. The third number is the records the side-car filled. The fourth number is the records that stayed thin and were dropped; their ids are in the manifest. The same 4 numbers are in the manifest under `corpus.text_coverage`.

The run writes 2 pair lists. `unusual-pairs.json` holds the pairs of the engine Find Unusual Pairs Across a Research Collection. `wording-and-meaning-pairs.json` holds the pairs of the engine Rank Unusual Pairs by Wording and Meaning. Each pair is a candidate, not verified. The run prints one class count line for each engine:

`<engine name> classes: cross <N>, open_open <N>, licensed_licensed <N>`

A `cross` pair puts an open technology next to one that got out, and it is a candidate, not verified. An `open_open` pair puts 2 open technologies together as a bundle candidate, not verified. A `licensed_licensed` pair puts 2 technologies that both got out together, as a candidate, not verified.

In the hub, every pair shows its class and its carried outcome cells as small label chips. The filter "Show pairs of class" offers "All classes", "Open next to licensed", "Both open" and "Both licensed". A pair does not mean that anything is new, wanted or valuable. It is a lead for human review.

## 7. MindrianOS on the same machine

MindrianOS finds the engine through the variable `MINDRIAN_EUREKA_ROOT` in the host settings. Set `MINDRIAN_EUREKA_ROOT=<folder>` where `<folder>` is the Eureka source folder of section 1. This was measured on the owner's machine on 2026-10-29: the value there is the engine checkout folder. The host starts the engine from that folder with `uv`, so `uv` must be on the `PATH` of the host process. The contract is in [the MindrianOS host integration](integrations/mindrianos.md).

## 8. Start a room from one pair

A finished run can give you a seed: a folder that MindrianOS can open as a room. Eureka only writes the folder. It writes no room, calls no model and makes no network call. Every result in it is a candidate, not verified.

List the places to start. The list shows counts and classes. It does not say what is worth more.

```sh
uv run eureka seed <run-folder> --list
```

Pick one pair or one record, then run one of these 2 commands. Replace the placeholder.

```sh
uv run eureka seed <run-folder> --pair <pair-id>
uv run eureka seed <run-folder> --cluster <record-id>
```

The hub shows the pair command under each pair. The folder is saved next to where you ran the command, under a name that starts with `eureka-seed`. Add `--out <folder>` to choose another place.

The folder holds a statement draft for each pair, one evidence file for each record with its hash, what is known and what to feed next, sorted by room section. The `room_sections` block of the mapping file decides the sections. Its `not_in_export` list names what the export lacks: patents, royalties and license income, and the true disclosure date. Each item names the system that holds it.

The people columns and the money columns never leave the CSV. The seed shows only that they are filled.

Working the room with Larry sends room content to the model provider. You decide whether to do that and when. The rules for MindrianOS are in the [room seed contract](room-seed-contract.md), file `docs/room-seed-contract.md`.

## How the bundle is built

The owner builds one carry-in folder per operating system with `scripts/build-partner-bundle --target <linux-x86_64 | windows-x86_64 | macos-arm64> --out dist --online`. The model folder comes from a local path given with `--model-path`, and the builder never downloads it unless `--allow-model-download` is passed. The folder `eureka-partner-bundle-<target>` holds the `uv` program for that system, the Eureka source at the agreed commit, the locked requirement list with hashes, the wheel folder, the model folder, the mapping file, a `sidecar/` folder with a README and the format example, this guide, and the launchers `start.sh` and `start.ps1`. The file `BUNDLE-MANIFEST.json` lists every file of the folder with its sha256 and byte size, so the receiving side can check each file before anything runs. The side-car file for this export, if one exists, is dropped into `sidecar/` before hand-over. On the partner machine the whole run is `start.sh` on Linux or macOS and `start.ps1` on Windows, with an input folder and an output folder that default to `input` and `output` next to the bundle. Add `--dry-run` (or `-DryRun`) to see the steps without running them. The first step of the launcher, before the 4 steps of section 2 to section 5, is a `uv sync` of the bundled source from the `wheels/` folder, offline, so the first run needs no network and no install on the machine; on the partner machine this sync is ASSUMED until the first real run. The launcher stops when `eureka doctor` finds a problem and leaves the printed fix on the screen. Re-running on a new export is the same click. Nothing in the bundle or the launcher calls the network. Every result stays a candidate, not verified.

Build status of the three targets, run on 2026-11-07 on a Linux builder with `--online`:

- PROVEN on 2026-11-07: the wheel download with hashes and the bundle manifest build finishes for `linux-x86_64` (exit 0, 459 MB, 51 wheels, 1103 files in the manifest).
- PROVEN on 2026-11-07: the wheel download with hashes and the bundle manifest build finishes for `windows-x86_64` (exit 0, 390 MB, 52 wheels, 1104 files in the manifest).
- PROVEN on 2026-11-07: the wheel download with hashes and the bundle manifest build finishes for `macos-arm64` (exit 0, 368 MB, 51 wheels, 1103 files in the manifest).

For each target, the wheel folder holds every package of the lock that applies to that system, and the manifest lists every file on disk. The builder takes the `torch` build for the CPU from the PyTorch CPU index, accepts the macOS 11 to 14 arm64 wheel tags, and reads the environment markers of the lock for the target system, not for the builder machine. The `requirements.txt` in the bundle is the unchanged output of `uv export`.

The `macos-arm64` bundle carries a `torch` wheel tagged `macosx_14_0_arm64`, so the Mac needs macOS 14 or newer. This minimum is ASSUMED until a Mac runs the bundle.

Running the launchers `start.sh` and `start.ps1` on Linux, Windows and macOS stays ASSUMED. The launchers were not run on any of the three systems, and no bundle was installed on the builder.

## Privacy

- The data never leaves the machine. The run, the doctor and the hub make no network call.
- The run writes only the run folder, the embedding cache and the job data folder. The hub writes only the hub folder.
- The people columns of the export never enter the engine and never enter the outputs.
- The carried columns are the outcome columns only. No column that names a company is carried.
- Every output keeps the wording candidate, not verified.
