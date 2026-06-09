# Build Evidencija.exe (requires Python on this machine only once).
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

Write-Host "Installing build dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-build.txt

Write-Host "Building executable..."
python -m PyInstaller --noconfirm build.spec

Write-Host ""
Write-Host "Done. Run:"
Write-Host "  dist\Evidencija\Evidencija.exe"
Write-Host ""
Write-Host "Copy the whole dist\Evidencija folder to the work PC."
Write-Host "Archives are stored in data\archive next to the .exe."
