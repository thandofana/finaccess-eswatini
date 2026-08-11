param(
    [string]$RawData = "",
    [string]$Dictionary = "",
    [string]$ReportDirectory = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$EnvironmentPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $EnvironmentPython)) {
    throw "Virtual environment not found. Run scripts\bootstrap.ps1 first."
}
if (-not $RawData) {
    $RawData = Join-Path $ProjectRoot "data\raw\Findex_Microdata_2025_updateEswatini.csv"
}
if (-not $Dictionary) {
    $Dictionary = Join-Path $ProjectRoot "reports\phase_2\data_dictionary.csv"
}
if (-not $ReportDirectory) {
    $ReportDirectory = Join-Path $ProjectRoot "reports\phase_4"
}

$env:PYTHONPATH = Join-Path $ProjectRoot "src"
$env:OPENBLAS_NUM_THREADS = "1"
$env:MPLBACKEND = "Agg"

& $EnvironmentPython -m finaccess_eswatini.phase4_eda `
    --raw $RawData `
    --dictionary $Dictionary `
    --output-dir $ReportDirectory
if ($LASTEXITCODE -ne 0) {
    throw "Phase 4 exploratory analysis failed."
}
