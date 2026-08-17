$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".venv")) {
    py -3.12 -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

if (-not (Test-Path ".env")) {
    $apiToken = & ".\.venv\Scripts\python.exe" -c "import secrets; print(secrets.token_urlsafe(48))"
    $sessionSecret = & ".\.venv\Scripts\python.exe" -c "import secrets; print(secrets.token_urlsafe(48))"
    $enrollmentToken = & ".\.venv\Scripts\python.exe" -c "import secrets; print(secrets.token_urlsafe(48))"

    @"
FALLEN_API_TOKEN=$apiToken
FALLEN_SESSION_SECRET=$sessionSecret
FALLEN_AGENT_ENROLLMENT_TOKEN=$enrollmentToken
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.6
FALLEN_DATA_DIR=./data
FALLEN_ALLOWED_HOSTS=127.0.0.1,localhost
FALLEN_ALLOWED_ORIGINS=http://127.0.0.1:5500,http://localhost:5500
FALLEN_COOKIE_SECURE=false
FALLEN_CLOUD_URL=http://127.0.0.1:8000
FALLEN_AGENT_ID=
FALLEN_AGENT_TOKEN=
FALLEN_AGENT_POLL_INTERVAL=1.5
FALLEN_AGENT_TIMEOUT=20
"@ | Set-Content -Encoding UTF8 .env
    & icacls.exe ".env" /inheritance:r /grant:r "$env:USERNAME:(R,W)" | Out-Null
}

Write-Host "FALLEN bootstrap complete." -ForegroundColor Green
Write-Host "Edit .env and set OPENAI_API_KEY before starting the backend."
