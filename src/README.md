# Source folder

This folder holds the Python package `mindrian_eureka`. It is the engine behind the `eureka` command and the `eureka-mcp` server.

The package has these parts:

- `run/` and `example/`: the one-command run (`eureka run`) and the check of the public example (`eureka check-example`).
- `opportunity_pairs/`: the unusual-pairs engine, the wording-and-meaning engine, the job store and the MCP server.
- `host_run/`: the plan, the approval receipt and the start of the pair screen run that a connected host calls.
- `encoder_spec.py` and `opportunity_pairs/encoders.py`: the encoder profiles `cpu-default` and `gpu-nemotron`, the fingerprint of an encoder setup, and the one place that builds an encoder. The profile `gpu-nemotron` is a spike profile and is unproven. `doctor.py` checks a profile with `eureka doctor --encoder-profile NAME`.
- `hub/` and `seed/`: the local hub page and the room seed folder, both built from a finished run.
- `partner_bundle/`: the builder of the carry-in folder for a partner machine.
- `graph_relations/`, `structure_mapping/`, `decision_patterns/` and `pitch_analysis/`: the other engines.
- `provenance/`: records of results that cannot be rebuilt from this repository.
- `data/`: the capability catalog, the published schemas and the bundled scripts.

For the commands, see the [main README](../README.md). Every result is a candidate, not verified.
