Set-Location $PSScriptRoot

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  Write-Host "Node.js is not installed. Install it first, then rerun." -ForegroundColor Red
  Write-Host "winget install OpenJS.NodeJS.LTS" -ForegroundColor Cyan
  exit 1
}

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example. Update DB credentials in .env" -ForegroundColor Yellow
}

npm install
npm run dev
