$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$cloudUrl = Read-Host "FALLEN Cloud URL (https://...)"
$parsedCloudUrl = [Uri]$cloudUrl
if ($parsedCloudUrl.Scheme -ne "https" -and
    $parsedCloudUrl.Host -notin @("127.0.0.1", "localhost", "::1")) {
    throw "Remote FALLEN Cloud URLs must use HTTPS."
}

$agentName = (Read-Host "Windows agent name").Trim()
if ([string]::IsNullOrWhiteSpace($agentName) -or $agentName.Length -gt 100) {
    throw "Agent name must contain 1-100 non-whitespace characters."
}
$secureEnrollment = Read-Host "FALLEN enrollment token" -AsSecureString

$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureEnrollment)
try {
    $enrollment = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)

    $body = @{
        enrollment_token = $enrollment
        name = $agentName
    } | ConvertTo-Json

    $response = Invoke-RestMethod `
        -Uri "$($cloudUrl.TrimEnd('/'))/agents/register" `
        -Method Post `
        -ContentType "application/json" `
        -Body $body

    if (-not $response.agent_id -or -not $response.token) {
        throw "Cloud registration returned incomplete credentials."
    }
    if ($response.token.Length -lt 32) {
        throw "Cloud returned an invalid agent token."
    }
}
finally {
    if ($ptr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

$agentDir = Join-Path $root "agent"
$agentEnv = Join-Path $agentDir ".env"
@"
FALLEN_CLOUD_URL=$($cloudUrl.TrimEnd('/'))
FALLEN_AGENT_ID=$($response.agent_id)
FALLEN_AGENT_TOKEN=$($response.token)
FALLEN_AGENT_POLL_INTERVAL=1.5
FALLEN_AGENT_TIMEOUT=20
"@ | Set-Content -Encoding UTF8 $agentEnv

# Keep the agent credential file readable only by the current Windows account.
& icacls.exe $agentEnv /inheritance:r /grant:r "$env:USERNAME:(R,W)" | Out-Null

Write-Host "Windows Agent credentials saved to agent\.env." -ForegroundColor Green
Write-Host "Agent ID: $($response.agent_id)"
Write-Host "Token saved without printing it."
