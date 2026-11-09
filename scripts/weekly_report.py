from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from amazon_release.storage import SQLiteStore
from amazon_release.report import render_weekly_html


def week_bounds(anchor: date) -> tuple[str, str]:
    start = anchor - timedelta(days=anchor.weekday())
    return start.isoformat(), (start + timedelta(days=6)).isoformat()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export a weekly Amazon New Releases report.")
    parser.add_argument("--db", default="data/amazon_release.sqlite3")
    parser.add_argument("--output-dir", default="data/reports")
    parser.add_argument("--start", help="Monday, YYYY-MM-DD. Defaults to the current week's Monday.")
    parser.add_argument(
        "--timezone",
        default="America/New_York",
        help="Local timezone used for week boundaries and first-seen dates.",
    )
    args = parser.parse_args(argv)
    if args.start:
        start, end = week_bounds(date.fromisoformat(args.start))
    else:
        start, end = week_bounds(datetime.now(ZoneInfo(args.timezone)).date())
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    with SQLiteStore(args.db) as store:
        rows = store.weekly_products(start, end, timezone_name=args.timezone)
        path = store.export_weekly_csv(
            start,
            end,
            output / f"weekly_new_products_{start}_{end}.csv",
            timezone_name=args.timezone,
        )
        html_path = render_weekly_html(
            rows,
            output / f"weekly_new_products_{start}_{end}.html",
            start_date=start,
            end_date=end,
            timezone_name=args.timezone,
        )
    print(f"CSV: {path}\nHTML: {html_path}\n商品数: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
