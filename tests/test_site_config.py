from datetime import datetime, time, timezone

import pytest

from amazon_release.site_config import SiteConfig, load_sites


def test_site_config_uses_named_timezone_for_business_date_and_due_check():
    site = SiteConfig(
        code="AU",
        timezone_name="Australia/Sydney",
        run_local_time="08:30",
        config_path="config.au.json",
    )

    now_utc = datetime(2026, 11, 8, 21, 0, tzinfo=timezone.utc)

    assert site.local_date(now_utc) == "2026-11-09"
    assert site.local_time(now_utc) == time(8, 0)
    assert site.is_due(now_utc) is False
    assert site.is_due(datetime(2026, 11, 8, 21, 30, tzinfo=timezone.utc)) is True


def test_site_config_handles_us_standard_and_daylight_offsets():
    site = SiteConfig(
        code="US",
        timezone_name="America/Los_Angeles",
        run_local_time="08:30",
        config_path="config.us.json",
    )

    winter = datetime(2026, 1, 15, 16, 30, tzinfo=timezone.utc)
    summer = datetime(2026, 7, 15, 15, 30, tzinfo=timezone.utc)

    assert site.is_due(winter) is True
    assert site.is_due(summer) is True


def test_load_sites_rejects_duplicate_codes_and_invalid_time(tmp_path):
    config = tmp_path / "sites.json"
    config.write_text(
        '{"sites": [{"code": "AU", "timezone": "Australia/Sydney", '
        '"run_local_time": "08:30", "config": "au.json"}, '
        '{"code": "AU", "timezone": "Australia/Sydney", '
        '"run_local_time": "09:00", "config": "au2.json"}]}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate site code"):
        load_sites(config)

    config.write_text(
        '{"sites": [{"code": "AU", "timezone": "Australia/Sydney", '
        '"run_local_time": "8:30", "config": "au.json"}]}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="HH:MM"):
        load_sites(config)
