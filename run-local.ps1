Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

function Get-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @{ Command = "py"; Args = @("-3") }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @{ Command = "python"; Args = @() }
    }
    throw "Python is not installed or not on PATH."
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    $pyCmd = Get-PythonCommand
    & $pyCmd.Command @($pyCmd.Args + @("-m", "venv", ".venv"))
}

Write-Host "Installing dependencies..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example." -ForegroundColor Yellow
    Write-Host "Update DB settings and credentials in .env before using production data." -ForegroundColor Yellow
}

Write-Host "Starting Streamlit on http://localhost:8501 ..." -ForegroundColor Green
& $venvPython -m streamlit run app.py --server.port 8501 --server.headless true
