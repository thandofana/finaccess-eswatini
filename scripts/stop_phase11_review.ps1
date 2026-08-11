$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path $projectRoot ".runtime"
$stateFile = Join-Path $runtimeRoot "phase11-review.json"

if (-not (Test-Path -LiteralPath $stateFile)) {
    Write-Host "No FinAccess design review started by the launcher is running."
    exit 0
}

$state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
$expectedExecutables = @{
    api_pid = (Join-Path $projectRoot ".venv\Scripts\python.exe")
    web_pid = (Join-Path $projectRoot ".tools\node-v24.19.0-win-x64\node.exe")
}

foreach ($field in @("web_pid", "api_pid")) {
    $processId = $state.$field
    if ($null -eq $processId) { continue }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    if ($null -eq $process) { continue }
    $expected = [IO.Path]::GetFullPath($expectedExecutables[$field])
    $actual = [IO.Path]::GetFullPath($process.ExecutablePath)
    if ($actual -ne $expected) {
        throw "Refusing to stop process $processId because it is not the recorded FinAccess service."
    }
    Stop-Process -Id $processId -Force
}

Remove-Item -LiteralPath $stateFile -Force
Write-Host "FinAccess design review services have stopped." -ForegroundColor Green
