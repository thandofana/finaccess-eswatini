$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$nodeRoot = Join-Path $projectRoot ".tools\node-v24.19.0-win-x64"
$webRoot = Join-Path $projectRoot "frontend\web"

if (-not (Test-Path -LiteralPath $pythonPath)) { throw "Project virtual environment not found." }
if (-not (Test-Path -LiteralPath (Join-Path $nodeRoot "npm.cmd"))) { throw "Project-local Node.js runtime not found." }

$env:PATH = "$nodeRoot;$env:PATH"
$env:PYTHONPATH = Join-Path $projectRoot "src"
$env:OPENBLAS_NUM_THREADS = "1"

& $pythonPath (Join-Path $projectRoot "scripts\write_phase13_regression.py") --status RUNNING
if ($LASTEXITCODE -ne 0) { throw "Phase 13 running record could not be written." }

Push-Location $projectRoot
try {
    & $pythonPath -m unittest discover -s tests -q
    if ($LASTEXITCODE -ne 0) { throw "Python project regression failed." }

    & $pythonPath -m unittest discover -s frontend/backend/tests -q
    if ($LASTEXITCODE -ne 0) { throw "Deployment backend regression failed." }
}
finally {
    Pop-Location
}

Push-Location $webRoot
try {
    & npm.cmd audit --omit=dev
    if ($LASTEXITCODE -ne 0) { throw "Production dependency audit failed." }
    & npm.cmd run lint
    if ($LASTEXITCODE -ne 0) { throw "Frontend lint failed." }
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw "Frontend production build failed." }
    & node.exe --test tests/rendered-html.test.mjs
    if ($LASTEXITCODE -ne 0) { throw "Rendered-route regression failed." }
}
finally {
    Pop-Location
}

Push-Location $projectRoot
try {
    & $pythonPath -m finaccess_eswatini.phase13_portfolio
    if ($LASTEXITCODE -ne 0) { throw "Phase 13 public portfolio validation failed." }
    & $pythonPath scripts/write_phase13_regression.py --status PASS
    if ($LASTEXITCODE -ne 0) { throw "Phase 13 regression record could not be written." }
}
finally {
    Pop-Location
}
