# MindrianOS Eureka

<p align="center">
  <img src="story/mindrian-opportunity-story/assets/theo-face-rest.svg" alt="Theo, the MindrianOS method guide" width="112" />
</p>

**Find the questions worth solving. Then help people test them.**

MindrianOS Eureka is a local-first set of research and innovation capabilities for MindrianOS. It helps people explore alternative futures, find opportunity problems inside them, and develop selected opportunities into clear, testable problems. Its methods can surface patterns, mechanisms, evidence gaps, and hard questions. People decide what matters and what to do next.

**MindrianOS entrypoint:** `/mos:eureka` · **Repository:** `mindrian-eureka` · **Runtime:** Python 3.11+

> **Theo is the method guide, not an oracle.** Theo helps the host choose a useful framework and sequence of inquiry. The Theo face moves through curiosity, searching, recognition, skepticism, decision, and handover: each pose signals how the inquiry is progressing. The host keeps room context, approvals, evidence review, and decisions. Eureka runs only the selected bounded method over the material the host supplies.

## The innovation process

The method starts by asking what kind of problem is in front of us. Different questions need different work:

| Problem type | The question | The work |
|---|---|---|
| **Undefined** | What might a future look like? | Imagine alternatives. Treat them as possibilities to explore, not predictions. |
| **Ill-defined** | Where might a worthwhile opportunity emerge? | Explore a field or future for needs, tensions, and candidate problems. There may be many useful answers. |
| **Well-defined** | Can we meet these stated criteria? | Develop and test a solution against explicit constraints and success measures. |

The point is to look beyond today's visible problems without losing contact with evidence. A selected opportunity must eventually become a well-defined problem before a team can test solutions or build a business case.

```mermaid
flowchart LR
  Q[Question about a future] --> U[Explore an undefined space]
  U --> I[Find opportunities in an ill-defined space]
  I --> C[Choose a candidate to investigate]
  C --> W[Define a testable problem]
  W --> S[Test solutions and develop the case]
  H[Human judgment] -. steers and reviews .-> U
  H -. steers and reviews .-> I
  H -. chooses .-> C
  H -. decides .-> S
```

The agents should be useful in four ways: **research assistant** (find and organize source-linked material), **method guide** (explain which inquiry fits the problem), **mentor** (help the user make the next move), and **devil's advocate** (surface assumptions, counterevidence, boundary conditions, and falsifiers). Critique should improve the investigation, not automatically reject an idea. The agents must show uncertainty and never present a similarity, analogy, or generated hypothesis as proof of novelty, demand, or value.

## What this repository provides

This repository packages bounded methods behind CLI and MCP interfaces, with a readiness-aware catalog describing what each job needs and what its result means. Available local surfaces include:

- **Opportunity pair discovery:** find unusual pairs in an authorized collection; combine RS and HSI shortlists for follow-up.
- **Portfolio signals:** compare wording and semantic patterns, inspect supplied taxonomy coverage, and examine room-relative whitespace hypotheses.
- **Cross-domain reasoning:** retrieve supplied mechanisms, compare structural fit, map a selected mechanism to a target problem, and prepare evidence checks.
- **Research support:** prepare bounded multidisciplinary tasks and group returned findings supplied by the host.
- **Challenge and review:** compare text for restatement, audit claim/evidence traceability, and organize sourced perspectives for a human review.
- **Other analysis:** compare explicitly coded decision sequences under supplied models; validate and package proposed portfolio relationships.

These are not all complete source-engine workflows. Some catalog jobs are blocked or planned; some callable stages are experimental or need host-brokered research. The [engine jobs guide](docs/engine-jobs.md) explains when to use each family. The [capability catalog](docs/capability-catalog.md) and `eureka capabilities` command are authoritative for exact IDs, maturity, inputs, and limitations.

## Quick start

Install the package and inspect the available job contracts:

```bash
uv sync
uv run eureka capabilities
uv run eureka capability opportunity.find_cross_domain_pairs
```

For local MCP use, install the MCP and local encoder extras. Point Eureka at an already available model; the server does not download one:

```bash
uv sync --extra mcp-server --extra modern-encoder
MINDRIAN_EUREKA_RS_MODEL_PATH=/absolute/path/to/local-model uv run eureka-mcp
```

The server uses stdio MCP. Configure the host to launch this command in its MCP server settings. For a constrained container launch, see [Run the MCP server](#run-the-mcp-server).

To run a supporting stage directly, prepare the JSON request required by that capability and pass it to `eureka-workflow`:

```bash
uv run eureka-workflow portfolio.find_hybrid_similarity_pairs request.json --output result.json
```

See [Using capabilities](docs/using-capabilities.md) and the relevant capability page for request schemas and examples. Direct CLI use runs only the named computation; it does not establish MindrianOS room scope or approval.

## How MindrianOS and Eureka work together

```mermaid
sequenceDiagram
  actor Person
  participant MOS as MindrianOS host
  participant Theo as Theo method guide
  participant E as Eureka MCP / CLI
  Person->>MOS: State a question, goal, or opportunity
  MOS->>Theo: Ask which method fits (when useful)
  Theo-->>MOS: Return general framework guidance
  MOS->>Person: Confirm objective, scope, and method
  MOS->>E: Send bounded, authorized input bundle
  E-->>MOS: Return result, sources, uncertainty, and next-step guidance
  MOS->>Person: Review evidence and decide what to do
```

**MindrianOS owns** the user conversation, room access, scope, approval gates, Theo calls, external research, human decisions, and portfolio or graph writes. **Eureka owns** the capability catalog, bounded computations, local job state, validation, and result provenance. Eureka does not read room paths, call Theo, fetch unapproved research, issue `/mos:*` commands, or write to the MindrianOS portfolio.

The MindrianOS `/mos:eureka` adapter to this repo's capability MCP is still to be wired. Until it is, a user-facing MindrianOS run must not be described as calling Eureka automatically. See the [host integration contract](docs/integrations/mindrianos.md) for the complete boundary and handoff.

## Run the MCP server

### Local process

```bash
uv sync --extra mcp-server --extra modern-encoder
MINDRIAN_EUREKA_RS_MODEL_PATH=/absolute/path/to/local-model \
  MINDRIAN_EUREKA_DATA_DIR=/absolute/path/to/eureka-data \
  uv run eureka-mcp
```

`MINDRIAN_EUREKA_DATA_DIR` holds job and cache data. Keep it in a location that follows the room's data handling and retention policy. Direct local execution is useful for development but does not provide OS-level isolation.

### Container process

```bash
docker build -t mindrian-eureka:local .
export MINDRIAN_EUREKA_RS_MODEL_PATH=/absolute/path/to/local-model
export MINDRIAN_EUREKA_DATA_DIR=/absolute/path/to/eureka-data
scripts/run-mcp-container
```

The wrapper disables network access, mounts the model read-only, makes the container root filesystem read-only, and applies configurable CPU and memory limits. The model must already exist on the host.

## Readiness at a glance

| Area | Current state |
|---|---|
| RS opportunity-pair discovery | Runnable CLI and durable stdio MCP jobs; experimental pending evaluation. |
| RS + HSI signal scout | Runnable shortlist union; it does not fuse scores or qualify opportunities. |
| SME mapping and research handoff | Local mapping and bounded workflow stages; external research is host-brokered and source/license review remains open. |
| HSI, analogy, Genesis, Jason, BONO, graph stages | Selected CLI/MCP stages are callable; full-family workflows have mixed or incomplete readiness. |
| OMM decision-sequence analysis | Experimental; not an opportunity finder or validated measure of a person's ability. |
| MindrianOS integration | Contract is documented; the `/mos:eureka` adapter remains outstanding. |

See the [machine-readable capability catalog](src/mindrian_eureka/data/capability-catalog.v1.json) for the complete status of each stable capability ID. See the [JHTV opportunity assessment](evaluations/room-runs/jhtv-opportunity-leads-2026-10-18.md) for an example of results framed as diligence leads with supporting evidence and disqualifying questions.

## Development

```bash
uv sync --extra mcp-server
uv run eureka capabilities
```

Useful entry points:

- `eureka` — inspect capability and host-workflow contracts.
- `eureka-mcp` — start the stdio MCP server.
- `eureka-rs` — run RS pair discovery from a prepared request.
- `eureka-sme` — run SME mapping and research workflow stages.
- `eureka-omm` — run decision-sequence analysis (install the `hmm` extra).
- `eureka-workflow` — run a named supporting capability stage.
- `eureka-scout` — run the local RS + HSI signal scout.

See [Using capabilities](docs/using-capabilities.md) for CLI and MCP examples, [Architecture](docs/architecture.md) for system design, and [Engine jobs](docs/engine-jobs.md) for JTBD and method guidance.

## Theo's role and face

Theo is MindrianOS's outside method thinker. The face is a reasoning cue, not decoration: curiosity opens a question, searching gathers material, recognition marks a possible connection, skepticism tests it, and decision/handover returns agency to the person. Pair every pose with clear language so the method remains understandable without the visual. Theo's current MCP provides general framework guidance; it does not receive arbitrary room material or judge a specific Eureka result. The host owns the boundary and any case-specific review.

