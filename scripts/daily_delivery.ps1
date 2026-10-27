param(
    [string]$Repo = (Split-Path -Parent $PSScriptRoot),
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"
Set-Location $Repo
$env:PYTHONPATH = $Repo
$date = [TimeZoneInfo]::ConvertTimeBySystemTimeZoneId((Get-Date), "China Standard Time").ToString("yyyy-MM-dd")
$output = Join-Path $Repo "data\reports"
$snapshot = Join-Path $output "snapshot_$date.json"
$newProducts = Join-Path $output "new_products_$date.csv"
$html = Join-Path $output "release_$date.html"

python run_amazon_release.py --config config.example.json --timezone Asia/Shanghai --output-dir data/reports
if (!(Test-Path $snapshot) -or !(Test-Path $newProducts)) { throw "采集未生成当天 JSON/CSV：$date" }
python render_release_report.py --snapshot $snapshot --new-products $newProducts --date $date --output $html
if (!(Test-Path $html)) { throw "HTML 报告生成失败：$html" }

pytest -q tests/test_report.py tests/test_cli.py tests/test_m2_validation.py
git add -- $snapshot $newProducts $html
git diff --cached --check
if (git diff --cached --quiet) {
    Write-Host "当天报告没有新增 Git 变更：$date"
    exit 0
}
git commit -m "report: 交付 Amazon AU 选品日报 $date"
if (!$SkipPush) { git push origin master }
Write-Host "日报交付完成：$date"
