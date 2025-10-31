
param(
  [string]$BuildDir = ".\dist\RecibosDigitales",
  [string]$OutDir = ".\release"
)

$stamp = Get-Date -Format "yyyyMMdd_HHmm"
$releaseName = "RecibosDigitales_" + $stamp
$dest = Join-Path $OutDir $releaseName

New-Item -ItemType Directory -Path $dest -Force | Out-Null
Copy-Item "$BuildDir\*" $dest -Recurse -Force

Write-Host "Release preparado en $dest"
