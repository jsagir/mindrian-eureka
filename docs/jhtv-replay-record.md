---
outcome: provenance_gap
room_mark: pending_approval
label: candidate, not verified
checked_on: 2026-11-07
---

# JHTV replay record: OPP-027 to OPP-031

## What this page is for

This page is the one record of the outcome of the graph-derive replay behind five JHTV opportunities, OPP-027 to OPP-031. Phase 4 and the plugin team read the front matter above. The outcome is a provenance gap. Every result here is candidate, not verified.

Each claim is marked PROVEN (seen in a file or a run in this check), INFERRED (reasoned from PROVEN facts) or UNVERIFIED (not run). The check date is 2026-11-07. The machine twin of this page is `evaluations/graph-derive-replay/record.v1.json`. Check numbers C1 to C9 below name the checks in that file.

## What the room says

The five candidates in the partner room cite one replay. The cited text says: a graph-derive replay over the room's stored vectors (model MongoDB/mdbr-leaf-ir, 2,130 claims, 2,267,385 pairs, CONVERGES floor 0.55), dated 2026-10-21, then a title scan of the full catalog. A second citation names the results file `derive_results.json`, dated 2026-10-21. The same text says the run was read only and that similarity is a screening signal, not a verified relationship.

The partner room is the source of these figures. No title and no room text is copied into this repo.

## What this repo holds

The repo holds nothing for this replay. It has no replay script, no claim table, no vector table and no `derive_results.json` (C1, PROVEN). A search of the repo found the figures only in planning files and in the files of this plan.

The nearest items are the JHTV pair results of 2026-10-18 and their reproduction record, `docs/hsi-rs-jhtv-reproduction.md`. That record covers a different run, with a different pair count.

## What exists outside this repo

- The partner room store holds 2,130 stored vectors of 384 dimensions today (C3, PROVEN). Only a row count was read. No vector value and no text was read. The store file is dated 2026-10-29, which is 8 days after the cited replay.
- No file named `derive_results.json` was found in the repo, the partner room, the dev folder with the plugin checkouts, the rooms folders, or the work, output, research and tmp folders (C4, PROVEN for those folders). A copy on a cloud drive or on another machine is not excluded (C5, UNVERIFIED).
- The model `mdbr-leaf-ir` is not on this machine (PROVEN). The stored vectors cannot be re-made here.
- The plugin derive code calls a pair CONVERGES at a cosine of 0.55 or more and counts all pairs as n times n minus 1, divided by 2 (C6, PROVEN, read in MindrianOS-Plugin at commit cd6879a98). The plugin changed its pair selection on 2026-10-21 to keep only the top-k pairs (C7, PROVEN, commit e2e819d43).
- That the replay was a run of this plugin code is INFERRED (C8). The figures match the code. No run record was found, and the code state of the run is not recorded.
- That the stored vectors are the same set as the replay used is INFERRED. The count of 2,130 matches. The dates differ by 8 days.

## The pair count check

The figure 2,267,385 equals 2,130 times 2,129 divided by 2 (C2, PROVEN). On the stored vectors, 2,165 pairs reach a cosine of 0.55 or more (PROVEN as a count in the read-only feasibility check of 2026-11-07; the count was not repeated in this plan).

This does not prove that a run happened. The figure is the count of all pairs of 2,130 items, so it follows from the claim count alone. It shows that the cited numbers agree with each other and with the stored vector count. The same identity holds for the wording-and-meaning pair count in `docs/hsi-rs-jhtv-reproduction.md`: 2,239,786 equals 2,117 times 2,116 divided by 2.

## Verdict

Verdict: provenance gap. The five items are OPP-027, OPP-028, OPP-029, OPP-030 and OPP-031. There are three reasons.

1. The output file the candidates cite, `derive_results.json`, was not found (C4, PROVEN for the folders searched).
2. No script and no run record was kept (C1, PROVEN; C8, INFERRED).
3. The title scan of the full catalog is not a script (C9). A perfect replay of the pair scoring would still not reproduce the five candidates.

The five candidates stay leads. The similarity behind them is a screening signal. All results are candidate, not verified.

## Why no replay script is built here

- The data is not in this repository, so a script here would run on nothing and would prove nothing.
- The vectors sit in a room that the host owns. Eureka does not read rooms.
- A rebuild needs a host-approved read-only export and a decision by the owner.
- The plugin changed its pair selection on the day of the replay. Even with the data, the result might differ.

## What would close the gap

The gap closes when one of these holds.

1. The host exports the claim ids and the stored vectors under an approved read-only export, and a recorded replay with the cited floor runs twice with equal output hashes.
2. The cited output file `derive_results.json` is found, and its sha256 is recorded in the machine record.

A partial replay on the stored vectors needs a host-approved read-only vector export. That work is deferred to Phase 3.1. The outcome stays `provenance_gap` until then.

A host export would need to hold the claim ids, the stored vectors, the model name, the floor and the code commit used. This list is a request for a later plan. It is not work of this phase.

## The room mark is a hand-off item

The mark "provenance gap" on the five opportunities is a write into the partner room. That write belongs to the host and needs the approval of the navigator. Eureka writes nothing to a room.

The script named below gives the host the exact list to mark. The front matter value `room_mark: pending_approval` means that no mark was written. Only a later Eureka quick task may change it to `done`, after the host session reports an approved write. An executor never sets it.

The hand-off contract `docs/mos-eureka-engine-run-contract.md` carries the same item for the plugin team. That file is written by plan 03-07 of this phase.

## How to emit the list

```bash
scripts/emit-provenance-gap-list
scripts/emit-provenance-gap-list --format text
scripts/emit-provenance-gap-list --check
```

The first command prints the list as JSON. The second prints plain text. The third compares the JSON with the golden file `evaluations/graph-derive-replay/gap-list.v1.json`. The output is byte-stable and the script prints its sha256 on stderr. The script is offline. It reads only the machine record and writes only to stdout and stderr.

Exit codes:

- 0: success, or the list equals the golden file.
- 1: the pair count check failed, or the list differs from the golden file.
- 2: bad input, such as a missing file, a file that is not JSON, or a file that fails the schema.

## Front matter keys

| Key | Value | Meaning |
| --- | --- | --- |
| `outcome` | `provenance_gap` or `replayed` | The result of the replay work. This page holds `provenance_gap`. |
| `room_mark` | `done` or `pending_approval` | Present only with `provenance_gap`. This page holds `pending_approval`. |
| `claims`, `pairs`, `two_run_hashes_equal` | number, number, true or false | Present only with `replayed`. Absent here. |
| `label` | `candidate, not verified` | The label of every result on this page. |
| `checked_on` | a date | The date of the checks. |
