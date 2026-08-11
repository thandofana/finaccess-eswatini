$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VirtualEnvironment = Join-Path $ProjectRoot ".venv"
$EnvironmentPython = Join-Path $VirtualEnvironment "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $EnvironmentPython)) {
    throw "Virtual environment not found. Run scripts\bootstrap.ps1 first."
}

$env:PYTHONPATH = Join-Path $ProjectRoot "src"
$env:OPENBLAS_NUM_THREADS = "1"

& $EnvironmentPython -m ipykernel install `
    --prefix $VirtualEnvironment `
    --name finaccess-eswatini `
    --display-name "FinAccess Eswatini"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to register the project notebook kernel."
}

& $EnvironmentPython (Join-Path $PSScriptRoot "execute_notebooks.py")
if ($LASTEXITCODE -ne 0) {
    throw "Notebook execution failed. Existing notebook files were preserved."
}
