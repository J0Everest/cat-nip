param(
  [string]$Server = "localhost",
  [switch]$Trusted
)

$scriptPath = Join-Path $PSScriptRoot "sql\schema.sql"

if ($Trusted) {
  sqlcmd -S $Server -E -i $scriptPath
} else {
  Write-Host "Using SQL auth from command line. Example:" -ForegroundColor Yellow
  Write-Host ".\setup-db.ps1 -Server localhost -Trusted" -ForegroundColor Yellow
  Write-Host "or run manually: sqlcmd -S localhost -U sa -P <password> -i .\sql\schema.sql" -ForegroundColor Yellow
}
