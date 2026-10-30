# Harness²: transferable design lessons for MindrianOS Eureka

**Purpose:** assess Harness² as a design reference for Eureka's future workflow selection and evaluation layer.
**Status:** source review; no Harness² code or benchmark data has been copied or executed.

## Summary

Harness² is useful as a reference for improving the *harness around an agent*: task instructions, tools, memory, orchestration, and bounded iteration. Its central transferable idea is to propose workflow changes, probe them against a task, compose a revised harness, and retain evidence-backed lessons for later work. For Eureka, this suggests evaluating versioned workflow recipes—how capabilities are selected and sequenced—after the capability contracts and run records are stable.

It does not justify making research engines rewrite themselves or automatically changing production behavior. Eureka should keep engine code, user scope, permissions, credentials, network policy, and portfolio promotion rules outside any optimization loop. A workflow variant should only be adopted after a controlled comparison and an explicit review.

## What the project describes

The Harness² README describes two related loops:

1. **Task-level recursion:** Propose–Probe–Compose, using contrastive candidate harnesses and parallel or sequential evaluation.
2. **Harness-level recurrence:** retain adopted harnesses and evidence-backed lessons for reuse in a domain.

The repository also describes a ledger for runs, budgets, and duplicate labels; artifact retention and resume; separate judging of selected outputs; and comparable baselines. Its experiment guidance calls for keeping benchmark, executor, evaluated subset, budget, mode, and seed aligned when comparing variants. These are implementation and process ideas we can inspect, not evidence that the same approach will improve Eureka.

The associated preprint is dated October 2026 and reports benchmark gains from the authors' experiments. Those results are author-reported and have not been independently reproduced for this review. They should not be used as a forecast for MindrianOS.

## Transfer map

| Harness² mechanism | Eureka adaptation | Boundary |
|---|---|---|
| Contrastive propose–probe–compose | Compare a small number of workflow recipes for a defined JTBD, then retain the best supported recipe | Recipe changes are suggestions until reviewed; no engine self-modification |
| Run ledger and budgets | Record recipe version, input snapshot, capability versions, model/provider, policy, cost, timing, and evaluation outcome | The runner, not a model-generated report, is authoritative for execution facts |
| Retained artifacts and resume | Preserve stage inputs/outputs, provenance, failure details, and checkpoints for inspectable runs | Resume only if the input snapshot, capability versions, permissions, and grants still match |
| Separate output judging | Evaluate decision usefulness and evidence quality separately from whether the workflow completed | Judge failure is unscored/unknown, never treated as a zero-quality result |
| Domain-scoped lessons | Save an adopted workflow recipe and its evidence for a named JTBD/domain | No cross-room or cross-user reuse by default; scope and sharing policy must be explicit |
| Fixed comparison conditions | Use the same input snapshot, model/provider, permissions, budget, and rubric for baseline and variant | If conditions differ, label the comparison confounded rather than ranking variants |

## Proposed Eureka workflow-improvement boundary

Treat a workflow recipe as versioned data that can select and order already registered capabilities, set bounded iteration counts, and describe the context passed between stages. The evaluator may propose recipe variants. It must not alter capability implementation, expand input scope, grant external access, change the user's objective, or promote an opportunity into MindrianOS's canonical portfolio.

Before comparing variants, Eureka should have:

- Stable capability manifests and input/output contracts.
- Immutable input snapshot IDs and resolvable source provenance.
- A baseline recipe and a task-specific evaluation rubric.
- Runner-recorded budget, model/provider, policy, timing, and failure data.
- A human-review path for workflow adoption and portfolio decisions.

Start with fixed public or synthetic tasks, or a user-approved local evaluation set. Keep evaluation offline or under the same explicit research grant as ordinary runs. Compare candidate recipes in a shadow/evaluation mode; do not let them change production routing automatically. Store lessons with their task domain, evidence, limitations, and expiry/review date.

## Risks and non-transfers

- **Unrestricted execution:** Harness²'s repository describes executor configurations that may have unrestricted network access and may run outside a sandbox. Eureka must not copy that as a default. Network access, filesystem scope, credentials, and resource limits remain host/runner-enforced policy.
- **Benchmark leakage:** the experiment guide warns that public benchmark rubrics can leak into harness instructions. Use held-out tasks or human-authored evaluation criteria where feasible, and report leakage risk.
- **Overfitting and noise:** a workflow can win on a narrow task subset without being better for the user's broader job. Keep a baseline, use repeated/held-out cases when feasible, and scope lessons narrowly.
- **Unreviewed reuse:** a past success may be inappropriate in another room or context. Do not silently transfer private findings or recipes across rooms/users.
- **Complexity before need:** a recursive evaluator adds cost and failure modes. Defer it until ordinary runs can be replayed and evaluated consistently.
- **License provenance:** the project is Apache-2.0, but referenced third-party code and benchmark datasets can have separate terms. This note takes design inspiration only; review provenance and licenses before copying any implementation or data.

## Recommendation

Add workflow-recipe evaluation as a later Eureka layer, after the first stable local run contract and evaluation records. The first useful implementation is a manually curated baseline plus side-by-side recipe comparison and an auditable adoption decision—not an always-running self-improver. This could test whether method selection and handoffs improve user outcomes without claiming that Eureka learns automatically.

## Sources

- [Harness² repository and README](https://github.com/google-research/harness2)
- [Harness² experiment guidance](https://github.com/google-research/harness2/blob/main/docs/EXPERIMENTS.md)
- [Harness² preprint](https://arxiv.org/abs/2610.14224)
