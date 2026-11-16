#!/usr/bin/env bash
# One-step Eureka setup for MindrianOS (macOS / Linux).
#   curl -fsSL https://raw.githubusercontent.com/jsagir/mindrian-eureka/main/scripts/setup-mindrianos.sh | bash
# Safe to run again: it updates what is there and skips what is done.
# Last line is always: EUREKA_SETUP: OK  or  EUREKA_SETUP: FAIL <step> <reason>
set -uo pipefail
REPO="https://github.com/jsagir/mindrian-eureka.git"
ENGINE="${MINDRIAN_EUREKA_ROOT:-$HOME/.mindrian/eureka-engine}"
MODEL_ID="sentence-transformers/all-MiniLM-L6-v2"
step(){ printf '\n== %s\n' "$*"; }
fail(){ echo "EUREKA_SETUP: FAIL $1 $2"; exit 1; }

step "1/6 tools"
command -v git >/dev/null || fail tools "git is missing; install git, then run again"
if ! command -v uv >/dev/null; then
  echo "uv missing - installing it with the official astral.sh installer"
  curl -LsSf https://astral.sh/uv/install.sh | sh || fail tools "uv install failed"
  export PATH="$HOME/.local/bin:$PATH"
fi
uv --version
if command -v node >/dev/null; then
  NV=$(node -p 'process.versions.node.split(".")[0]')
  [ "$NV" -ge 22 ] && echo "node $(node --version) ok" || echo "WARN node $NV found; MindrianOS and some Eureka workers need Node 22+"
else echo "WARN node not found; MindrianOS needs Node 22+"; fi

step "2/6 engine code -> $ENGINE"
mkdir -p "$(dirname "$ENGINE")"
if [ -d "$ENGINE/.git" ]; then
  git -C "$ENGINE" pull --ff-only -q || echo "WARN could not fast-forward $ENGINE; keeping the current copy"
else
  git clone -q "$REPO" "$ENGINE" || fail engine "git clone failed (network?)"
fi
echo "engine commit $(git -C "$ENGINE" rev-parse --short HEAD)"

step "3/6 python packages (network, one time)"
uv sync -q --python 3.12 --project "$ENGINE" --extra mcp-server --extra modern-encoder || fail packages "uv sync failed (network or proxy?)"

step "4/6 meaning model ($MODEL_ID)"
SNAP=$(uv run -q --project "$ENGINE" --no-sync python -c "from huggingface_hub import snapshot_download as s; print(s('sentence-transformers/all-MiniLM-L6-v2', ignore_patterns=['onnx/*','openvino/*','*.bin','*.h5','*.msgpack','*.ot','tf_model*','rust_model*']))" 2>/dev/null | tail -1)
[ -d "$SNAP" ] || fail model "model download failed (network or proxy?)"
echo "model at $SNAP"
for RC in "$HOME/.zshrc" "$HOME/.bashrc"; do
  [ -f "$RC" ] || continue
  sed -i.bak '/MINDRIAN_EUREKA_RS_MODEL_PATH/d' "$RC" 2>/dev/null || true
  echo "export MINDRIAN_EUREKA_RS_MODEL_PATH=\"$SNAP\"" >> "$RC"
done
export MINDRIAN_EUREKA_RS_MODEL_PATH="$SNAP"

step "5/6 health check"
uv run --project "$ENGINE" --no-sync --offline eureka doctor --load-model || fail doctor "eureka doctor reported a FAIL (see above)"

step "6/6 connect to MindrianOS"
ENABLE=$(ls -d "$HOME"/.claude/plugins/cache/*/mos/*/lib/core/eureka/eureka-engine-enable.cjs 2>/dev/null | sort -V | tail -1)
if [ -z "$ENABLE" ]; then
  echo "WARN MindrianOS plugin not found under ~/.claude/plugins; install it, then run: /mos:eureka enable engine --path $ENGINE"
  echo "EUREKA_SETUP: OK engine-only $ENGINE"; exit 0
fi
node "$ENABLE" --path "$ENGINE" >/dev/null || fail connect "saving the engine folder in MindrianOS failed"
node "$ENABLE" --check | tail -12
echo "EUREKA_SETUP: OK $ENGINE"
