param(
    [string]$Repo = (Split-Path -Parent $PSScriptRoot),
    [string]$Config = "config.example.json",
    [string]$OutputSubdir = "",
    [string]$Db = "",
    [string]$OutputDir = "",
    [string]$Timezone = "",
    [string]$SiteCode = "",
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"
Set-Location $Repo
$env:PYTHONPATH = $Repo
if (!(Test-Path $Config)) { throw "配置文件不存在：$Config" }
$configObject = Get-Content -Raw -Encoding UTF8 $Config | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace($Timezone)) { $Timezone = [string]$configObject.timezone }
if ([string]::IsNullOrWhiteSpace($Timezone)) { throw "必须提供站点时区：$Config" }
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = "data\reports"
    if ($SiteCode) { $OutputDir = Join-Path $OutputDir $SiteCode.ToLowerInvariant() }
    if ($OutputSubdir) { $OutputDir = Join-Path $OutputDir $OutputSubdir }
}
if ([string]::IsNullOrWhiteSpace($Db)) {
    $Db = "data/amazon_release.sqlite3"
    if ($SiteCode) { $Db = "data/amazon_release_$($SiteCode.ToLowerInvariant()).sqlite3" }
}
$windowsTimezone = switch ($Timezone) {
    "America/New_York" { "Eastern Standard Time"; break }
    "America/Chicago" { "Central Standard Time"; break }
    "America/Denver" { "Mountain Standard Time"; break }
    "America/Los_Angeles" { "Pacific Standard Time"; break }
    "Australia/Sydney" { "AUS Eastern Standard Time"; break }
    "Asia/Shanghai" { "China Standard Time"; break }
    default { $Timezone }
}
$date = [TimeZoneInfo]::ConvertTimeBySystemTimeZoneId((Get-Date), $windowsTimezone).ToString("yyyy-MM-dd")
$output = Join-Path $Repo $OutputDir
$dbPath = Join-Path $Repo $Db
$snapshot = Join-Path $output "snapshot_$date.json"
$newProducts = Join-Path $output "new_products_$date.csv"
$html = Join-Path $output "release_$date.html"

python run_amazon_release.py --config $Config --timezone $Timezone --output-dir $output --db $dbPath
if (!(Test-Path $snapshot) -or !(Test-Path $newProducts)) { throw "采集未生成当天 JSON/CSV：$date ($Timezone)" }
python resolve_release_images.py --snapshot $snapshot --new-products $newProducts --output-html $html
if (!(Test-Path $html)) { throw "HTML 报告生成失败：$html" }

pytest -q tests/test_report.py tests/test_cli.py tests/test_m2_validation.py
# data/ is ignored for local runtime artifacts; force-add only the three customer deliverables.
git add -f -- $snapshot $newProducts $html
if (Test-Path (Join-Path $output "images")) {
    git add -f -- (Join-Path $output "images")
}
git diff --cached --check
if (git diff --cached --quiet) {
    Write-Host "当天报告没有新增 Git 变更：$date [$SiteCode]"
    exit 0
}
git commit -m "report: 交付 Amazon $SiteCode 选品日报 $date"
if (!$SkipPush) { git push origin master }
Write-Host "日报交付完成 [$SiteCode]：$date ($Timezone)"
