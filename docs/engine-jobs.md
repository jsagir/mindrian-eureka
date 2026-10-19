# Engine jobs and when to use them

Mindrian's intelligence agents are built to explore uncertainty for opportunity, especially in wicked problems: evolving, interconnected challenges with unclear boundaries, contested frames, and no single final formulation or solution. Their job is to help people map the uncertainty, explore alternative futures, connect signals across fields, and develop multiple sourced opportunity hypotheses. They act as research assistant, method guide, mentor, and devil's advocate. They expose assumptions, contradictions, counterevidence, unintended effects, and useful next questions. They do not collapse uncertainty into false certainty or decide which opportunity is best.

Wickedness is the context the agents explore, not a stage they claim to finish. Within it, they use different inquiry modes: explore **undefined problems** to imagine alternative futures; explore **ill-defined problems** to discover opportunity areas; and frame selected paths as **well-defined problems** when a bounded test is useful. Movement between these modes is iterative: evidence can reopen the frame, and a new possibility can restart future exploration. The engine jobs below are supporting methods in that work. Engine acronyms and source-package names remain in code and provenance; capability IDs stay stable for existing callers. The readiness column describes what this repository currently provides, not what exists in the source package.

| User-facing job | Use it when… | Available here |
|---|---|---|
| **Find technical bottlenecks and unusual connections** | A scoped collection is available and you want to surface constraints or cross-field pairs that deserve investigation. | RS pair screening and an RS+HSI shortlist are callable by CLI and MCP. The original fetch, expert, and thesis routines are not all ported. |
| **Find unusual similarities and thin areas in a portfolio** | A comparable portfolio and, for whitespace checks, a clear taxonomy or reference baseline are available. | HSI pair scoring, taxonomy counts, and room-relative whitespace stages are callable by CLI and MCP. The full source pipeline is not ported. |
| **Find and challenge opportunity leads** | You want candidate changes grounded in room material, with assumptions and evidence prepared for human review. | A local RS+HSI shortlist is callable. The full harvest, critic, and qualification workflow is not. |
| **Find mechanisms that could solve a problem in a new way** | Work is stuck in its familiar field and a sourced mechanism corpus or host-approved research results are available. | Local lexical retrieval and structural-fitness stages are callable. The full retrieval and whitespace workflow is not. |
| **Map a mechanism and test what might transfer** | You have a source mechanism, a target problem, and claim-linked evidence, and want testable mapping hypotheses. | SME mapping plus research-plan, bundle-validation, and reviewer-assessment stages are callable by CLI and MCP. External research remains host-brokered. |
| **Plan and synthesize research across fields** | A question needs several confirmed disciplines and you need bounded research tasks or a careful grouping of returned findings. | Planning and exact-claim grouping are callable by CLI and MCP. Search execution, expert panels, and consensus formation are not. |
| **Compare claims and challenge a proposed solution** | Descriptions may restate one another, or a proposal needs its evidence, assumptions, and falsifiers checked. | Text-difference analysis and claim-traceability review are callable by CLI and MCP. The full source pitch-critique workflow is not. |
| **Compare patterns in decision sequences** | You have explicitly coded decision traces and fully specified competing models, and want relative model fit for research. | OMM analysis is callable by CLI and MCP with the optional HMM dependency. It is not a person score or opportunity finder. |
| **Prepare a balanced review of competing views** | A bounded decision has source-linked arguments from different perspectives and needs open questions organized for a human ruling. | Six Thinking Hats review preparation is callable by CLI and MCP. The full BONO research and governed-debate loop is not. |
| **Find and review links between portfolio items** | You have an authorized graph snapshot and want missing or useful relationships explained before anyone files them. | Candidate-link validation and packaging are callable by CLI and MCP. Graph discovery and ranking are not. |

## How the jobs explore uncertainty

1. **Map the wicked challenge.** Identify system boundaries, connected actors, contested definitions, feedbacks, uncertainty, and what is currently unknown. Keep multiple credible frames visible.
2. **Explore possible futures.** For a question such as “What might healthcare look like if patients rarely see a doctor in person?”, surface plausible alternatives and trace what could change in each. This is exploration, not forecasting.
3. **Search the uncertainty for opportunities.** For a question such as “What might become possible as prosthetics, sensing, and human-machine interfaces change?”, connect research and portfolio signals across fields; surface candidate needs, tensions, and leverage points with sources and uncertainty attached.
4. **Develop several leads.** Compare opportunity hypotheses against the user's goals and available evidence. Keep the choice with the user and team; the intelligence should expand and sharpen the search, not declare a universal “best” idea.
5. **Make one path testable.** When useful, frame a selected opportunity as a well-defined problem with explicit constraints and success criteria. Testing that path produces learning; it does not solve the entire wicked challenge.
6. **Return learning to the exploration.** New evidence may change the system map, assumptions, or future scenarios. Reopen the inquiry and continue looking for opportunities rather than forcing a linear finish.

Use a devil's-advocate pass to test a candidate's assumptions, counterevidence, boundary conditions, unintended effects, and falsifiers. The aim is to improve the team's reasoning and identify what to learn next, not to reject ideas automatically. Use mentor and guide behavior to explain the next method and why it fits the current uncertainty; don't run every engine on every candidate.

## Readiness rule

The capability catalog is the source of truth for the exact callable stage, prerequisites, and limits. A family-level job can describe a desired outcome even when its full workflow is blocked or planned. Mindrian should offer only the implemented stage whose inputs are ready, and should show its readiness before invoking it.

See the [machine-readable capability catalog](../src/mindrian_eureka/data/capability-catalog.v1.json) and [using the capabilities](using-capabilities.md) for stable IDs and invocation details.
