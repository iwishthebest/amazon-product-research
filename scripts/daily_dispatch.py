from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from amazon_release.site_config import SiteConfig, load_sites


def due_sites(
    sites: list[SiteConfig],
    now_utc: datetime,
    ledger: dict[str, str],
) -> list[SiteConfig]:
    return [
        site
        for site in sites
        if site.is_due(now_utc) and ledger.get(site.code) != site.local_date(now_utc)
    ]


def mark_completed(ledger: dict[str, str], site: SiteConfig, now_utc: datetime) -> None:
    ledger[site.code] = site.local_date(now_utc)


def _read_ledger(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("dispatch ledger must be an object")
    return {str(key): str(value) for key, value in payload.items()}


def _write_ledger(path: Path, ledger: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _run_site(repo: Path, site: SiteConfig, *, push: bool) -> None:
    script = repo / "scripts" / "daily_delivery.ps1"
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-Repo",
        str(repo),
        "-Config",
        site.config_path,
        "-Timezone",
        site.timezone_name,
        "-SiteCode",
        site.code,
        "-OutputDir",
        site.output_dir,
        "-Db",
        site.db_path,
    ]
    if not push:
        command.append("-SkipPush")
    subprocess.run(command, cwd=repo, check=True)


def dispatch_once(
    repo: Path,
    sites: list[SiteConfig],
    ledger: dict[str, str],
    now_utc: datetime,
    runner: Callable[[Path, SiteConfig], None] | None = None,
    *,
    push: bool = False,
) -> list[str]:
    completed: list[str] = []
    for site in due_sites(sites, now_utc, ledger):
        if runner is None:
            _run_site(repo, site, push=push)
        else:
            runner(repo, site)
        mark_completed(ledger, site, now_utc)
        completed.append(site.code)
    return completed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run due Amazon marketplace daily reports.")
    parser.add_argument("--sites-config", default="config.sites.json")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--ledger", default="data/daily_dispatch_ledger.json")
    parser.add_argument("--now-utc", help="ISO timestamp for deterministic checks")
    parser.add_argument("--push", action="store_true", help="Allow daily_delivery.ps1 to push Git changes")
    parser.add_argument("--dry-run", action="store_true", help="Only list sites due for execution")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo = Path(args.repo).resolve()
    sites_path = Path(args.sites_config)
    if not sites_path.is_absolute():
        sites_path = repo / sites_path
    ledger_path = Path(args.ledger)
    if not ledger_path.is_absolute():
        ledger_path = repo / ledger_path
    sites = load_sites(sites_path)
    ledger = _read_ledger(ledger_path)
    now_utc = datetime.fromisoformat(args.now_utc) if args.now_utc else datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    if args.dry_run:
        print(json.dumps({"due": [site.code for site in due_sites(sites, now_utc, ledger)]}, ensure_ascii=False))
        return 0

    try:
        completed = dispatch_once(repo, sites, ledger, now_utc, push=args.push)
    except subprocess.CalledProcessError as exc:
        print(f"站点日报失败，退出码：{exc.returncode}", file=sys.stderr)
        return exc.returncode or 1
    _write_ledger(ledger_path, ledger)
    print(json.dumps({"completed": completed}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
