# Hub password gate record

Recorded 2026-10-25. Owner ruling D-17 keeps the optional gate. The implemented format is specified by Phase 2.1 Plan 14 and `src/mindrian_eureka/hub/gate.py`.

## What the gate does

`eureka hub RUN_DIR --password-env NAME` reads a passphrase from the named environment variable and encrypts the hub data. No flag takes the passphrase itself. The locked page contains the form and fixed copy; record fields and counts appear only after a successful unlock. The passphrase is absent from generated files, summaries and application error messages.

## The derivation

- Plaintext is canonical JSON from the verified payload, encoded as UTF-8.
- Salt is the first 16 bytes of SHA-256 of `eureka.hub.gate.salt.v1` followed by the 32 raw bytes of the run manifest digest.
- PBKDF2-HMAC-SHA256 derives a 32-byte key from the UTF-8 passphrase and salt with 600,000 iterations. The [Python PBKDF2 documentation](https://docs.python.org/3.12/library/hashlib.html#hashlib.pbkdf2_hmac) describes this API.
- Nonce is the first 12 bytes of HMAC-SHA256 under that key over `eureka.hub.gate.nonce.v1`, the salt and the SHA-256 of the plaintext. The [Python HMAC documentation](https://docs.python.org/3/library/hmac.html#hmac.new) describes the keyed digest API.
- AES-256-GCM encrypts the payload with the associated data `eureka.hub-envelope.v1|600000`. The ciphertext ends with its 16-byte authentication tag, matching WebCrypto. The [installed cryptography version's AESGCM documentation](https://cryptography.io/en/46.0.3/hazmat/primitives/aead/#cryptography.hazmat.primitives.ciphers.aead.AESGCM) explains tag verification and the importance of nonce handling.
- The envelope stores the schema, fixed algorithm names and iteration count, base64 salt, base64 nonce and base64 tagged ciphertext. It stores no key. Unsupported parameters fail before an edited envelope can request unbounded derivation work.

The versioned derivation contexts and associated data form one format; a format change requires reviewing them together. The frozen known-answer test and the 1,000-message nonce regression detect changes. That regression is not proof that a finite nonce space cannot collide, and this custom deterministic construction has not had an independent cryptographic audit.

## Why salt and nonce are derived

D-07 requires repeatable output. The same payload, passphrase and run digest produce the same bytes. A different payload enters the nonce derivation. The source-link exception from Plan 09 still applies: moving a file-linked hub can change relative source links and thus the payload.

## What this costs

Repeated builds of one run use the same salt and can be linked; precomputation for that run can be reused. The same inputs repeat the ciphertext. Its length reveals the amount of data. An offline guess costs 600,000 PBKDF2 rounds; a copied file cannot count or limit wrong tries. A short passphrase gets a build warning.

The hub manifest intentionally retains the required opaque run-manifest digest for provenance. It has `gated: true` and no counts. The digest is public metadata and also links builds of the same run. It is absent from the locked HTML and envelope plaintext fields.

## What the gate does not protect

The gate does not protect a computer that already has the passphrase, decrypted data in browser memory, the original run or source folders, earlier unencrypted exports or backups, or the terminal's build summary. It does not encrypt the file names, folder structure, styles, vendored library or surrounding page scripts. A trusted application copy is still required. Clearing the input and dropping the passphrase variable after unlock is not secure memory erasure.

## Browser results

Chromium and Firefox passed from local file URLs with a UTF-8 test passphrase. One measured unlock, including page startup after derivation, took 79.2000 ms in Chromium and 119.0000 ms in Firefox. These are observed local timings, not device guarantees.

Tests cover correct and wrong passphrases, changed ciphertext and nonce, truncated base64, changed iteration count and envelope schema, authenticated non-JSON data and a wrong payload schema, absent WebCrypto, Show/Hide, Enter, hostile record text, and locked-screen widths. Both tested origins reported zero local and session storage entries and an empty cookie string after unlock. The application contains no storage writes.

WebKit does not start on this machine. Safari remains a human check; no Safari result is claimed. Owner visual and screen-reader review remain pending.

## The dependency

Building a locked hub needs `cryptography` through the optional `hub-gate` extra. Tests here used installed version 46.0.3. The approved declared range is at least 44 and below 51; the existing lock records 50.0.2. No dependency was downloaded for this implementation. An ungated build and CLI help do not import the cipher library. Opening a locked hub needs only a current browser.

## Fallbacks

L05 reports an unsuccessful open, including authentication failures. L06 reports missing WebCrypto and disables unlocking. L08 reports authenticated data that cannot be read as a supported payload; its face is Limit. Other locked states retain Boundary. None of these messages echoes the passphrase. L07 states the same at-rest limit as this record.
