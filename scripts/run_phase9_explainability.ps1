$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $projectRoot "src"
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"

& $python -m finaccess_eswatini.phase9_explainability
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
