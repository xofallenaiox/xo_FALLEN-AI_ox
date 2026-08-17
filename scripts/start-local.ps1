$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".env")) {
    throw "Missing .env. Run .\scripts\bootstrap_windows.ps1 first."
}

& ".\.venv\Scripts\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
