param(
    [string]$Repo = (Split-Path -Parent $PSScriptRoot),
    [string]$Timezone = "America/New_York",
    [string]$Db = "data/amazon_release.sqlite3",
    [string]$OutputDir = "data/reports",
    [string]$Start = ""
)
$ErrorActionPreference = "Stop"
Set-Location $Repo
$env:PYTHONPATH = $Repo
$arguments = @(
    "scripts/weekly_report.py",
    "--db", $Db,
    "--output-dir", $OutputDir,
    "--timezone", $Timezone
)
if ($Start) { $arguments += @("--start", $Start) }
python @arguments
if ($LASTEXITCODE -ne 0) { throw "周报汇总失败，退出码：$LASTEXITCODE" }
$report = Get-ChildItem -Path (Join-Path $Repo $OutputDir) -Filter "weekly_new_products_*.csv" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if ($null -eq $report) { throw "周报汇总未生成 CSV：$(Join-Path $Repo $OutputDir)" }
$htmlReport = Get-ChildItem -Path (Join-Path $Repo $OutputDir) -Filter "weekly_new_products_*.html" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if ($null -eq $htmlReport) { throw "周报汇总未生成 HTML：$(Join-Path $Repo $OutputDir)" }
Write-Host "周报 CSV：$($report.FullName)"
Write-Host "周报 HTML：$($htmlReport.FullName)"
