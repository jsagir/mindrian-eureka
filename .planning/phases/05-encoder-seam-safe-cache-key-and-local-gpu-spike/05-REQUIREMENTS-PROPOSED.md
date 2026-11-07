# Phase 5 proposed requirements (ENC)

**Status:** proposal from the planner, 2026-11-08. Not yet merged into `.planning/REQUIREMENTS.md`. The orchestrator merges it and sets `**Requirements**: ENC-01, ENC-02, ENC-03, ENC-04, ENC-05, ENC-06, ENC-07, ENC-08, ENC-09, ENC-10` in the Phase 5 section of `.planning/ROADMAP.md` (it says `TBD` now).

## Lines for the section "v1 Requirements" of REQUIREMENTS.md

Add after the block "Public example (EXM)":

### Encoder seam (ENC)

- [ ] **ENC-01**: One `EncoderSpec`, one `Encoder` protocol and one `make_encoder` factory build every encoder, with two named profiles (`cpu-default` with MiniLM at 384 dimensions, `gpu-nemotron` as a spike profile); MiniLM stays the default and every default result stays byte-identical.
- [ ] **ENC-02**: The two pair engines (`runner.py`, `run/engines.py`) and `doctor.py` load their encoder through the factory; the build sites that are not routed in this phase are listed with their risk, and `hsi_reference.py` is not edited.
- [ ] **ENC-03**: The embedding cache key holds the full encoder identity (model id, revision, model digest, dimension, dtype, attention, device, prefixes, normalization, chunking, batch size, token cap); the cache schema version is raised so old entries are ignored; a stored vector of the wrong width is rejected on a hit; each profile has its own cache file.
- [ ] **ENC-04**: The run manifest has an `encoder` block with the profile, the determinism class (`cpu-exact` or `gpu-approx`) and an encoder fingerprint for each engine; `eureka check-example` compares a `gpu-approx` run by ranking overlap and not by bytes, and never reports a match while no overlap threshold has been measured.
- [ ] **ENC-05**: Every ranked result carries the label "candidate, not verified" and an encoder fingerprint in a stable field: on each output of the library runner, in the optional `encoder` key of the host run result, and in the manifest; the pair files of a non-default profile also carry the fingerprint.
- [ ] **ENC-06**: `eureka doctor --encoder-profile NAME` adds one encoder check (profile name, libraries, device, model folder, and with `--load-model` the vector width) without changing the `eureka.doctor.v1` shape or any existing check id.
- [ ] **ENC-07**: GPU-related packages live in the optional extra `gpu-encoder`; the core dependencies stay `jsonschema`, `numpy` and `scikit-learn`; `uv.lock` is regenerated in the same commit as `pyproject.toml`.
- [ ] **ENC-08**: A self-contained spike script and a results page let the owner run `nvidia/Nemotron-3-Embed-1B-BF16` on the RTX 3060 in a scratch environment outside the repository; every number on the page comes from the run log; until the owner returns a log, every value is NOT RUN.
- [ ] **ENC-09**: A measured comparison of MiniLM, `mdbr-leaf-ir` and the Nemotron profile on the 36-record public example reports the dense top-200 pair overlap and the texts per second; the CPU part runs on this computer, a column that cannot run is marked NOT RUN with its reason, and the owner decides any change of the default encoder.
- [ ] **ENC-10**: The hand-offs for the MindrianOS plugin session (environment allowlist, request field for the profile, contract version marker, one `vec0` table for each profile, re-tuned 0.55 floor, failure reasons, start stderr, doctor checks that are not added) are written in `docs/encoder-profiles.md` with a source and a mark for each; no plugin checkout is edited.
- [ ] **ENC-11**: The READMEs (README.md, examples/public-example/README.md, src/README.md) are refreshed for the encoder profiles, `--encoder-profile`, `doctor --encoder-profile`, the `gpu-encoder` extra and the `cpu-exact` / `gpu-approx` classes, and every claim is checked against the code and a run (owner rule 2026-11-07).

## Rows for the section "Traceability" of REQUIREMENTS.md

| Requirement | Phase | Status |
|-------------|-------|--------|
| ENC-01 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |
| ENC-02 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |
| ENC-03 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |
| ENC-04 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |
| ENC-05 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |
| ENC-06 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |
| ENC-07 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |
| ENC-08 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending (owner-run spike) |
| ENC-09 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending (CPU part here, GPU part owner-run) |
| ENC-10 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |
| ENC-11 | Phase 5 - Encoder seam, safe cache key and local GPU spike | Pending |

## Coverage line for REQUIREMENTS.md

- v1 requirements: 32 total (21 before, plus 11 ENC)
- Mapped to phases: 32 (Phase 1: 5, Phase 2: 7, Phase 2.1: 5, Phase 3: 2, Phase 4: 2, Phase 5: 11)
- Unmapped: 0

## Which plan cites which requirement

| Plan | Wave | Requirements |
|------|------|--------------|
| 05-01 Encoder spec, factory and gpu-encoder extra | 1 | ENC-01, ENC-07 |
| 05-02 Safe cache key | 1 | ENC-03 |
| 05-03 Runner and doctor through the seam | 2 | ENC-02, ENC-03, ENC-05, ENC-06 |
| 05-04 check-example for non-exact runs | 2 | ENC-04 |
| 05-05 Pipeline profile, manifest encoder block, wording engine | 3 | ENC-02, ENC-03, ENC-04, ENC-05 |
| 05-06 Host result key, profiles page, plugin hand-offs | 4 | ENC-02, ENC-05, ENC-10 |
| 05-07 Comparison harness and CPU run | 4 | ENC-09 |
| 05-08 GPU spike script, results page, owner checkpoint | 4 | ENC-08, ENC-09 |

## Which plan serves which success criterion of the roadmap

| Criterion | Plans |
|-----------|-------|
| 1 One spec and one factory; the two pair engines first; the others listed | 05-01, 05-03, 05-05, 05-06 |
| 2 Cache key holds the full setup; old entries ignored | 05-02, 05-03, 05-05 |
| 3 Default run still gives `Result: MATCH`; full suite green | 05-01 to 05-05 (real-model run in each), full suite in 05-05 |
| 4 Manifest and ranked results carry fingerprint and label; non-CPU compared by overlap | 05-03, 05-04, 05-05, 05-06 |
| 5 Recorded spike with numbers from a run log | 05-08 (prepared; owner-run) |
| 6 Measured comparison on the 36-record example | 05-07 (CPU part), 05-08 (GPU vectors); owner decides the default |
| 7 Close-out: READMEs refreshed and checked against code and a run | 05-09 |
