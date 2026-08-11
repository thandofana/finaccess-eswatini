$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$nodePath = Join-Path $projectRoot ".tools\node-v24.19.0-win-x64\node.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Project virtual environment not found. Run scripts/bootstrap.ps1 first."
}
if (-not (Test-Path -LiteralPath $nodePath)) {
    throw "Project-local Node.js runtime not found."
}

Push-Location $projectRoot
try {
    $env:PYTHONPATH = Join-Path $projectRoot "src"
    & $nodePath scripts/capture_phase13_screenshots.mjs
    if ($LASTEXITCODE -ne 0) { throw "Live screenshot capture failed." }

    & $pythonPath scripts/build_phase13_notebook.py
    if ($LASTEXITCODE -ne 0) { throw "Phase 13 notebook build failed." }

    & $pythonPath -m finaccess_eswatini.phase13_portfolio
    if ($LASTEXITCODE -ne 0) { throw "Phase 13 portfolio validation failed." }
}
finally {
    Pop-Location
}
