
param(
  [string]$ServerRoot = "M:\RecibosDigitales",
  [string]$BackupPath = ""
)

if (-not $BackupPath) { throw "Usá -BackupPath para indicar la carpeta de respaldo." }

$AppDir  = Join-Path $ServerRoot "app"
$Current = Join-Path $AppDir "RecibosDigitales"

if (-not (Test-Path $BackupPath)) { throw "No existe $BackupPath" }

Get-Process RecibosDigitales -ErrorAction SilentlyContinue | Stop-Process -Force

robocopy $BackupPath $Current /MIR | Out-Null

Write-Host "Rollback OK -> $BackupPath"
