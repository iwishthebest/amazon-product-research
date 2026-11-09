param(
    [string]$Repo = (Split-Path -Parent $PSScriptRoot),
    [string]$SitesConfig = "config.sites.json",
    [string]$Ledger = "data/daily_dispatch_ledger.json",
    [switch]$Push,
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
Set-Location $Repo
$env:PYTHONPATH = $Repo
$arguments = @(
    "scripts/daily_dispatch.py",
    "--repo", $Repo,
    "--sites-config", $SitesConfig,
    "--ledger", $Ledger
)
if ($Push) { $arguments += "--push" }
if ($DryRun) { $arguments += "--dry-run" }
python @arguments
if ($LASTEXITCODE -ne 0) { throw "日报分发失败，退出码：$LASTEXITCODE" }
