$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvironmentPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $EnvironmentPython -PathType Leaf)) {
    throw "Virtual environment not found. Run scripts\bootstrap.ps1 first."
}

Push-Location $ProjectRoot
try {
    $env:PYTHONPATH = Join-Path $ProjectRoot "src"
    & $EnvironmentPython -m finaccess_eswatini.phase2_dictionary
    if ($LASTEXITCODE -ne 0) {
        throw "Phase 2 dictionary build failed."
    }

    & $EnvironmentPython -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) {
        throw "Phase 2 validation tests failed."
    }
}
finally {
    Pop-Location
}

