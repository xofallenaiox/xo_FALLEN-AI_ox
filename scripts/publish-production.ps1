$ErrorActionPreference = "Stop"

param(
    [string]$Repository = "xofallenaiox/xo_FALLEN-AI_ox",
    [string]$Branch = "production-hardening"
)

$root = Split-Path -Parent $PSScriptRoot
$repoDir = Join-Path $root "..\..\xo_FALLEN-production"

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is required."
}

$repoDir = [IO.Path]::GetFullPath($repoDir)
if (-not (Test-Path $repoDir)) {
    git clone "https://github.com/$Repository.git" $repoDir
}

Set-Location $repoDir

git fetch origin
if (git show-ref --verify --quiet "refs/heads/$Branch") {
    git checkout $Branch
} else {
    git checkout -b $Branch
}

$source = [IO.Path]::GetFullPath($root)
robocopy $source $repoDir /E /XD ".git" ".venv" "__pycache__" ".pytest_cache" "data" /XF ".env" "fallen_cloud.db" "*.db" | Out-Null

if (Test-Path ".env") {
    throw "Refusing to publish: .env exists in the repository."
}

git status --short
git add .
git commit -m "Harden FALLEN for production deployment"
git push -u origin $Branch

Write-Host "Published branch: $Branch" -ForegroundColor Green
