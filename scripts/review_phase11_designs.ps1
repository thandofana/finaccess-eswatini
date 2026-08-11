param(
    [int]$WebPort = 3011,
    [int]$ApiPort = 8000,
    [switch]$NoBrowser,
    [switch]$ExitAfterReady
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $projectRoot "frontend"
$runtimeRoot = Join-Path $projectRoot ".runtime"
$stateFile = Join-Path $runtimeRoot "phase11-review.json"
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$nodeRoot = Join-Path $projectRoot ".tools\node-v24.19.0-win-x64"
$node = Join-Path $nodeRoot "node.exe"
$npm = Join-Path $nodeRoot "npm.cmd"
$vinext = "node_modules\vinext\dist\cli.js"
$apiProcess = $null
$webProcess = $null
$startupCompleted = $false

function Test-ApiReady {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$ApiPort/health" -TimeoutSec 2
        return $health.status -eq "healthy"
    }
    catch { return $false }
}

function Test-WebReady {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$WebPort/" -TimeoutSec 2
        return $response.StatusCode -eq 200 -and $response.Content -match "FinAccess Eswatini"
    }
    catch { return $false }
}

function Wait-UntilReady {
    param([scriptblock]$Check, [string]$Name)
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if (& $Check) { return }
        Start-Sleep -Milliseconds 500
    }
    throw "$Name did not become ready."
}

function Stop-OwnedProcess {
    param($Process)
    if ($null -ne $Process -and -not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force
    }
}

try {
    if (-not (Test-Path -LiteralPath $python)) { throw "The project Python environment is missing." }
    if (-not (Test-Path -LiteralPath $node)) { throw "The project web runtime is missing." }
    if (-not (Test-Path -LiteralPath (Join-Path $frontendRoot $vinext))) { throw "Frontend packages are missing." }

    New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null
    $apiOut = Join-Path $runtimeRoot "phase11-api.out.log"
    $apiErr = Join-Path $runtimeRoot "phase11-api.err.log"
    $webOut = Join-Path $runtimeRoot "phase11-web.out.log"
    $webErr = Join-Path $runtimeRoot "phase11-web.err.log"

    $env:PYTHONPATH = "$projectRoot$([IO.Path]::PathSeparator)$(Join-Path $projectRoot 'src')"
    $env:FINACCESS_API_URL = "http://127.0.0.1:$ApiPort"
    $env:PATH = "$nodeRoot;$env:PATH"

    if (-not (Test-ApiReady)) {
        Write-Host "Starting the prediction service..." -ForegroundColor DarkGreen
        $apiProcess = Start-Process -FilePath $python `
            -ArgumentList @("-m", "uvicorn", "api.app.main:app", "--host", "127.0.0.1", "--port", "$ApiPort") `
            -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput $apiOut -RedirectStandardError $apiErr
        Wait-UntilReady -Check ${function:Test-ApiReady} -Name "Prediction service"
    }

    if (-not (Test-Path -LiteralPath (Join-Path $frontendRoot "dist\server\index.js"))) {
        Write-Host "Preparing the design gallery for first use..." -ForegroundColor DarkGreen
        Push-Location $frontendRoot
        try {
            & $npm run build
            if ($LASTEXITCODE -ne 0) { throw "The design gallery could not be prepared." }
        }
        finally { Pop-Location }
    }

    if (-not (Test-WebReady)) {
        Write-Host "Starting the design gallery..." -ForegroundColor DarkGreen
        $webProcess = Start-Process -FilePath $node `
            -ArgumentList @($vinext, "start", "--port", "$WebPort") `
            -WorkingDirectory $frontendRoot -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput $webOut -RedirectStandardError $webErr
        Wait-UntilReady -Check ${function:Test-WebReady} -Name "Design gallery"
    }

    [ordered]@{
        project_root = $projectRoot
        api_pid = if ($null -ne $apiProcess) { $apiProcess.Id } else { $null }
        web_pid = if ($null -ne $webProcess) { $webProcess.Id } else { $null }
        api_url = "http://127.0.0.1:$ApiPort"
        review_url = "http://127.0.0.1:$WebPort/"
    } | ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding UTF8

    $reviewUrl = "http://127.0.0.1:$WebPort/"
    Write-Host ""
    Write-Host "FinAccess design review is ready." -ForegroundColor Green
    Write-Host "Opening The Ledger, Open Field, and Signal at:"
    Write-Host $reviewUrl -ForegroundColor Cyan
    Write-Host "Use STOP_DESIGN_REVIEW.cmd when you are finished."
    $startupCompleted = $true

    if (-not $NoBrowser) { Start-Process -FilePath $reviewUrl }
}
catch {
    Write-Host ""
    Write-Host "Startup failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Details are saved in $runtimeRoot" -ForegroundColor Yellow
    throw
}
finally {
    if ($ExitAfterReady -or -not $startupCompleted) {
        Stop-OwnedProcess $webProcess
        Stop-OwnedProcess $apiProcess
    }
}
