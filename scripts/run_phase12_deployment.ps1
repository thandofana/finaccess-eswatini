$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Project virtual environment not found. Run scripts/bootstrap.ps1 first."
}

Push-Location $projectRoot
try {
    $env:PYTHONPATH = Join-Path $projectRoot "src"
    & $pythonPath -m finaccess_eswatini.phase12_deployment
    if ($LASTEXITCODE -ne 0) {
        throw "Phase 12 deployment validation failed."
    }
}
finally {
    Pop-Location
}
