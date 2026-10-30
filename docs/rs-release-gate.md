---
record: rs-source-release-gate
version: 1
decision: no-go
decision_scope: public distribution of the unusual-pairs engine (eureka-pair-scout, hybrid_2026 and legacy) and its docs
decided_by: Jonathan Sagir (owner)
decided_on: ""
status: draft
reopen_when:
  - G1
  - G2
  - G3
  - G5
evidence_checked_on: 2026-10-23
partner_internal_decision: approve
partner_internal_scope: partner-internal distribution of the engine package to JHTV, on its own machine and for its own staff, not public, not redistributable
partner_internal_decided_on: 2026-10-29
partner_internal_decided_by: Jonathan Sagir (owner)
---

# Release gate for the unusual-pairs engine source

This record answers one question: may Eureka ship the engine "Find Unusual Pairs Across a Research Collection" (id opportunity.find_cross_domain_pairs, formerly called RS) publicly. It finds pairs of documents in a collection where meaning and wording disagree. Below, this record calls it the unusual-pairs engine. It is a project status note. It is not a license grant and not legal advice.

Label key. PROVEN means the fact was read or measured by a command on 2026-10-23. UNKNOWN means no evidence was found.

## 1. Summary

The default answer is no-go. The method of the unusual-pairs engine and its numeric settings come from a research code package of 5 files that was handed to the project. That package has no license text, no copyright line and no author line. Four gaps are open: who wrote the code (G1), whether a paper exists (G2), what terms came with the hand-over (G3), and whether written permission to adapt or redistribute exists (G5). The repo docs say these must close before production distribution. The owner (Jonathan Sagir) is the only person who can change this record from draft. Until then, Phases 2 and 3 proceed, and Phase 4 ships the unusual-pairs example and guide as internal only.

## 2. Origin facts

Evidence was re-run on 2026-10-23. Every hash below equals the output of `sha256sum` run on that date. The measured line total of the 5 original files is 434 lines (`wc -l`). Older notes say about 250 and 438. The research file also says 434, so this fact is unchanged since research.

| Item | Path | sha256 | Status |
|------|------|--------|--------|
| Original file comparison.py (Downloads copy) | `/mnt/c/Users/jsagi/Downloads/similarity_code (3)/similarity_code/comparison.py` | aef650814e1407181232df7dc1e0d0c14fee9ff92e7dcd840d9e490ef8978f3d | PROVEN |
| Original file lsa.py (Downloads copy) | `/mnt/c/Users/jsagi/Downloads/similarity_code (3)/similarity_code/lsa.py` | a3672feacfd970a4e7a5eb978ba05feb1b002c2df7b9444518673fae66772048 | PROVEN |
| Original file paper_cleaning.py (Downloads copy) | `/mnt/c/Users/jsagi/Downloads/similarity_code (3)/similarity_code/paper_cleaning.py` | dbf5f402a3effe7ef366884c30c3ed6e4b80e291afb0dd96bdcb96adb203c45c | PROVEN |
| Original file paper_gathering.py (Downloads copy) | `/mnt/c/Users/jsagi/Downloads/similarity_code (3)/similarity_code/paper_gathering.py` | dd2a46fd519a31e7b086d203fecf6d40091a832bc6190531fef8edd40f5ec024 | PROVEN |
| Original file sts_bert.py (Downloads copy) | `/mnt/c/Users/jsagi/Downloads/similarity_code (3)/similarity_code/sts_bert.py` | d0edc2c3d56961387c4809887e55d7db81d4f4e04650ee4ddb2402aee946825c | PROVEN |
| Original file comparison.py (plugin repo copy) | `/home/jsagi/dev/MindrianOS-Plugin/.planning/phases/89-reverse-salient-engine/source/comparison.py` | aef650814e1407181232df7dc1e0d0c14fee9ff92e7dcd840d9e490ef8978f3d | PROVEN |
| Original file lsa.py (plugin repo copy) | `/home/jsagi/dev/MindrianOS-Plugin/.planning/phases/89-reverse-salient-engine/source/lsa.py` | a3672feacfd970a4e7a5eb978ba05feb1b002c2df7b9444518673fae66772048 | PROVEN |
| Original file paper_cleaning.py (plugin repo copy) | `/home/jsagi/dev/MindrianOS-Plugin/.planning/phases/89-reverse-salient-engine/source/paper_cleaning.py` | dbf5f402a3effe7ef366884c30c3ed6e4b80e291afb0dd96bdcb96adb203c45c | PROVEN |
| Original file paper_gathering.py (plugin repo copy) | `/home/jsagi/dev/MindrianOS-Plugin/.planning/phases/89-reverse-salient-engine/source/paper_gathering.py` | dd2a46fd519a31e7b086d203fecf6d40091a832bc6190531fef8edd40f5ec024 | PROVEN |
| Original file sts_bert.py (plugin repo copy) | `/home/jsagi/dev/MindrianOS-Plugin/.planning/phases/89-reverse-salient-engine/source/sts_bert.py` | d0edc2c3d56961387c4809887e55d7db81d4f4e04650ee4ddb2402aee946825c | PROVEN |
| LATEST script `rs-engine.py` (reference path B; the r-and-d copy in the plugin repo has the same hash) | `/mnt/c/Users/jsagi/Downloads/research/LATEST/engines/rs/shared/scripts/rs-engine.py` | 044b9ae6b807617f32dc029ff310b73653efa40e245e5bcf7750ef811c9fde45 | PROVEN |
| Shipped plugin script `rs-engine.py` (path A, legacy scoring only) | `/home/jsagi/dev/MindrianOS-Plugin/scripts/rs-engine.py` | 57c18df558d83fbffc8e9f7fda905729d0c0fbfe18a1c370b1db816efa3937f1 | PROVEN |
| PowerPoint deck "Algorithmic Generation of Solutions" | searched under `/mnt/c/Users/jsagi/Downloads` and `/home/jsagi` (depth 6), names "Algorithmic Generation of Solutions" and "Algorithmic Generation of Reverse Salient Solutions" | none | UNKNOWN (not found on disk) |
| Date the project received the code | plugin planning file `.planning/phases/89-reverse-salient-engine/PLAN.md` (line 53) | none | PROVEN as a written claim: 2026-04-12 |

The two copies of the 5 original files are byte-identical (PROVEN). The plugin repo copy sits in a gitignored planning directory, so it is not in git history. No fact in this section changed since the research file.

## 3. Author and citation facts

- Original author, name held privately. This record does not quote the name. It appears in comments of one older adapted source file, tracked as open item O1 (section 4). The name is also held in the plugin repo planning files, which are private and gitignored: `.planning/phases/89-reverse-salient-engine/PLAN.md` (line 53), `RESEARCH.md` and `ALGORITHM-SOURCE.md` in the same directory, under `/home/jsagi/dev/MindrianOS-Plugin/`. The owner holds the pointer.
- The plugin notes cite the method with "et al.". That wording names no other person (PROVEN). Who else took part is unknown (G1).
- No paper venue, DOI or URL was found in any file searched (PROVEN). Whether a paper exists is unknown (G2).
- The line counts conflict across notes: about 250, 438, and 434 measured (PROVEN).
- The dates conflict: the code is attributed to 2023, the deck file is dated 2025-04-20 in the origin note, and the code was received on 2026-04-12 (PROVEN as written claims in the plugin planning files and the origin note).
- The deck author is not listed on the slides, per the origin note. The deck file is not on disk now (UNKNOWN).
- Condition C1: the attribution wording must be settled with the original author before any public release. Phase 1 does not do this.

## 4. License facts

- Original files: no license text and no header in any of the 5 files (PROVEN). A search for license, copyright and author lines found only: string literals in `paper_cleaning.py` that strip publisher copyright notices from abstracts, and a comment in `paper_gathering.py` about a vendor author-search web service. None of these is a rights statement.
- Plugin repo: Business Source License 1.1. The licensor line reads "Licensor: Jonathan Sagir" and the licensed work is "(c) 2024-2026 Jonathan Sagir" (PROVEN, first 15 lines of `/home/jsagi/dev/MindrianOS-Plugin/LICENSE`).
- This repo: no top-level `LICENSE` file, on purpose. See [licensing and provenance](licensing-and-provenance.md).
- Open item O1: one comment in `src/mindrian_eureka/data/rs/rs-differential-scorer.cjs` (line 33) cites the original author and a year. Changing that comment changes the sha256 of the adapted file that is listed in `docs/engine-source-ledger.md`. Phase 1 does not edit that file. The owner decides later. The comment is not quoted here.

## 5. What the repo copied versus reimplemented

- The Python path of the unusual-pairs engine in `src/mindrian_eureka/opportunity_pairs/algorithm.py` reuses these numeric settings from the original `lsa.py`: 2000 features, max_df 0.5, 80 components, n_iter 10, seed 256, top 7 terms per topic (PROVEN by reading both files).
- The code text is independent. No original file is copied into this repo (PROVEN by the ledger statement and by the Phase 1 rule not to vendor). This record cites paths and sha256 values only.
- The CJS files under `src/mindrian_eureka/data/rs/` carry the header "Copyright (c) 2026 Mindrian. BSL 1.1."
- Whether reuse of the numeric settings needs permission is a question for the owner. This record does not answer it.

## 6. Gap list

| Gap | Question | Who can close it | What closes it |
|-----|----------|------------------|----------------|
| G1 | Who wrote the code beyond one person? | The original author | A written reply from the source author that lists all contributors |
| G2 | Does a paper exist? What is its citation (venue, year, DOI)? | The original author | A written reply from the source author that gives the citation, or a statement that no paper exists |
| G3 | What terms came with the hand-over? | The owner and the original author | The original hand-over message or a written reply that states the terms |
| G4 | Who wrote the deck? Do the code and the deck share an owner? | The owner and the original author | A copy of the deck file with its author field, or a written reply from the source author |
| G5 | Does written permission to adapt or redistribute exist? | The original author | A written reply from the source author that states permitted use and preferred citation |
| G6 | Does an employer or institution of the author have a claim? | The original author | A written reply from the source author on affiliation and any claim. This is listed as a gap only. This record gives no legal opinion. |

## 7. Decision and conditions

Decision: no-go. Status: draft. The fields `decided_by` and `decided_on` are the owner's. An agent does not change them.

To move to go, the owner needs: G1, G2, G3 and G5 closed, and condition C1 done. A go with open gaps is invalid, and the test file `tests/test_release_gate_record.py` rejects it. The owner may also choose internal-only. This record is a project status note and not legal advice.

## 8. Effect on phases

- Phases 2 and 3 proceed on a no-go.
- Phase 4 ships the unusual-pairs example and guide as internal only on a no-go, and records the reason.
- The decision gates public shipping in Phase 4 only.

## 9. Partner-internal distribution ruling (2026-10-29)

PROVEN (the owner's ruling, given in conversation on 2026-10-29): the owner approved partner-internal distribution of the engine package to JHTV on 2026-10-29. The scope is that partner's own machine and its own staff. The package is not public and not redistributable. Public distribution stays no-go, and the fields `decision`, `status` and `reopen_when` above are unchanged. G1, G2, G3 and G5 stay open. This ruling closes no gap. The partner guide is `docs/partner-run-guide.md`. The 4 front-matter keys that start with `partner_internal_` record this ruling, and `tests/test_release_gate_record.py` pins them.
