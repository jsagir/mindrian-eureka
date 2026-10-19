# ADR 0001: Standalone MindrianOS Eureka repository

- **Status:** accepted for architecture bootstrap
- **Date:** 2026-10-18

## Context

Opportunity discovery currently spans MindrianOS capabilities and a separate research package containing Node, Python, prompt-driven, and research prototypes. Their names do not guarantee compatible contracts, readiness, permissions, or behavior. MindrianOS must be able to use selected capabilities without inheriting an unreviewed package as one opaque subsystem.

## Decision

Create the standalone repository `mindrian-eureka`; integrate it with MindrianOS's existing `/mos:eureka` user workflow. The repo owns bounded capability execution and job/result contracts. MindrianOS owns room permissions, user approvals, canonical portfolio records, and decisions.

Start with one local MCP server and internal modular capabilities. Use child workers for distinct runtime/dependency needs. Allow future capability-specific MCP processes without requiring them in the first release.

## Consequences

- Engine migrations are individually reviewed and source/license tracked.
- No engine can directly write to MindrianOS room or portfolio state.
- Network access defaults to denied and research uses a host-approved broker.
- The repo can be developed and evaluated independently of MindrianOS through a CLI and synthetic/public fixtures.
- The existing host command is `/mos:eureka`; the integration must preserve its room, Theo, approval, and portfolio behavior while adding this repository's capability MCP.

