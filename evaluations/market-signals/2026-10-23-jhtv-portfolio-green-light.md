---
record_type: market-signal
record_id: 2026-10-23-jhtv-portfolio-green-light
signal_strength: critical
meeting_date: 2026-10-23
room_binding:
  room_id: jhtv-oliver-kuntz
  meeting_id: 2026-10-23-jhtv-portfolio-green-light-session
  pointer_only: true
review_status: proposed
source_roles:
  - partner
  - mentor
  - founder
twin: 2026-10-23-jhtv-portfolio-green-light.json
---

# Market signal: partner organization portfolio green light

A partner organization gave the clearest buyer signal so far: a green light to run its whole technology portfolio through the tool. The data cannot leave a secure enclave, so the tool must be installed and run on the partner's side. These are 16 candidate claims, all proposed. No person has confirmed any of them. No payer, price, budget or timeline came up.

## Claims

| ID | Claim in plain words | Knowledge type | Confidence | Market signal | Requirement impact |
|----|----------------------|----------------|------------|---------------|--------------------|
| MS-01 | The partner reports a green light to run the whole portfolio. No scope, payer, price or timeline. The approval is to run the tool, not to pay. | fact | 0.9 | critical | RUN-01 |
| MS-02 | The partner organization's data is not organized for machine use. A data operations function is being stood up and is a likely owner. Readiness and budget not stated. | fact | 0.85 | critical | RUN-02 |
| MS-03 | No opportunity in the current bank is validated. Domain experts and licensing staff would have to review them before a buyer acts. | fact | 0.9 | critical | RUN-05 |
| MS-04 | The partner reacted strongly and asked what counts as a eureka and whether the technologies are licensable. The founder's definition was loose. No purchase commitment. | fact | 0.75 | critical | RUN-05, EXM-02 |
| MS-05 | Technology licensing associates are the likely users. They find new opportunities and work on given ones. | fact | 0.9 | critical | EXM-02 |
| MS-06 | The full portfolio data cannot leave the secure enclave. Install and run inside it, guided by shared screen, with no data handover. | fact | 0.9 | critical | RUN-01, RUN-03, DOC-01, HOST-01 |
| MS-07 | The founder is separating the engine so it installs on its own on the partner's machine. It needs a container runtime and heavy compute. No deadline. The engine name is uncertain (speech-to-text). | fact | 0.7 | none | RUN-01, DOC-01, HOST-01 |
| MS-08 | The tool does not find licensing or outcome signal alone. A person must say which records show outcomes. Data so far has no licensed-technology signal. | causal | 0.9 | critical | RUN-05, EXM-02 |
| MS-09 | Compute limits extension to other universities. The founder builds for ordinary hardware. Useful results on ordinary PCs are not yet shown. | assumption | 0.75 | none | DOC-01, RUN-01 |
| MS-10 | Extending to other universities is the agreed next step. Timing is not settled: start talks early, or show local value first. | heuristic | 0.7 | none | none |
| MS-11 | One earlier pilot gave a business-development person a market suggestion he had not considered. One reported case. Outcome not stated. | causal | 0.7 | none | none |
| MS-12 | The partner will send export headers and coded values for technology states, including commercial outcomes. The founder will return preparation commands. | fact | 0.9 | critical | RUN-02, RUN-05 |
| MS-13 | Soft commitments with no firm dates: an introduction to another university's transfer office, an introduction for a possible talk, and a review of an earlier email. | fact | 0.7 | none | none |
| MS-14 | A shared-screen working session of about 1 hour is proposed for 2026-10-27. No backup slot. The date is inferred. | fact | 0.85 | critical | none |
| MS-15 | The opportunity bank page will be password-protected before use or sharing, because the combinations are the valuable part. Sensitivity not fully settled. | fact | 0.8 | none | out of scope (see below) |
| MS-16 | An inventor may refuse to work with another. The mentor suggests selling separate patents as a package. No evidence for this route. | assumption | 0.65 | none | none |

## What this changes for Eureka

These are proposed readings. Each needs a human decision before it changes a requirement.

- **Enclave install (MS-06, MS-07):** A candidate need for an install that runs fully offline on the partner's machine, with a run manifest and hashes the partner can inspect. Touches RUN-01 (one command), RUN-03 (run manifest), DOC-01 (`eureka doctor` on a locked machine) and HOST-01 (the host calls the engine without a data handover).
- **Licensing signal needs a human (MS-08, MS-12):** The engine cannot infer outcomes. A person supplies which fields mark outcomes. Touches RUN-05 (labels must say outcome signal came from the user) and EXM-02 (the reproduce guide states this limit in plain English).
- **Password (MS-15):** Out of scope for the engine. Page protection belongs to the host and the sharing step. Record only.
- **Compute and local PC (MS-09):** The belief about ordinary hardware is untested. Touches DOC-01 (doctor reports hardware limits) and RUN-01 (the command should fail clearly on weak hardware).
- **Validation gap (MS-03, MS-04):** Every output keeps "candidate" labels and says what a score means. Touches RUN-05. The unclear meaning of "eureka" for the buyer also touches EXM-02.
- **Data readiness (MS-02, MS-12):** The partner's data needs preparation before a run. Touches RUN-02 (clean corpus with stable IDs).

## Not established

- No payer, price, budget or timeline.
- No purchase commitment. The only commercial signal is the green light to run the tool.
- No expert at the partner organization has reviewed any opportunity.
- No record yet shows which export fields mark licensed or outcome states.
- No result on ordinary hardware.

## How to reuse

Cite the room pointer: room id `jhtv-oliver-kuntz`, meeting id `2026-10-23-jhtv-portfolio-green-light-session`. Do not copy room content into this repository. Keep every claim at its stated confidence and knowledge type. Keep `review_status: proposed` until a person in the room confirms a claim and the room records it. Keep the label "candidate, not verified" on any output that uses these claims.
