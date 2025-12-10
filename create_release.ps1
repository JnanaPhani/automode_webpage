# PowerShell script to create GitHub release
# Usage: .\create_release.ps1 -Token "your_github_token"

param(
    [Parameter(Mandatory=$true)]
    [string]$Token
)

$repo = "JnanaPhani/automode_webpage"
$tag = "v1.0.0-windows"
$releaseName = "Windows Release v1.0.0 - ZenithTek Sensor Configuration Tool"
$releaseNotes = Get-Content "RELEASE_NOTES_v1.0.0-windows.md" -Raw

$body = @{
    tag_name = $tag
    name = $releaseName
    body = $releaseNotes
    draft = $false
    prerelease = $false
} | ConvertTo-Json

$headers = @{
    "Authorization" = "token $Token"
    "Accept" = "application/vnd.github.v3+json"
}

try {
    $response = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/releases" -Method Post -Headers $headers -Body $body -ContentType "application/json"
    Write-Host "Release created successfully!" -ForegroundColor Green
    Write-Host "Release URL: $($response.html_url)" -ForegroundColor Cyan
} catch {
    Write-Host "Error creating release: $_" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
}

