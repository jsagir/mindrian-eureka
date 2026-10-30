"""Launcher texts written into the bundle by `builder.build_bundle`.

`start.sh` and `start.ps1` run the same sequence on the partner machine: sync the
bundled source from the wheel folder offline, `eureka doctor` (stop on a failure and
show the printed fix), `eureka run`, `eureka hub`, then open the page. `--dry-run`
prints the sequence and executes nothing. The docker pair loads the saved image and
runs the same sequence inside a container with no network. None of the texts makes a
network call. The token `@PYTHON_SERIES@` is replaced by the builder with the Python
series the bundled wheels were built for.
"""

# ruff: noqa: E501  (shell and PowerShell lines are kept whole, so a reader can copy them)

from __future__ import annotations

PYTHON_SERIES = "3.12"

START_SH = r"""#!/usr/bin/env bash
# Eureka partner launcher. Runs doctor, run and hub on this machine. No network call.
# Usage: start.sh [input folder] [output folder] [--dry-run]
set -euo pipefail

BUNDLE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PARENT="$(cd "$BUNDLE/.." && pwd -P)"
DRY_RUN=0
INPUT=""
OUTPUT=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help)
      echo "usage: start.sh [input folder] [output folder] [--dry-run]"
      exit 0
      ;;
    *)
      if [ -z "$INPUT" ]; then INPUT="$arg"; else OUTPUT="$arg"; fi
      ;;
  esac
done
if [ -z "$INPUT" ]; then
  if [ -d "$PARENT/input" ]; then INPUT="$PARENT/input"; else INPUT="$BUNDLE/input"; fi
fi
if [ -z "$OUTPUT" ]; then OUTPUT="$PARENT/output"; fi

export PATH="$BUNDLE:$PATH"
export UV_OFFLINE=1
export UV_NO_PROGRESS=1
export UV_PYTHON="@PYTHON_SERIES@"
export UV_CACHE_DIR="$BUNDLE/.uv-cache"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
if [ -d "$BUNDLE/python" ]; then export UV_PYTHON_INSTALL_DIR="$BUNDLE/python"; fi
if [ -d "$BUNDLE/model" ]; then export MINDRIAN_EUREKA_RS_MODEL_PATH="$BUNDLE/model"; fi

SIDECAR=""
for candidate in "$BUNDLE"/sidecar/*.csv "$BUNDLE"/sidecar/*.json; do
  [ -f "$candidate" ] || continue
  name="$(basename "$candidate")"
  if [ "$name" = "README.md" ] || [ "$name" = "text-sidecar.example.csv" ]; then continue; fi
  SIDECAR="$candidate"
  break
done

MAPPING="$BUNDLE/mapping/technology-audit-export.json"
SYNC=(uv sync --offline --no-index --find-links "$BUNDLE/wheels" --extra modern-encoder --extra hub-gate)
if [ ! -d "$BUNDLE/wheels" ]; then
  echo "No wheels folder. The sync uses a cache on this machine, if one exists."
  SYNC=(uv sync --offline --extra modern-encoder --extra hub-gate)
fi
DOCTOR=(uv run --offline eureka doctor)
RUN=(uv run --offline eureka run "$INPUT" --out "$OUTPUT" --mapping "$MAPPING")
if [ -n "$SIDECAR" ]; then RUN+=(--text-sidecar "$SIDECAR"); fi
HUB=(uv run --offline eureka hub "$OUTPUT" --out "$OUTPUT-hub")
PAGE="$OUTPUT-hub/hub.html"

if [ "$DRY_RUN" = "1" ]; then
  echo "would run: cd $BUNDLE/source && ${SYNC[*]}"
  echo "would run: ${DOCTOR[*]}"
  echo "would run: ${RUN[*]}"
  echo "would run: ${HUB[*]}"
  echo "would run: open $PAGE"
  exit 0
fi

if [ ! -d "$INPUT" ]; then
  echo "Input folder not found: $INPUT"
  echo "Put the export CSV in a folder named input next to the bundle, or pass the folder as the first argument."
  exit 1
fi

cd "$BUNDLE/source"
echo "step 1: ${SYNC[*]}"
"${SYNC[@]}"
echo "step 2: ${DOCTOR[*]}"
if ! "${DOCTOR[@]}"; then
  echo "Doctor found a problem. Read the fix above, then run start.sh again."
  exit 1
fi
echo "step 3: ${RUN[*]}"
"${RUN[@]}"
echo "step 4: ${HUB[*]}"
"${HUB[@]}"
echo "step 5: open $PAGE"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$PAGE" >/dev/null 2>&1 || echo "Open this page in a browser: $PAGE"
elif command -v open >/dev/null 2>&1; then
  open "$PAGE" || echo "Open this page in a browser: $PAGE"
else
  echo "Open this page in a browser: $PAGE"
fi
"""

START_PS1 = r"""# Eureka partner launcher. Runs doctor, run and hub on this machine. No network call.
# Usage: start.ps1 [-InputDir <folder>] [-OutputDir <folder>] [-DryRun]
param(
  [string]$InputDir = "",
  [string]$OutputDir = "",
  [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$Bundle = Split-Path -Parent $MyInvocation.MyCommand.Path
$Parent = Split-Path -Parent $Bundle
if ($InputDir -eq "") {
  if (Test-Path "$Parent\input") { $InputDir = "$Parent\input" } else { $InputDir = "$Bundle\input" }
}
if ($OutputDir -eq "") { $OutputDir = "$Parent\output" }

$env:PATH = "$Bundle;$env:PATH"
$env:UV_OFFLINE = "1"
$env:UV_NO_PROGRESS = "1"
$env:UV_PYTHON = "@PYTHON_SERIES@"
$env:UV_CACHE_DIR = "$Bundle\.uv-cache"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
if (Test-Path "$Bundle\python") { $env:UV_PYTHON_INSTALL_DIR = "$Bundle\python" }
if (Test-Path "$Bundle\model") { $env:MINDRIAN_EUREKA_RS_MODEL_PATH = "$Bundle\model" }

$Uv = "$Bundle\uv.exe"
$Mapping = "$Bundle\mapping\technology-audit-export.json"
$Sidecar = ""
$Skip = @("README.md", "text-sidecar.example.csv")
$Files = Get-ChildItem -Path "$Bundle\sidecar" -File | Where-Object { $_.Extension -in ".csv", ".json" }
foreach ($File in ($Files | Sort-Object Name)) {
  if ($Skip -contains $File.Name) { continue }
  $Sidecar = $File.FullName
  break
}

$Sync = "sync --offline --no-index --find-links $Bundle\wheels --extra modern-encoder --extra hub-gate"
if (-not (Test-Path "$Bundle\wheels")) {
  Write-Output "No wheels folder. The sync uses a cache on this machine, if one exists."
  $Sync = "sync --offline --extra modern-encoder --extra hub-gate"
}
$SidecarArgs = @()
if ($Sidecar -ne "") { $SidecarArgs = @("--text-sidecar", $Sidecar) }
$SidecarText = ""
if ($Sidecar -ne "") { $SidecarText = " --text-sidecar $Sidecar" }
$Page = "$OutputDir-hub\hub.html"

if ($DryRun) {
  Write-Output "would run: Set-Location $Bundle\source; uv $Sync"
  Write-Output "would run: uv run --offline eureka doctor"
  Write-Output "would run: uv run --offline eureka run $InputDir --out $OutputDir --mapping $Mapping$SidecarText"
  Write-Output "would run: uv run --offline eureka hub $OutputDir --out $OutputDir-hub"
  Write-Output "would run: Start-Process $Page"
  exit 0
}

if (-not (Test-Path $InputDir)) {
  Write-Output "Input folder not found: $InputDir"
  Write-Output "Put the export CSV in a folder named input next to the bundle, or pass -InputDir."
  exit 1
}

Set-Location "$Bundle\source"
Write-Output "step 1: uv $Sync"
& $Uv $Sync.Split(" ")
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Output "step 2: uv run --offline eureka doctor"
& $Uv run --offline eureka doctor
if ($LASTEXITCODE -ne 0) {
  Write-Output "Doctor found a problem. Read the fix above, then run start.ps1 again."
  exit 1
}
Write-Output "step 3: uv run --offline eureka run $InputDir --out $OutputDir --mapping $Mapping$SidecarText"
& $Uv run --offline eureka run $InputDir --out $OutputDir --mapping $Mapping @SidecarArgs
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Output "step 4: uv run --offline eureka hub $OutputDir --out $OutputDir-hub"
& $Uv run --offline eureka hub $OutputDir --out "$OutputDir-hub"
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Output "step 5: Start-Process $Page"
Start-Process $Page
"""

START_DOCKER_SH = r"""#!/usr/bin/env bash
# Eureka partner launcher, docker variant. Loads the saved image and runs it with no network.
# Usage: start-docker.sh [input folder] [output folder] [--dry-run]
set -euo pipefail

BUNDLE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PARENT="$(cd "$BUNDLE/.." && pwd -P)"
DRY_RUN=0
INPUT=""
OUTPUT=""
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help)
      echo "usage: start-docker.sh [input folder] [output folder] [--dry-run]"
      exit 0
      ;;
    *)
      if [ -z "$INPUT" ]; then INPUT="$arg"; else OUTPUT="$arg"; fi
      ;;
  esac
done
if [ -z "$INPUT" ]; then
  if [ -d "$PARENT/input" ]; then INPUT="$PARENT/input"; else INPUT="$BUNDLE/input"; fi
fi
if [ -z "$OUTPUT" ]; then OUTPUT="$PARENT/output"; fi

IMAGE="$(sed -n 's/.*"docker_image": "\([^"]*\)".*/\1/p' "$BUNDLE/BUNDLE-MANIFEST.json" | head -n 1)"
IMAGE="${IMAGE:-mindrian-eureka:local}"

SIDECAR=""
for candidate in "$BUNDLE"/sidecar/*.csv "$BUNDLE"/sidecar/*.json; do
  [ -f "$candidate" ] || continue
  name="$(basename "$candidate")"
  if [ "$name" = "README.md" ] || [ "$name" = "text-sidecar.example.csv" ]; then continue; fi
  SIDECAR="$candidate"
  break
done

LOAD=(docker load -i "$BUNDLE/eureka-image.tar")
DOCKER=(docker run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges)
DOCKER+=(--tmpfs /tmp:rw,noexec,nosuid,size=1g)
DOCKER+=(-v "$INPUT:/data/input:ro" -v "$OUTPUT:/data/output" -v "$BUNDLE/model:/models:ro")
DOCKER+=(-v "$BUNDLE/mapping:/data/mapping:ro")
if [ -n "$SIDECAR" ]; then DOCKER+=(-v "$BUNDLE/sidecar:/data/sidecar:ro"); fi
DOCKER+=(-e MINDRIAN_EUREKA_RS_MODEL_PATH=/models -e HF_HUB_OFFLINE=1 -e TRANSFORMERS_OFFLINE=1)
DOCTOR=("${DOCKER[@]}" "$IMAGE" eureka doctor)
RUN=("${DOCKER[@]}" "$IMAGE" eureka run /data/input --out /data/output/run --mapping /data/mapping/technology-audit-export.json)
if [ -n "$SIDECAR" ]; then RUN+=(--text-sidecar "/data/sidecar/$(basename "$SIDECAR")"); fi
HUB=("${DOCKER[@]}" "$IMAGE" eureka hub /data/output/run --out /data/output/hub)
PAGE="$OUTPUT/hub/hub.html"

if [ "$DRY_RUN" = "1" ]; then
  echo "would run: ${LOAD[*]}"
  echo "would run: ${DOCTOR[*]}"
  echo "would run: ${RUN[*]}"
  echo "would run: ${HUB[*]}"
  echo "would run: open $PAGE"
  exit 0
fi

if [ ! -d "$INPUT" ]; then
  echo "Input folder not found: $INPUT"
  exit 1
fi
mkdir -p "$OUTPUT"
echo "step 1: ${LOAD[*]}"
"${LOAD[@]}"
echo "step 2: ${DOCTOR[*]}"
if ! "${DOCTOR[@]}"; then
  echo "Doctor found a problem. Read the fix above, then run start-docker.sh again."
  exit 1
fi
echo "step 3: ${RUN[*]}"
"${RUN[@]}"
echo "step 4: ${HUB[*]}"
"${HUB[@]}"
echo "step 5: open $PAGE"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$PAGE" >/dev/null 2>&1 || echo "Open this page in a browser: $PAGE"
elif command -v open >/dev/null 2>&1; then
  open "$PAGE" || echo "Open this page in a browser: $PAGE"
else
  echo "Open this page in a browser: $PAGE"
fi
"""

START_DOCKER_PS1 = r"""# Eureka partner launcher, docker variant. Loads the saved image and runs it with no network.
# Usage: start-docker.ps1 [-InputDir <folder>] [-OutputDir <folder>] [-DryRun]
param(
  [string]$InputDir = "",
  [string]$OutputDir = "",
  [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$Bundle = Split-Path -Parent $MyInvocation.MyCommand.Path
$Parent = Split-Path -Parent $Bundle
if ($InputDir -eq "") {
  if (Test-Path "$Parent\input") { $InputDir = "$Parent\input" } else { $InputDir = "$Bundle\input" }
}
if ($OutputDir -eq "") { $OutputDir = "$Parent\output" }

$Manifest = Get-Content "$Bundle\BUNDLE-MANIFEST.json" -Raw | ConvertFrom-Json
$Image = $Manifest.builder.docker_image
if (-not $Image) { $Image = "mindrian-eureka:local" }

$Sidecar = ""
$Skip = @("README.md", "text-sidecar.example.csv")
$Files = Get-ChildItem -Path "$Bundle\sidecar" -File | Where-Object { $_.Extension -in ".csv", ".json" }
foreach ($File in ($Files | Sort-Object Name)) {
  if ($Skip -contains $File.Name) { continue }
  $Sidecar = $File.Name
  break
}

$Flags = "run --rm --network none --read-only --cap-drop ALL --security-opt no-new-privileges".Split(" ")
$Flags += @("--tmpfs", "/tmp:rw,noexec,nosuid,size=1g")
$Flags += @("-v", "${InputDir}:/data/input:ro", "-v", "${OutputDir}:/data/output", "-v", "$Bundle\model:/models:ro")
$Flags += @("-v", "$Bundle\mapping:/data/mapping:ro")
if ($Sidecar -ne "") { $Flags += @("-v", "$Bundle\sidecar:/data/sidecar:ro") }
$Flags += @("-e", "MINDRIAN_EUREKA_RS_MODEL_PATH=/models", "-e", "HF_HUB_OFFLINE=1", "-e", "TRANSFORMERS_OFFLINE=1")
$SidecarArgs = @()
$SidecarText = ""
if ($Sidecar -ne "") {
  $SidecarArgs = @("--text-sidecar", "/data/sidecar/$Sidecar")
  $SidecarText = " --text-sidecar /data/sidecar/$Sidecar"
}
$FlagText = $Flags -join " "
$Page = "$OutputDir\hub\hub.html"

if ($DryRun) {
  Write-Output "would run: docker load -i $Bundle\eureka-image.tar"
  Write-Output "would run: docker $FlagText $Image eureka doctor"
  Write-Output "would run: docker $FlagText $Image eureka run /data/input --out /data/output/run --mapping /data/mapping/technology-audit-export.json$SidecarText"
  Write-Output "would run: docker $FlagText $Image eureka hub /data/output/run --out /data/output/hub"
  Write-Output "would run: Start-Process $Page"
  exit 0
}

if (-not (Test-Path $InputDir)) {
  Write-Output "Input folder not found: $InputDir"
  exit 1
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
Write-Output "step 1: docker load -i $Bundle\eureka-image.tar"
& docker load -i "$Bundle\eureka-image.tar"
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Output "step 2: docker $FlagText $Image eureka doctor"
& docker @Flags $Image eureka doctor
if ($LASTEXITCODE -ne 0) {
  Write-Output "Doctor found a problem. Read the fix above, then run start-docker.ps1 again."
  exit 1
}
Write-Output "step 3: docker $FlagText $Image eureka run"
& docker @Flags $Image eureka run /data/input --out /data/output/run --mapping /data/mapping/technology-audit-export.json @SidecarArgs
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Output "step 4: docker $FlagText $Image eureka hub"
& docker @Flags $Image eureka hub /data/output/run --out /data/output/hub
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Output "step 5: Start-Process $Page"
Start-Process $Page
"""

SIDECAR_README = """# Side-car text

A side-car file adds text to records whose own text is thin.
The launcher passes the first CSV or JSON file in this folder to the run.
CSV format: the first column is the record id, and a column named `text` holds the text.
JSON format: one object whose keys are record ids and whose values are the text.
The example `text-sidecar.example.csv` shows the CSV layout; the launcher skips it.
Only records whose own text is under the thin limit get side-car text, added after their own text.
Own text is never replaced.
Drop the side-car file for this export here, next to the example, before the first run.
The file never leaves this machine; the run records its sha256 only.
"""
