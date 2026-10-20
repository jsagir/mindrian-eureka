# JHTV IP-finance domain detector evaluation

**Run:** 2026-10-20  
**Capability:** `research.classify_ip_finance_domain_signals`  
**Room:** JHTV Fast Forward (Oliver Kuntz)  
**Source snapshot:** July 6, 2026 technology catalog  
**Purpose:** test the newly exposed LATEST Genesis IP-finance lexicon on the complete catalog and check it for misleading domain assignments.

## Run and lineage

- Input: `/home/jsagi/decks/jhtv-oliver-eureka-hub/october-2026/technologies-full-extract.csv`
- Input SHA-256: `efa77ea633dc800a10055eafbd279f98dc1149f42f738536b7808f621871ff5a`
- Records processed: 2,117
- Fields used: title, unmet need, one preferred description field (`description_full`, else `value_prop`, else `tech_description`), and category keywords. Inventor and contact fields were excluded.
- Scope/snapshot: `room:jhtv-oliver-kuntz` / `sha256:efa77ea633dc800a10055eafbd279f98dc1149f42f738536b7808f621871ff5a`
- Input fingerprint: `764563e134d761ffbb89652b013b60fd30bb264beb2394b472653f7618fa7b1d`
- Output SHA-256: `e95b47192f8fc00dd73e8655820e58b5461ffaa95636a9443076ff993eb14384`
- Reproduction command:

```sh
PYTHONPATH=src uv run python evaluations/room-runs/run_jhtv_ip_finance_domain_detection.py \
  --input /home/jsagi/decks/jhtv-oliver-eureka-hub/october-2026/technologies-full-extract.csv \
  --output /tmp/jhtv-ip-finance-result.json
```

The reproduction script verifies the exact source CSV hash before running. A second run returned byte-identical output.

## Observed signals

| Best domain label | Records |
|---|---:|
| Biotechnology | 844 |
| Computer vision | 280 |
| Machine learning | 280 |
| General systems | 248 |
| Robotics | 99 |
| Patent analytics | 86 |
| Credit risk analysis | 24 |
| IP-backed finance | **0** |

These are the source algorithm's highest-label counts, not validated classifications. The more specific IP-backed-finance pattern did not match any record. The service did not identify an opportunity.

## Negative-control finding

The source lexicon matches short uppercase acronyms such as `PD` against credit-risk terms. In this biomedical catalog, the same letters occur in Parkinson's disease and programmed-death immunotherapy records. Of the 24 records labeled `Credit-Risk-Analysis`, 22 fired the `PD` acronym rule. For example:

- C12915 is a PD-1/PD-L1 immunotherapy record.
- C14766 explicitly concerns Parkinson's disease.
- C14812 is a magnetic catheter, drain, and tube device; its high heuristic score came from repeated `PD` text, not credit-risk content.

The adapter now returns source-linked `ambiguous_acronym_match` warnings. This preserves the upstream classification while making the risk visible to callers. Across the 2,117 records, 56 segments produced warnings involving eight short tokens (`PD`, `AR`, `CAR`, `VR`, `ROI`, `ROS`, `SEP`, and `PE`).

## Decision

This capability is callable and useful as a rough field-routing aid, but this run provides a negative result for an IP-backed-finance opportunity search. Do not add a candidate to the JHTV opportunity bank from these domain labels. Review the source record and use evidence, graph relationships, and appropriate subject-matter methods before treating any domain overlap as an opportunity.

The acronym collision should remain part of the regression set. Source authorship and reuse rights also remain unresolved; local evaluation only.
