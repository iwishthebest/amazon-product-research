from datetime import datetime, timezone
import subprocess
import sys

from amazon_release.site_config import SiteConfig
from scripts.daily_dispatch import due_sites, mark_completed


def test_due_sites_returns_each_site_once_per_local_business_date():
    sites = [
        SiteConfig("AU", "Australia/Sydney", "08:30", "au.json"),
    ]
    now_utc = datetime(2026, 11, 8, 21, 30, tzinfo=timezone.utc)
    ledger = {}

    due = due_sites(sites, now_utc, ledger)
    assert [site.code for site in due] == ["AU"]

    mark_completed(ledger, due[0], now_utc)
    assert due_sites(sites, now_utc, ledger) == []


def test_due_sites_keeps_us_business_date_separate_from_au():
    sites = [
        SiteConfig("AU", "Australia/Sydney", "08:30", "au.json"),
        SiteConfig("US", "America/Los_Angeles", "08:30", "us.json"),
    ]
    now_utc = datetime(2026, 11, 9, 16, 30, tzinfo=timezone.utc)

    due = due_sites(sites, now_utc, {})

    assert [site.code for site in due] == ["US"]
    assert due[0].local_date(now_utc) == "2026-11-09"


def test_dispatch_script_can_run_directly_from_repo_root():
    result = subprocess.run(
        [sys.executable, "scripts/daily_dispatch.py", "--help"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Run due Amazon marketplace daily reports" in result.stdout


def test_dispatch_dry_run_lists_due_sites_without_site_configs(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/daily_dispatch.py",
            "--sites-config",
            "config.sites.example.json",
            "--repo",
            ".",
            "--ledger",
            str(tmp_path / "ledger.json"),
            "--now-utc",
            "2026-11-09T16:30:00+00:00",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert '"due": ["US"]' in result.stdout
