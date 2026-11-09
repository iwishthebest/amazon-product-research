param(
    [string]$Repo = (Split-Path -Parent $PSScriptRoot),
    [string]$SitesConfig = "config.sites.json",
    [int]$DispatchEveryMinutes = 30,
    [string]$WeeklyTime = "09:30"
)
$ErrorActionPreference = "Stop"
$dispatch = Join-Path $Repo "scripts\daily_dispatch.ps1"
$weekly = Join-Path $Repo "scripts\weekly_delivery.ps1"
$shell = (Get-Command powershell.exe).Source
$dispatchCommand = "$shell -NoProfile -ExecutionPolicy Bypass -File `"$dispatch`" -Repo `"$Repo`" -SitesConfig `"$SitesConfig`""
schtasks /Query /TN "AmazonRelease-DailyCollect" 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    schtasks /Delete /TN "AmazonRelease-DailyCollect" /F | Out-Null
}
schtasks /Create /TN "AmazonRelease-DailyDispatch" /SC MINUTE /MO $DispatchEveryMinutes /TR $dispatchCommand /F | Out-Null
schtasks /Create /TN "AmazonRelease-WeeklyReport" /SC WEEKLY /D SUN /ST $WeeklyTime /TR "$shell -NoProfile -ExecutionPolicy Bypass -File `"$weekly`" -Repo `"$Repo`"" /F | Out-Null
Write-Host "Registered timezone-aware daily and weekly AmazonRelease tasks"
