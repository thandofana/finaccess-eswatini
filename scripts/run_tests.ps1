$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvironmentPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $EnvironmentPython)) {
    throw "Virtual environment not found. Run scripts\bootstrap.ps1 first."
}

$env:PYTHONPATH = Join-Path $ProjectRoot "src"
$env:OPENBLAS_NUM_THREADS = "1"

Push-Location $ProjectRoot
try {
    & $EnvironmentPython -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) {
        throw "Project validation tests failed."
    }
}
finally {
    Pop-Location
}
