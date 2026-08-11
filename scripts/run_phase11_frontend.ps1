$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $projectRoot "frontend"
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$nodeRoot = Join-Path $projectRoot ".tools\node-v24.19.0-win-x64"

if (-not (Test-Path -LiteralPath $python)) { throw "Virtual environment not found. Run scripts\bootstrap.ps1 first." }
if (-not (Test-Path -LiteralPath (Join-Path $nodeRoot "npm.cmd"))) { throw "Project-local Node.js runtime is missing." }

$env:PATH = "$nodeRoot;$env:PATH"
$env:PYTHONPATH = Join-Path $projectRoot "src"

Push-Location $frontendRoot
try {
    & npm.cmd run lint
    if ($LASTEXITCODE -ne 0) { throw "Frontend lint failed." }
    & npm.cmd test
    if ($LASTEXITCODE -ne 0) { throw "Frontend build or rendered-route tests failed." }
}
finally {
    Pop-Location
}

Push-Location $projectRoot
try {
    & $python -m finaccess_eswatini.phase11_frontend_validation
    if ($LASTEXITCODE -ne 0) { throw "Phase 11 frontend validation failed." }
    & $python -m unittest tests.test_phase11_frontend tests.test_project_structure -v
    if ($LASTEXITCODE -ne 0) { throw "Phase 11 project tests failed." }
}
finally {
    Pop-Location
}
