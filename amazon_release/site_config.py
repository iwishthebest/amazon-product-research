from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


_LOCAL_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


@dataclass(frozen=True)
class SiteConfig:
    code: str
    timezone_name: str
    run_local_time: str
    config_path: str
    output_dir: str = "data/reports"
    db_path: str = "data/amazon_release.sqlite3"

    def __post_init__(self) -> None:
        code = self.code.strip().upper()
        if len(code) != 2 or not code.isalpha():
            raise ValueError("site code must be two letters")
        object.__setattr__(self, "code", code)
        try:
            ZoneInfo(self.timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"unknown timezone: {self.timezone_name}") from exc
        if not _LOCAL_TIME_RE.fullmatch(self.run_local_time):
            raise ValueError("run_local_time must use HH:MM")
        if not str(self.config_path).strip():
            raise ValueError("config path is required")

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)

    @property
    def run_time(self) -> time:
        return time.fromisoformat(self.run_local_time)

    def local_now(self, now_utc: datetime | None = None) -> datetime:
        value = now_utc or datetime.now(timezone.utc)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(self.zone)

    def local_date(self, now_utc: datetime | None = None) -> str:
        return self.local_now(now_utc).date().isoformat()

    def local_time(self, now_utc: datetime | None = None) -> time:
        return self.local_now(now_utc).time().replace(microsecond=0)

    def is_due(self, now_utc: datetime | None = None) -> bool:
        return self.local_time(now_utc) >= self.run_time


def load_sites(path: str | Path) -> list[SiteConfig]:
    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    raw_sites = payload.get("sites")
    if not isinstance(raw_sites, list) or not raw_sites:
        raise ValueError("sites must be a non-empty list")

    sites: list[SiteConfig] = []
    seen: set[str] = set()
    for raw in raw_sites:
        if not isinstance(raw, dict):
            raise ValueError("each site must be an object")
        site = SiteConfig(
            code=str(raw.get("code", "")),
            timezone_name=str(raw.get("timezone", "")),
            run_local_time=str(raw.get("run_local_time", "")),
            config_path=str(raw.get("config", "")),
            output_dir=str(raw.get("output_dir", "data/reports")),
            db_path=str(raw.get("db", "data/amazon_release.sqlite3")),
        )
        if site.code in seen:
            raise ValueError(f"duplicate site code: {site.code}")
        seen.add(site.code)
        sites.append(site)
    return sites
