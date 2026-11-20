param([string]$Distro = 'Ubuntu-24.04', [string]$OllamaPath)
$ErrorActionPreference = 'Stop'
$evaluation = Join-Path (Split-Path $PSScriptRoot -Parent | Split-Path -Parent) 'rosa-evaluation'
$state = Join-Path $evaluation '.local\ollama'
New-Item -ItemType Directory -Path $state -Force | Out-Null
if (!$OllamaPath) {
    $localBinary = Join-Path (Split-Path $evaluation -Parent) '.local\ollama-0.40.6\ollama.exe'
    if (Test-Path -LiteralPath $localBinary) { $OllamaPath = $localBinary }
}
$route = (& wsl.exe -d $Distro --exec ip -4 route show default | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $route -notmatch 'default via ([0-9.]+)') { throw 'Could not discover the Windows gateway from WSL.' }
$hostAddress = $Matches[1]
$adapter = Get-NetIPAddress -AddressFamily IPv4 -IPAddress $hostAddress -ErrorAction Stop
if ($adapter.InterfaceAlias -notmatch 'WSL') { throw 'Refusing to bind Ollama to an interface that is not the WSL virtual adapter.' }
$baseUrl = "http://${hostAddress}:11434"
try { $version = Invoke-RestMethod "$baseUrl/api/version" -TimeoutSec 2 } catch { $version = $null }
if (!$version) {
    $variables = @{
        OLLAMA_HOST = "${hostAddress}:11434"
        OLLAMA_NO_CLOUD = '1'
        OLLAMA_CONTEXT_LENGTH = '4096'
        OLLAMA_NUM_PARALLEL = '1'
        OLLAMA_MAX_LOADED_MODELS = '1'
    }
    $saved = @{}
    try {
        foreach ($key in $variables.Keys) {
            $saved[$key] = [Environment]::GetEnvironmentVariable($key, 'Process')
            [Environment]::SetEnvironmentVariable($key, $variables[$key], 'Process')
        }
        if ($OllamaPath) { $ollama = (Resolve-Path -LiteralPath $OllamaPath).Path }
        else { $ollama = (Get-Command ollama.exe -ErrorAction Stop).Source }
        $process = Start-Process -FilePath $ollama -ArgumentList 'serve' -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $state 'stdout.log') -RedirectStandardError (Join-Path $state 'stderr.log')
        @{ pid = $process.Id; endpoint = $baseUrl; executable = $ollama; started = (Get-Date).ToString('o') } | ConvertTo-Json | Set-Content (Join-Path $state 'process.json')
    } finally {
        foreach ($key in $saved.Keys) { [Environment]::SetEnvironmentVariable($key, $saved[$key], 'Process') }
    }
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try { $version = Invoke-RestMethod "$baseUrl/api/version" -TimeoutSec 2; break } catch { Start-Sleep -Milliseconds 500 }
    }
    if (!$version) { throw "Ollama did not start. Inspect $state\stderr.log" }
}
$linuxEndpoint = Join-Path $evaluation '.env'
if (Test-Path -LiteralPath $linuxEndpoint) {
    $lines = @(Get-Content -LiteralPath $linuxEndpoint)
    $lines = @($lines | Where-Object { $_ -notmatch '^OLLAMA_(BASE_URL|MODEL)=' })
} else { $lines = @() }
$lines += "OLLAMA_BASE_URL=$baseUrl"
$lines += 'OLLAMA_MODEL=qwen3.5:9b'
[System.IO.File]::WriteAllText($linuxEndpoint, (($lines -join "`n") + "`n"), [System.Text.UTF8Encoding]::new($false))
Write-Host "Ollama $($version.version): $baseUrl (WSL virtual adapter only)"
