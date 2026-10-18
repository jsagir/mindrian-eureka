# MindrianOS Eureka

**MindrianOS entrypoint:** `/m:os:eureka`  
**Repository:** `mindrian-eureka`  
**Status:** architecture plus first local capability prototype; MCP orchestration and MindrianOS integration remain future work.

MindrianOS Eureka is the standalone opportunity-discovery runtime MindrianOS will use to find, assess, and accumulate promising opportunity candidates from authorized material. It is designed to support local analysis first, controlled outside research, and a growing portfolio of evidence-linked candidates.

The user asks MindrianOS to scout or deepen an opportunity. MindrianOS frames the job, binds room scope, obtains approval for any outbound work, and calls this repo through MCP. Eureka runs bounded capabilities, returns versioned results with source lineage and uncertainty, and leaves filing and human decisions to MindrianOS.

## Ownership boundary

- **MindrianOS owns:** user experience, room/session binding, access control, approval gates, Theo/framework guidance, canonical opportunity portfolio, human decisions, and truth-state changes.
- **MindrianOS Eureka owns:** capability catalog, job planning/execution, worker/runtime management, run persistence, engine adapters, result validation, and evidence/provenance envelopes.
- **Eureka does not:** choose an unapproved room scope, access unrelated files, make unapproved network calls, write directly to MindrianOS rooms/graph/portfolio, or promote a generated hypothesis to fact.

## Architecture

See [the architecture proposal](docs/architecture.md). The first deployment is one local MCP server with internal capability modules and bounded Node/Python workers. Engine isolation and deployment can be split later when a real dependency or trust boundary warrants it.

The [Harness² design review](docs/inspirations/harness2-analysis.md) records a possible later workflow-evaluation layer. It is a design reference, not an adopted dependency or a claim that Eureka already learns from runs.

The proposed MindrianOS call is a workflow, not a raw “run every engine” command:

1. Define objective and authorized scope.
2. Inspect and prepare traceable input material.
3. Select a suitable capability or explain missing prerequisites.
4. Run a bounded job with explicit network/model policy.
5. Return a validated result and durable job handle.
6. Let MindrianOS and the user review, research, and file candidate decisions.

## Current state

The first capability prototype is `opportunity.find_cross_domain_pairs` (user-facing: **Find Cross-Domain Opportunity Pairs**). It implements the documented structural/semantic disagreement method and exposes a separately named modern encoder option. It is a local CLI capability, not yet an MCP service. No original engine source code or model weights have been copied. The PPTX/package source license and exact reproduction status remain unresolved; see [the method and source note](docs/engines/opportunity-pairs.md).

## Naming

`/m:os:eureka` is the intended MindrianOS workflow name. **Eureka is the portfolio-level opportunity discovery workflow**, not necessarily one algorithm. Users should see job names such as “Find a bottleneck,” “Find portfolio gaps,” “Find breakthrough pairs,” and “Test a structural analogy,” with plain-language “hire when” descriptions.

