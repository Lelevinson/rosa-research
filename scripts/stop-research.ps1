param([string]$Distro = 'Ubuntu-24.04')
$ErrorActionPreference = 'Stop'
$evaluation = Join-Path (Split-Path $PSScriptRoot -Parent | Split-Path -Parent) 'rosa-evaluation'
$linuxEvaluation = (& wsl.exe -d $Distro --exec wslpath -u $evaluation.Replace('\', '/') | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Could not resolve the evaluation checkout in WSL.' }
& wsl.exe -d $Distro --cd $linuxEvaluation --exec bash scripts/phoenix-service.sh stop
if ($LASTEXITCODE -ne 0) { throw 'Phoenix failed to stop.' }
$recordPath = Join-Path $evaluation '.local\ollama\process.json'
if (Test-Path -LiteralPath $recordPath) {
    $record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json
    $ownedProcess = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
    if ($ownedProcess -and $ownedProcess.Path -eq $record.executable) { Stop-Process -Id $ownedProcess.Id }
    Remove-Item -LiteralPath $recordPath
}
Write-Host 'Research services stopped. Models, results, and Phoenix data are retained.'
