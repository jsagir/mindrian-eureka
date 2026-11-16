# One-step Eureka setup for MindrianOS (Windows PowerShell).
#   irm https://raw.githubusercontent.com/jsagir/mindrian-eureka/main/scripts/setup-mindrianos.ps1 | iex
# Safe to run again. Last line is always: EUREKA_SETUP: OK  or  EUREKA_SETUP: FAIL <step> <reason>
$Repo = "https://github.com/jsagir/mindrian-eureka.git"
$Engine = if ($env:MINDRIAN_EUREKA_ROOT) { $env:MINDRIAN_EUREKA_ROOT } else { Join-Path $HOME ".mindrian\eureka-engine" }
$ModelId = "sentence-transformers/all-MiniLM-L6-v2"
function Fail($s, $r) { Write-Host "EUREKA_SETUP: FAIL $s $r"; exit 1 }

Write-Host "`n== 1/6 tools"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail "tools" "git is missing; install Git for Windows, then run again" }
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
  Write-Host "uv missing - installing it with the official astral.sh installer"
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  $env:Path = "$HOME\.local\bin;$env:Path"
  if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { Fail "tools" "uv install failed" }
}
uv --version
if (Get-Command node -ErrorAction SilentlyContinue) { node --version } else { Write-Host "WARN node not found; MindrianOS needs Node 22+" }

Write-Host "`n== 2/6 engine code -> $Engine"
New-Item -ItemType Directory -Force (Split-Path $Engine) | Out-Null
if (Test-Path (Join-Path $Engine ".git")) { git -C $Engine pull --ff-only -q }
else { git clone -q $Repo $Engine; if ($LASTEXITCODE -ne 0) { Fail "engine" "git clone failed (network?)" } }

Write-Host "`n== 3/6 python packages (network, one time)"
uv sync -q --project $Engine --extra mcp-server --extra modern-encoder
if ($LASTEXITCODE -ne 0) { Fail "packages" "uv sync failed (network or proxy?)" }

Write-Host "`n== 4/6 meaning model ($ModelId)"
$Py = "from huggingface_hub import snapshot_download as s; print(s('sentence-transformers/all-MiniLM-L6-v2', ignore_patterns=['onnx/*','openvino/*','*.bin','*.h5','*.msgpack','*.ot','tf_model*','rust_model*']))"
$Snap = (uv run -q --project $Engine --no-sync python -c $Py 2>$null | Select-Object -Last 1)
if (-not $Snap -or -not (Test-Path $Snap)) { Fail "model" "model download failed (network or proxy?)" }
[Environment]::SetEnvironmentVariable("MINDRIAN_EUREKA_RS_MODEL_PATH", $Snap, "User")
$env:MINDRIAN_EUREKA_RS_MODEL_PATH = $Snap
Write-Host "model at $Snap"

Write-Host "`n== 5/6 health check"
uv run --project $Engine --no-sync --offline eureka doctor --load-model
if ($LASTEXITCODE -ne 0) { Fail "doctor" "eureka doctor reported a FAIL (see above)" }

Write-Host "`n== 6/6 connect to MindrianOS"
$Enable = Get-ChildItem -Path (Join-Path $HOME ".claude\plugins\cache\*\mos\*\lib\core\eureka\eureka-engine-enable.cjs") -ErrorAction SilentlyContinue |
  Sort-Object { [version](($_.FullName -split '\\mos\\')[1].Split('\')[0] -replace '-beta\.', '.') } | Select-Object -Last 1
if (-not $Enable) {
  Write-Host "WARN MindrianOS plugin not found; install it, then run: /mos:eureka enable engine --path $Engine"
  Write-Host "EUREKA_SETUP: OK engine-only $Engine"; exit 0
}
node $Enable.FullName --path $Engine | Out-Null
if ($LASTEXITCODE -ne 0) { Fail "connect" "saving the engine folder in MindrianOS failed" }
node $Enable.FullName --check | Select-Object -Last 12
Write-Host "EUREKA_SETUP: OK $Engine"
