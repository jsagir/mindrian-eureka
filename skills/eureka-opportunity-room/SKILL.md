---
name: eureka-opportunity-room
description: Turn a technology list (CSV export) or a folder of documents into a working MindrianOS opportunity room in one step - runs Eureka on it, builds the result hub with its 3D map, opens one room for the job, files the strongest candidate pairs as evidence and opportunity-bank entries, works the room with Larry and hands over the first move. Use when the user says "find opportunities in my list", "run Eureka on this export", "open a room on this job", or gives a CSV of technologies and asks MindrianOS to do the work.
argument-hint: "<path to the CSV export or the folder> [room name]"
---

# Eureka opportunity room (one step)

The user invoking this skill with a path is their approval for the offline steps (1 to 4). The
room step (5 onward) sends room content to the model provider when Larry works it, so it waits
for the ONE card in Step 5. Do not ask anything else. Say in one line what will happen, then go.

One line to say first:
"I'll run Eureka on your list on this machine, build the result page with its 3D map, then ask
you once before I open a MindrianOS room and work the best leads in it."

Every result stays a candidate, not verified. Never call a pair an opportunity without that label.

## Paths

- `INPUT` = the path the user gave. If it is a CSV file, use its parent folder as the input
  folder only when the CSV is the only file there; otherwise copy the CSV into
  `~/eureka-jobs/<job>/input/` and use that folder. Never write into the user's own folder.
- `JOB` = `~/eureka-jobs/<job>` where `<job>` is a short slug from the room name or the file name.
- `ENGINE` = `~/.mindrian/eureka-engine` (or `$MINDRIAN_EUREKA_ROOT`).
- Run every `eureka` command as `uv run --project "$ENGINE" --no-sync eureka ...`.

## Step 1 - Engine ready

Run `uv run --project "$ENGINE" --no-sync --offline eureka doctor`. If the folder is missing or
the doctor shows a FAIL, run the setup skill first (`/mindrian-eureka:mindrian-eureka-setup`),
then continue. Long timeouts: up to 10 minutes per step.

## Step 2 - Pick the mapping

Read the CSV header.
- It has `case_number`, `title` and `abstract` (a technology-transfer export such as JHTV):
  use `$ENGINE/examples/mappings/technology-audit-export.json`. Run once with `--dry-run`. If the
  dry run names columns that are missing, copy the mapping to `$JOB/mapping.json`, remove only
  the missing names from it, and use the copy. Tell the user which columns were dropped.
- Any other CSV: copy that mapping to `$JOB/mapping.json` and set `id_column`, `title_column`
  and `text_columns` to the CSV's own id, title and description columns; empty the outcome and
  carried lists that do not exist. Keep its `room_sections` block (needed for seeding).
- A folder of documents (no CSV): run without `--mapping`; Step 4 then skips seeding and the
  room gets the top pairs from `ranked-pairs.md` instead.

If a side-car file of extra text (`case_number,text`) sits next to the CSV, add
`--text-sidecar <file>` and report the coverage line the run prints.

## Step 3 - Run and build the hub (offline)

```bash
uv run --project "$ENGINE" --no-sync eureka run "$INPUT_FOLDER" --out "$JOB/run" --mapping "$MAPPING"
uv run --project "$ENGINE" --no-sync eureka hub "$JOB/run" --out "$JOB/hub"
```

Open `$JOB/hub/hub.html` in the default browser (`open` on macOS, `start` on Windows,
`xdg-open` on Linux). Tell the user the hub has the ranked pairs, a filter by class
(open next to licensed, both open, both licensed) and the Graph view with the 3D map of how the
technologies connect. Report the class count lines the run printed.

## Step 4 - Choose the leads (offline)

```bash
uv run --project "$ENGINE" --no-sync eureka seed "$JOB/run" --list --json
```

Pick up to 5 `cross` pairs, then up to 2 `open_open` pairs, in the order listed, plus the first
spine (if any). For each pick write a seed:

```bash
uv run --project "$ENGINE" --no-sync eureka seed "$JOB/run" --pair <pair_id> --out "$JOB/seeds/<pair_id>"
uv run --project "$ENGINE" --no-sync eureka seed "$JOB/run" --cluster <record_id> --out "$JOB/seeds/cluster"
```

## Step 5 - The one card: open the room

Fire ONE AskUserQuestion card (the room birth gate). Name the room, the number of leads, and
state the boundary in plain words: "Working these leads with Larry sends their text to the model
provider (Anthropic). The run and the hub stayed on this machine." Options:
- Open the room and work the leads (Recommended)
- Open the room, file only, no Larry work yet
- Stop here - keep the hub only

On "Stop here", end with the hub path. Nothing else is written.

## Step 6 - Birth and fill the room

1. Create the room through the MindrianOS chokepoint: invoke the `mos:rooms` skill with
   `new <room-slug>` (never build room folders by hand). Bind it (`room_bind`) and confirm.
2. For every seed folder: verify each `evidence_sha256` in `seed.json` against its file; stop on
   a mismatch. File each evidence file byte for byte into the section its records belong to
   (`problem-definition` by default) with `artifact_file`.
3. File each `bank_entries[].statement.text` into `opportunity-bank`, one artifact per entry,
   with `review_status: proposed`, `critic: pending`, `banked: false`, the pair class and the
   label "candidate, not verified".
4. File one provenance artifact in `references`: the run `manifest.json` sha256, each
   `seed.json` sha256, `seed_writer` and `engine_versions`, and the hub path.
5. For the first section in `suggested_sections`, write its BRIEF so the first move is the first
   `feed_next` entry, in plain words.

## Step 7 - Work the room (only on "Open the room and work the leads")

Run, in this order, inside the room:
1. `/mos:eureka` on the filed leads (room perspectives on the candidate pairs).
2. `/mos:find-connections` across the filed evidence.
3. `suggest_next` for the first move.

Do not grade, bank or confirm anything. Every bank entry stays `proposed` until the user decides.

## Step 8 - Hand over

Report in 5 to 8 plain lines:
- the hub path (and that the 3D map is in its Graph view),
- the run counts (records, pairs, class counts) and any dropped columns,
- the room name and what was filed (evidence files, bank entries),
- the top 3 leads in one line each, labelled candidate, not verified,
- one next move from `suggest_next`.

To rerun on a new export: run this skill again with the new file; it writes a new `$JOB/run`.

## Rules

- Claim only what ran. Quote the run and seed summary lines; never invent counts.
- The people and money columns never enter the room; only what the seed files carry.
- Offline until the Step 5 card says yes. No web search, no Brain call with room text.
- On any failure, show the tool's own error and its printed Fix line, then stop.
