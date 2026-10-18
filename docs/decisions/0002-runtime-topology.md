# ADR 0002: Initial runtime topology

- **Status:** proposed
- **Date:** 2026-10-18

## Decision proposal

Use one MindrianOS-facing local MCP server, a capability registry, a durable local job ledger, and bounded workers. Keep Node/TypeScript as the control plane to align with MindrianOS. Run Python-based methods through pinned per-family environments and a versioned JSON worker protocol.

Do not create a separate MCP server for every engine by default. Keep capability modules independently addressable and split them into MCP processes only when a capability requires a genuinely different trust, credential, runtime, scaling, or release boundary.

## Rationale

MCP is the interface. It does not install dependencies, isolate processes, enforce network policy, persist jobs, or own the opportunity portfolio. A local job runner supplies those responsibilities while MindrianOS retains user and room authority.

## Revisit when

- a runtime cannot be safely supported in a bounded child worker;
- a capability requires different credentials or network permissions;
- deployments must scale or release independently;
- host tool discovery becomes confusing in user evaluation.

