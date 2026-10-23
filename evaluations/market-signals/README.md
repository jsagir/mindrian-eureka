# Market signals

This folder holds sanitized records of buyer and partner signals that bear on Eureka requirements. Each record has a readable `.md` file and a machine-readable `.json` twin. A record is bound to a private room by pointer only: it names the room id and the meeting id and nothing else from the room. Every claim is a candidate with `review_status: proposed`. It keeps the knowledge type and confidence that the source gave it. No claim is confirmed by a person.

## Sanitizing rules

- Write claims in plain words. Use roles (the partner, the mentor, the founder), never personal names.
- Do not name third parties or institution contacts. Prefer "the partner organization" and "other universities".
- Do not copy transcript text or room file text. Restate each claim in new words.
- Do not raise a claim above its stated confidence. Do not use "validated" or "verified" as a status.
- Keep the room id and the meeting id as pointers only. Do not copy room content.
- Do not use em-dashes. Use hyphens.
- Output stays labeled "candidate, not verified".
