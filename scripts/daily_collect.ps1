param(
    [string]$Repo = (Split-Path -Parent $PSScriptRoot),
    [string]$Config = "config.example.json",
    [string]$Timezone = "",
    [string]$Db = "",
    [string]$OutputDir = "",
    [string]$SiteCode = ""
)
$ErrorActionPreference = "Stop"
Set-Location $Repo
$env:PYTHONPATH = $Repo

function Resolve-WindowsTimezoneId([string]$Name) {
    switch ($Name) {
        "America/New_York" { return "Eastern Standard Time" }
        "America/Chicago" { return "Central Standard Time" }
        "America/Denver" { return "Mountain Standard Time" }
        "America/Los_Angeles" { return "Pacific Standard Time" }
        "Australia/Sydney" { return "AUS Eastern Standard Time" }
        "Asia/Shanghai" { return "China Standard Time" }
        default { return $Name }
    }
}

if (!(Test-Path $Config)) { throw "配置文件不存在：$Config" }
$configObject = Get-Content -Raw -Encoding UTF8 $Config | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace($Timezone)) { $Timezone = [string]$configObject.timezone }
if ([string]::IsNullOrWhiteSpace($Timezone)) { throw "必须提供站点时区：$Config" }
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = "data/reports"
    if ($SiteCode) { $OutputDir = Join-Path $OutputDir $SiteCode.ToLowerInvariant() }
}
if ([string]::IsNullOrWhiteSpace($Db)) {
    $Db = "data/amazon_release.sqlite3"
    if ($SiteCode) { $Db = "data/amazon_release_$($SiteCode.ToLowerInvariant()).sqlite3" }
}

$windowsTimezone = Resolve-WindowsTimezoneId $Timezone
$date = [TimeZoneInfo]::ConvertTimeBySystemTimeZoneId((Get-Date), $windowsTimezone).ToString("yyyy-MM-dd")
$arguments = @(
    "run_amazon_release.py",
    "--config", $Config,
    "--timezone", $Timezone,
    "--db", $Db,
    "--output-dir", $OutputDir
)
python @arguments
if ($LASTEXITCODE -ne 0) { throw "每日采集失败，退出码：$LASTEXITCODE" }
$required = @(
    (Join-Path $Repo (Join-Path $OutputDir "snapshot_$date.json")),
    (Join-Path $Repo (Join-Path $OutputDir "categories_$date.json")),
    (Join-Path $Repo (Join-Path $OutputDir "new_products_$date.csv")),
    (Join-Path $Repo $Db)
)
$missing = @($required | Where-Object { !(Test-Path $_) })
if ($missing.Count -gt 0) { throw "每日采集未完整落盘：$($missing -join ', ')" }
Write-Host "每日新品采集完成 [$SiteCode]：$date ($Timezone)"
