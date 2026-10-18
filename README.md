# MindrianOS Eureka

**MindrianOS entrypoint:** `/m:os:eureka`  
**Repository:** `mindrian-eureka`  
**Status:** runnable local RS capability with CLI, stdio MCP, durable jobs, and human evaluation records. Empirical validation, host integration, and source/license review remain open.

MindrianOS Eureka is the standalone opportunity-discovery runtime MindrianOS will use to find, assess, and accumulate promising opportunity candidates from authorized material. It is designed to support local analysis first, controlled outside research, and a growing portfolio of evidence-linked candidates.

The user asks MindrianOS to scout or deepen an opportunity. MindrianOS frames the job, binds room scope, obtains approval for any outbound work, and calls this repo through MCP. Eureka runs bounded capabilities, returns versioned results with source lineage and uncertainty, and leaves filing and human decisions to MindrianOS.

## Ownership boundary

- **MindrianOS owns:** user experience, room/session binding, access control, approval gates, Theo/framework guidance, canonical opportunity portfolio, human decisions, and truth-state changes.
- **MindrianOS Eureka owns:** capability catalog, job planning/execution, worker/runtime management, run persistence, engine adapters, result validation, and evidence/provenance envelopes.
- **Eureka does not:** choose an unapproved room scope, access unrelated files, make unapproved network calls, write directly to MindrianOS rooms/graph/portfolio, or promote a generated hypothesis to fact.

## Architecture

See [the architecture proposal](docs/architecture.md). The first deployment is one local MCP server with internal capability modules. The RS capability includes a constrained container launcher; other engine families are not yet migrated.

The [Harness² design review](docs/inspirations/harness2-analysis.md) records a possible later workflow-evaluation layer. It is a design reference, not an adopted dependency or a claim that Eureka already learns from runs.

The proposed MindrianOS call is a workflow, not a raw “run every engine” command:

1. Define objective and authorized scope.
2. Inspect and prepare traceable input material.
3. Select a suitable capability or explain missing prerequisites.
4. Run a bounded job with explicit network/model policy.
5. Return a validated result and durable job handle.
6. Let MindrianOS and the user review, research, and file candidate decisions.

## Current state

The first implemented capability is `opportunity.find_cross_domain_pairs` (user-facing: **Find Cross-Domain Opportunity Pairs**). It has a CLI and job-oriented stdio MCP interface, SQLite job persistence, embedding cache, local/external-bundle/hybrid run modes, provenance-bearing results, cancellation, deletion, and human review records. It runs only on the artifact bundle MindrianOS supplies; external research retrieval and grant authorization stay with the host. No original engine source or weights have been copied. The source deck/archive, license, and exact reproduction status remain unresolved, and the capability stays experimental until evaluated; see [the method and source note](docs/engines/opportunity-pairs.md).

## Run the local MCP capability

Use Python 3.11 or newer and provide a local semantic model. The model is not downloaded by the MCP server.

```bash
uv sync --extra mcp-server --extra modern-encoder
MINDRIAN_EUREKA_RS_MODEL_PATH=/absolute/path/to/local-model uv run eureka-mcp
```

For a containerized local MCP process, build once and launch the stdio wrapper:

```bash
docker build -t mindrian-eureka:local .
export MINDRIAN_EUREKA_RS_MODEL_PATH=/absolute/path/to/local-model
export MINDRIAN_EUREKA_DATA_DIR=/absolute/path/to/eureka-data
scripts/run-mcp-container
```

The wrapper disables network access, mounts the model read-only, makes the container root filesystem read-only, and applies configurable CPU/memory limits. MindrianOS can launch the wrapper as its stdio MCP command. The direct Python command is useful for development and does not provide OS/container isolation. The engine does not itself validate scope or grant IDs; MindrianOS must do that before sending material. See the [capability guide](docs/engines/opportunity-pairs.md) and [MindrianOS host integration contract](docs/integrations/mindrianos.md) for the full user journey and boundaries.

## Naming

`/m:os:eureka` is the intended MindrianOS workflow name. **Eureka is the portfolio-level opportunity discovery workflow**, not necessarily one algorithm. Users should see job names such as “Find a bottleneck,” “Find portfolio gaps,” “Find breakthrough pairs,” and “Test a structural analogy,” with plain-language “hire when” descriptions.

