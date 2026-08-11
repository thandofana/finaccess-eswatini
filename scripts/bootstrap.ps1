param(
    [string]$PythonVersion = "3.13"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$VirtualEnvironment = Join-Path $ProjectRoot ".venv"
$env:OPENBLAS_NUM_THREADS = "1"

Push-Location $ProjectRoot
try {
    & py "-$PythonVersion" -m venv $VirtualEnvironment
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create the virtual environment with Python $PythonVersion."
    }

    $EnvironmentPython = Join-Path $VirtualEnvironment "Scripts\python.exe"
    & $EnvironmentPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install the project requirements."
    }

    & $EnvironmentPython --version
    Write-Output "Environment ready: $VirtualEnvironment"
}
finally {
    Pop-Location
}
