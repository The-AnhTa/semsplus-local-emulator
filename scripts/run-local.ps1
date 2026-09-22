param(
    [string]$HostAddress = $(if ($env:CER_HOST) { $env:CER_HOST } else { "0.0.0.0" }),
    [int]$Port = $(if ($env:CER_PORT) { [int]$env:CER_PORT } else { 8080 })
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$frontendIndex = Join-Path $projectRoot "frontend\dist\index.html"

if (-not (Test-Path -LiteralPath $frontendIndex -PathType Leaf)) {
    throw "Compiled frontend assets are missing from frontend/dist."
}

$pythonBin = if (Test-Path -LiteralPath $venvPython -PathType Leaf) { $venvPython } else { "python" }
$dataDir = if ($env:CER_DATA_DIR) { $env:CER_DATA_DIR } else { Join-Path $projectRoot "data" }
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

if (-not $env:CER_DATABASE_PATH) {
    $env:CER_DATABASE_PATH = Join-Path $dataDir "cer-emulator.db"
}

& $pythonBin -m uvicorn app.main:app `
    --app-dir (Join-Path $projectRoot "backend") `
    --host $HostAddress `
    --port $Port
exit $LASTEXITCODE
