# ADR 0001: Standalone MindrianOS Eureka repository

- **Status:** accepted for architecture bootstrap
- **Date:** 2026-10-18

## Context

Opportunity discovery currently spans MindrianOS capabilities and a separate research package containing Node, Python, prompt-driven, and research prototypes. Their names do not guarantee compatible contracts, readiness, permissions, or behavior. MindrianOS must be able to use selected capabilities without inheriting an unreviewed package as one opaque subsystem.

## Decision

Create the standalone repository `mindrian-eureka`; expose its user-facing MindrianOS workflow as `/m:os:eureka`. The repo owns bounded capability execution and job/result contracts. MindrianOS owns room permissions, user approvals, canonical portfolio records, and decisions.

Start with one local MCP server and internal modular capabilities. Use child workers for distinct runtime/dependency needs. Allow future capability-specific MCP processes without requiring them in the first release.

## Consequences

- Engine migrations are individually reviewed and source/license tracked.
- No engine can directly write to MindrianOS room or portfolio state.
- Network access defaults to denied and research uses a host-approved broker.
- The repo can be developed and evaluated independently of MindrianOS through a CLI and synthetic/public fixtures.
- The entrypoint name `/m:os:eureka` is a product/workflow label; the host's exact command registration syntax must be verified during integration.

