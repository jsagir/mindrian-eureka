# Security policy

MindrianOS Eureka processes sensitive research material supplied by its host. Security reports and suspected data exposure should be handled privately.

## Reporting a vulnerability

Use GitHub's **Report a vulnerability** action in the repository's Security tab when it is available. If private vulnerability reporting is unavailable, contact the repository owner directly through GitHub. Do not open a public issue containing exploit details, credentials, room data, or personal information.

Include the affected version or commit, impact, reproduction steps, and any suggested mitigation. Do not attach real user or room data; use a minimal synthetic example.

## Security expectations

- MindrianOS owns authorization, room scope, external-research approval, and portfolio writes.
- Engine requests must use bounded host-prepared bundles; do not pass room paths, credentials, or unrelated files.
- Keep models local unless an explicit, reviewed architecture change allows another route.
- Treat job stores, embeddings, logs, evaluation bundles, and rendered artifacts as potentially sensitive derived data.
- Report suspected exposure promptly and preserve relevant logs without copying sensitive payloads into tickets.
