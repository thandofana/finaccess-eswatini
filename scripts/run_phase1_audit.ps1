$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvironmentPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $EnvironmentPython -PathType Leaf)) {
    throw "Virtual environment not found. Run scripts\bootstrap.ps1 first."
}

Push-Location $ProjectRoot
try {
    $env:PYTHONPATH = Join-Path $ProjectRoot "src"
    & $EnvironmentPython -m finaccess_eswatini.data_audit
    if ($LASTEXITCODE -ne 0) {
        throw "Phase 1 audit failed."
    }

    & $EnvironmentPython -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) {
        throw "Phase 1 validation tests failed."
    }
}
finally {
    Pop-Location
}

