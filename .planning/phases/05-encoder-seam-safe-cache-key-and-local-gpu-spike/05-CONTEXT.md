# Phase 5: Encoder seam, safe cache key and local GPU spike - Context

**Gathered:** 2026-11-07
**Status:** Ready for planning
**Source:** owner answers of 2026-11-07, `.planning/ROADMAP.md` Phase 5, and `05-RESEARCH.md` (AI-generated fan-out research; claims carry PROVEN, INFERRED or UNVERIFIED; the skeptic stage refuted several lane claims, listed in 05-RESEARCH.md under Critic conflicts; do not rely on a refuted claim)

<domain>
## Phase Boundary

Eureka builds each text encoder in one place, never reuses a vector made by a different encoder setup, and can run one named local GPU encoder on the owner's own computer. MiniLM stays the default. Every default result stays byte-identical to today.

In scope: an `EncoderSpec`, an `Encoder` protocol and `make_encoder`; routing the two pair engines through it first; a cache key and a schema version that hold the full encoder identity; a dimension check on cache hit; an encoder block and a determinism class in the manifest; `check-example` behavior for non-CPU runs; a stable "candidate, not verified" field and an encoder fingerprint on ranked results; a doctor encoder probe; a recorded spike of Nemotron-3-Embed-1B-BF16 on the owner's RTX 3060; a measured comparison on the 36-record public example.

Out of scope: any socket or loopback HTTP encoder client; NIM; Cloudflare Tunnel or any shared host; an ontology or taxonomy layer; changing the default encoder; editing `src/mindrian_eureka/hsi_reference.py` (its sha256 is recorded in manifests); any edit in the MindrianOS plugin checkouts (hand-offs only); GGUF or NVFP4 weights; a push.
</domain>

<decisions>
## Locked decisions (owner, 2026-11-07)

- D-01 In-process on the user's own computer for now. Local NIM stays a later option the owner wants to keep; it is not designed or built in this phase.
- D-02 The topic taxonomy idea (OpenAlex Topics as a soft signal) is parked for a later phase. No work here.
- D-03 The first model comparison uses the 36-record public example only. The JHTV corpus is not used until the owner says so.
- D-04 MiniLM (all-MiniLM-L6-v2) stays the default. A change of default is the owner's decision after the measured comparison, never inside this phase.

## Planner decisions (the owner may overrule any before execution)

- D-05 One `EncoderSpec` carries: model id, revision, dimension, dtype, device, query prefix, document prefix, normalize flag, chunk setting, batch size. The cache key holds the spec identity. Bump the cache `SCHEMA_VERSION`; old entries are ignored, not misread.
- D-06 At least seven places build a `SentenceTransformer` today (PROVEN by the research, file:line in 05-RESEARCH.md): runner.py, run/engines.py, hsi_engine.py, analogy_fitness.py, hsi_reference.py, pitch_analysis/algorithm.py, doctor.py. The plan routes the two pair engines (runner.py, run/engines.py) and doctor.py first. `hsi_reference.py` is not edited. The remaining sites are listed as follow-ups with their risk; the plan says which of them it covers.
- D-07 Named encoder profiles, never mixed in one store: `cpu-default` (MiniLM, 384 dimensions) and `gpu-nemotron` (a spike profile). Each profile has its own cache namespace; a room store vector table width must match the profile dimension.
- D-08 Determinism classes: `cpu-exact` keeps the byte check of `check-example`; `gpu-approx` is compared by ranking overlap with a threshold that the spike measures. The manifest records the class.
- D-09 Keep stable for the MindrianOS plugin: the `eureka-mcp` script and name, the registered tool names (27 today), the `eureka.doctor.v1` shape and existing check ids, the failure reasons (a missing model still surfaces as `local_model_unavailable`), and a `uv.lock` in sync with `pyproject.toml` (the plugin starts with `uv run --no-sync --offline --locked --no-python-downloads eureka-mcp`). A healthy `eureka-mcp` start writes nothing to stderr (tests/test_mcp_start_stderr.py pins this). Any new dependency or extra changes `uv.lock` in the same commit; core dependencies stay exactly `jsonschema`, `numpy`, `scikit-learn` (tests/test_hub_assets.py pins them), so GPU-related packages go in an optional extra.
- D-10 A new device or backend setting reaches the engine only through a request field or a config file, not a new environment variable, because the plugin passes an allowlisted environment. If an environment variable is wanted, the plan lists it as a hand-off to the plugin session.
- D-11 The spike runs in a scratch virtual environment outside the repo on the owner's RTX 3060 machine (Windows/WSL). Its result is a recorded note with numbers from a run log. If the machine is not reachable from this session, the spike task ends as a prepared script plus `NEEDS_HUMAN`, never as an invented number.
- D-12 Honest labels: every ranked result keeps "candidate, not verified". Every number in a plan or doc has a source.
</decisions>

<canonical_refs>
## Canonical references

- `.planning/phases/05-encoder-seam-safe-cache-key-and-local-gpu-spike/05-RESEARCH.md` (evidence, critic gaps, refuted claims, lane digest)
- `.planning/ROADMAP.md` Phase 5 (goal, six success criteria, scope notes)
- `docs/research/mindrian-eureka-local-nim-hosting.md` (owner-saved research; Option B tunnel conflicts with the privacy rule; NIM on a GeForce 3060 is not supported)
- `docs/mos-eureka-engine-run-contract.md` and the plugin facts in `.planning/phases/03-host-integration-and-replay-rebuild/03-CONTEXT.md` (F9, F14, F15)
- `docs/rs-release-gate.md`, `examples/public-example/expected-hashes.json`, `tests/test_public_example.py`, `tests/test_run_engines.py`, `tests/test_embedding_cache.py` (if present), `tests/test_rs_engine_parity.py`
- Code: `src/mindrian_eureka/opportunity_pairs/encoders.py`, `opportunity_pairs/cache.py`, `opportunity_pairs/runner.py`, `run/engines.py`, `run/pipeline.py`, `run/manifest.py`, `example/check.py`, `doctor.py`, `models.py`
</canonical_refs>

<verified_facts>
## Facts checked on 2026-11-07

| Id | Fact | Status |
|----|------|--------|
| F1 | Full suite: 1735 passed, 29 skipped, 0 failed. ruff src tests 1465 errors; mypy src 88 errors in 17 files. | PROVEN (run) |
| F2 | The machine is aarch64 Linux, 12 cores, 17 GB RAM, no GPU; MiniLM reference runs on 36 records take about 15 s at 0.82 GB; four output files are byte-identical across 1 and 12 threads, cache and no cache, and a system Python run. | PROVEN (run) |
| F3 | The owner's RTX 3060 12 GB is on a Windows/WSL machine, not this one. | owner statement |
| F4 | The plugin reads these engine facts: project name `mindrian-eureka`, script `eureka-mcp`, five hard-coded scout tool names, doctor JSON `eureka.doctor.v1`. | PROVEN in research lanes, file:line in 05-RESEARCH.md |
| F5 | Nemotron-3-Embed-1B-BF16: about 1.14B parameters, 2048 dimensions, 32k context, mean pooling, `query:`/`passage:` prefixes, OpenMDW-1.1 license, needs sentence-transformers 5.4.1 or newer and transformers 5.2 or newer (Eureka pins sentence-transformers >=5.0,<6). Whether it loads through Eureka's class is UNVERIFIED. | model card, UNVERIFIED on this stack |
</verified_facts>
</context>
