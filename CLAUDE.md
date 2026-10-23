<!-- GSD:project-start source:PROJECT.md -->

## Project

**MindrianOS Eureka**

MindrianOS Eureka is a local Python engine (CLI + stdio MCP server) that finds candidate opportunity pairs in a collection of documents. It ranks pairs where meaning-similarity and vocabulary-structure similarity disagree (the unusual-pairs engine, the wording-and-meaning pairs engine, graph services). It returns leads for human review. It never claims novelty, evidence, or value.

Repo: `mindrian-eureka`. Runtime: Python 3.11+ with `uv`. Used by MindrianOS (`/mos:eureka`) and by direct CLI.

**Core Value:** A user who is not the author can install Eureka, run it on their own collection with one command, and get the same ranked candidates every time, with hashes and settings that prove it. Output stays labeled "candidate, not verified".

### Constraints

- **Offline by default**: engine makes no network calls; models must already be on disk.
- **Determinism**: ranking is code, no LLM; seeds and versions are recorded in result provenance.
- **Honest labels**: every output keeps "candidate, not verified" wording.
- **Privacy**: embeddings are derived sensitive data; cache and job data stay local with owner-only permissions.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->

## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `$gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `$gsd-debug` for investigation and bug fixing
- `$gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `$gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
