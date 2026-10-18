# Open decisions

1. Confirm long-term repository name and remote URL; local repo slug is `mindrian-eureka`.
2. Confirm whether `/m:os:eureka` is the final command syntax in the intended MindrianOS host, or a display name that maps to the existing `/mos:eureka` route.
3. Choose initial public/private license. No license is declared until ownership and redistribution scope are decided.
4. Select MCP SDK/protocol versions compatible with the MindrianOS host; do not upgrade based on current docs alone.
5. Choose supported Node and Python versions and worker package manager/lock strategy.
6. Decide first capability only after current MindrianOS vs research-package behavior is compared.
7. Decide whether first release needs CLI + MCP or MCP only. Architecture recommends both using the same core API.
8. Define which model provider, if any, may receive user content; local process execution does not imply local inference.
9. Define retention, deletion, and cache invalidation for job inputs/results.
10. Complete source/license ledger before moving any engine code.

