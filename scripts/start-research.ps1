param([string]$Distro = 'Ubuntu-24.04', [switch]$SmokeTest)
$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'start-ollama-windows.ps1') -Distro $Distro
$evaluation = Join-Path (Split-Path $PSScriptRoot -Parent | Split-Path -Parent) 'rosa-evaluation'
$linuxEvaluation = (& wsl.exe -d $Distro --exec wslpath -u $evaluation.Replace('\', '/') | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Could not resolve the evaluation checkout in WSL.' }
& wsl.exe -d $Distro --cd $linuxEvaluation --exec bash scripts/phoenix-service.sh start
if ($LASTEXITCODE -ne 0) { throw 'Phoenix failed to start.' }
Write-Host 'Research services ready. Phoenix: http://localhost:6006'
if ($SmokeTest) {
    & wsl.exe -d $Distro --cd $linuxEvaluation --exec bash run.sh research --probe-qwen
    if ($LASTEXITCODE -ne 0) { throw 'Qwen readiness smoke test failed. Inspect its result.json report.' }
}
