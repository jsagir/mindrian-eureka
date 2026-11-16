---
name: mindrian-eureka-setup
description: Set up the Eureka engine for MindrianOS in one step - installs the engine code, its Python packages and its meaning model, checks it, and connects it to the MindrianOS plugin. Use when the user says "set up Eureka", "install Eureka", "enable the Eureka engine", "connect Eureka to MindrianOS", or when a /mos:eureka tool answers engine_absent, engine_model_missing or engine_extra_missing.
---

# Eureka setup for MindrianOS (one step)

The user invoking this skill is their approval to run the whole setup. Do not ask questions
before starting. Say in one line what will happen, then run it.

One line to say first:
"Setting up Eureka: I'll get the engine code from GitHub, install its Python packages and its
meaning model (a one-time download), check it and connect it to MindrianOS. Nothing from your
rooms leaves this machine."

## Step 1 - Run the setup script

Pick the line for the user's system (check with `uname` or the platform in your environment).
Run it with a long timeout (up to 10 minutes); the first run downloads packages and the model.

macOS / Linux:
```bash
curl -fsSL https://raw.githubusercontent.com/jsagir/mindrian-eureka/main/scripts/setup-mindrianos.sh | bash
```

Windows (PowerShell):
```powershell
irm https://raw.githubusercontent.com/jsagir/mindrian-eureka/main/scripts/setup-mindrianos.ps1 | iex
```

The script is safe to run again. It installs `uv` if it is missing, clones or updates the engine
in `~/.mindrian/eureka-engine`, runs `uv sync` with the `mcp-server` and `modern-encoder` extras,
downloads `sentence-transformers/all-MiniLM-L6-v2` into the Hugging Face cache, saves
`MINDRIAN_EUREKA_RS_MODEL_PATH`, runs `eureka doctor --load-model`, and saves the engine folder in
the MindrianOS plugin (`~/.mindrian/eureka-engine.json`), then prints the plugin's own check.

## Step 2 - Read the last line

The last line is always one of:

| Last line | Meaning | What you do |
|-----------|---------|-------------|
| `EUREKA_SETUP: OK <folder>` | Done and connected | Go to Step 3 |
| `EUREKA_SETUP: OK engine-only <folder>` | Engine works; the MindrianOS plugin was not found | Tell the user to install MindrianOS (https://mindrian-os.com), then run `/mos:eureka enable engine --path <folder>` |
| `EUREKA_SETUP: FAIL tools ...` | git missing, or uv could not install | Give the exact install step for git or uv, then rerun Step 1 |
| `EUREKA_SETUP: FAIL engine ...` or `packages ...` or `model ...` | Network blocked (often a company proxy) | Say so plainly; suggest another network (a phone hotspot) and rerun Step 1 |
| `EUREKA_SETUP: FAIL doctor ...` | The engine check failed | Quote the FAIL lines from the doctor output and their printed Fix line; apply the fix; rerun Step 1 |
| `EUREKA_SETUP: FAIL connect ...` | Saving into MindrianOS failed | Run `/mos:eureka enable engine --path ~/.mindrian/eureka-engine` |

A `WARN` line about Node or about the offline variables does not block. One `[WARN] D7 Offline
variables` in the doctor output is normal.

## Step 3 - Report and hand over

Report in 3 to 5 plain lines:
- the engine folder and its commit,
- the doctor result (passed / warnings / failed counts),
- the route families from the plugin check (`graph`, `pairs-and-scout`, `node-workers`, `decision`),
- one next step: "Try it in your room with `/mos:eureka`."

`decision: needs_extra (needs hmm)` is expected. That route needs a compiler and is optional; offer
`/mos:eureka enable engine --sync --extras hmm` only if the user asks for decision sequences.

If Claude Desktop is used instead of the terminal, tell the user to fully quit and reopen it once
so it picks up the saved model path.

## Rules

- Claim only what the script output shows. Never report success without the `EUREKA_SETUP: OK` line.
- Never print or move room content; this setup touches no room.
- Do not edit the script output or skip the doctor step.
