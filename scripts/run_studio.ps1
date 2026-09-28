# Explainer Studio 를 Windows PC 브라우저에서 연다.
# 사용:  repo 루트에서  powershell -ExecutionPolicy Bypass -File .\scripts\run_studio.ps1
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if (-not (Test-Path ".venv")) {
  Write-Host "[setup] Python venv 생성…"
  python -m venv .venv
  & .\.venv\Scripts\Activate.ps1
  python -m pip install -U pip
  pip install -e ".[dev]"
} else {
  & .\.venv\Scripts\Activate.ps1
}

$Port = if ($env:PORT) { $env:PORT } else { "8765" }
$HostBind = if ($env:HOST) { $env:HOST } else { "0.0.0.0" }
Write-Host ""
Write-Host "  Explainer Studio → http://localhost:$Port/"
Write-Host "  (종료: Ctrl+C)"
Write-Host ""
python -m explainer studio --host $HostBind --port $Port --root $Root
