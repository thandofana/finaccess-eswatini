$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Project Python environment not found. Run scripts\bootstrap.ps1 first."
}

$env:PYTHONPATH = Join-Path $ProjectRoot "src"
$env:OPENBLAS_NUM_THREADS = "1"
$env:MPLBACKEND = "Agg"

& $Python -m finaccess_eswatini.phase8_model2 @args
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
