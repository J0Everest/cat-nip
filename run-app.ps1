Set-Location $PSScriptRoot

# Activate virtual environment
if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
  Write-Host "Virtual environment not found. Creating..." -ForegroundColor Yellow
  python -m venv .venv
}
& ".venv\Scripts\Activate.ps1"

# Install dependencies
pip install -r requirements.txt --quiet

# Create .env from example if missing
if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example. Review DB settings before continuing." -ForegroundColor Yellow
  Write-Host "Edit .env, then re-run this script." -ForegroundColor Cyan
  exit 0
}

# Apply migrations (creates local SQLite DB for saved scenarios)
python manage.py migrate --run-syncdb

Write-Host ""
Write-Host "Starting CAT-NIP..." -ForegroundColor Green
Write-Host "Open http://localhost:8000 in your browser" -ForegroundColor Cyan
Write-Host ""

python manage.py runserver
