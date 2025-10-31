
param(
  [string]$LocalRelease = "",
  [string]$ServerRoot   = "M:\RecibosDigitales"
)

if (-not $LocalRelease) { throw "Especificá -LocalRelease con la carpeta del release." }
if (-not (Test-Path $LocalRelease)) { throw "No existe $LocalRelease" }
if (-not (Test-Path (Join-Path $LocalRelease "RecibosDigitales.exe"))) {
  throw "El release no contiene RecibosDigitales.exe"
}

$AppDir   = Join-Path $ServerRoot "app"
$Current  = Join-Path $AppDir "RecibosDigitales"
$DataRoot = Join-Path $ServerRoot "data"

New-Item -ItemType Directory -Path $ServerRoot -Force | Out-Null
New-Item -ItemType Directory -Path $AppDir -Force | Out-Null
New-Item -ItemType Directory -Path $DataRoot -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $DataRoot "db") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $DataRoot "logs") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $DataRoot "recibos") -Force | Out-Null

$stamp = Get-Date -Format "yyyyMMdd_HHmm"
$TargetVersion = Join-Path $AppDir ("RecibosDigitales_" + $stamp)

robocopy $LocalRelease $TargetVersion /MIR | Out-Null

Get-Process RecibosDigitales -ErrorAction SilentlyContinue | Stop-Process -Force

$Backup = Join-Path $AppDir ("RecibosDigitales_backup_" + $stamp)
if (Test-Path $Current) {
  robocopy $Current $Backup /MIR | Out-Null
}

robocopy $TargetVersion $Current /MIR | Out-Null

$EnvFile = Join-Path $ServerRoot ".env"
if (Test-Path $EnvFile) {
  Copy-Item $EnvFile (Join-Path $Current ".env") -Force
}

Write-Host "Deploy OK."
Write-Host "Versión nueva: $TargetVersion"
Write-Host "Respaldo:     $Backup"
Write-Host "Carpeta viva: $Current"
