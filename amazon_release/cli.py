from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from .client import AmazonHttpClient
from .crawler import NewReleaseCrawler
from .models import CategoryLink
from .storage import SQLiteStore


DEFAULT_CONFIG = {
    "marketplace_id": "A39IBJ37TRP1C6",
    "allowed_domain": "amazon.com.au",
    "timezone": "Australia/Sydney",
    "delay_seconds": 1.0,
    "max_pages": 10,
    "max_category_depth": 2,
    "discover_subcategories": True,
    "exclude_node_ids": ["5043942051"],
    "roots": [
        {
            "name": "Pilates",
            "node_id": "5044228051",
            "url": "https://www.amazon.com.au/gp/new-releases/sporting-goods/5044228051",
        },
        {
            "name": "Yoga",
            "node_id": "5044231051",
            "url": "https://www.amazon.com.au/gp/new-releases/sporting-goods/5044231051",
        },
    ],
}


class FixtureFetcher:
    """Map Amazon New Releases URLs to local HTML fixtures for offline runs."""

    def __init__(self, fixture_dir: str | Path) -> None:
        self.fixture_dir = Path(fixture_dir)

    def fetch(self, url: str) -> str:
        parsed = urlparse(url)
        node_matches = re.findall(r"/(\d{4,})(?:/|$)", parsed.path)
        match = node_matches[-1] if node_matches else None
        if not match:
            raise FileNotFoundError(f"Cannot infer category node from fixture URL: {url}")
        node_id = match
        page = parse_qs(parsed.query).get("pg", ["1"])[0]
        suffix = "" if page == "1" else f"_page{page}"
        path = self.fixture_dir / f"category_{node_id}{suffix}.html"
        if not path.exists():
            raise FileNotFoundError(f"Missing fixture for {url}: {path}")
        return path.read_text(encoding="utf-8")


def load_config(path: str | Path | None) -> dict:
    config = dict(DEFAULT_CONFIG)
    if path:
        supplied = json.loads(Path(path).read_text(encoding="utf-8"))
        config.update(supplied)
    config["roots"] = config.get("roots") or DEFAULT_CONFIG["roots"]
    return config


def _report_date(config: dict) -> str:
    timezone_name = config.get("timezone", "UTC")
    return datetime.now(ZoneInfo(timezone_name)).date().isoformat()


def run_once(config: dict, *, fixture_dir: str | Path | None, db_path: str | Path, output_dir: str | Path, dry_run: bool = False) -> dict:
    if fixture_dir:
        fetcher = FixtureFetcher(fixture_dir)
    else:
        fetcher = AmazonHttpClient(
            allowed_domain=config["allowed_domain"],
            timeout=float(config.get("timeout_seconds", 30.0)),
            delay_seconds=float(config.get("delay_seconds", 1.0)),
            max_retries=int(config.get("max_retries", 3)),
        )
    crawler = NewReleaseCrawler(
        fetcher,
        marketplace_id=config["marketplace_id"],
        allowed_domain=config["allowed_domain"],
        # AmazonHttpClient owns request pacing; the crawler itself stays side-effect free.
        delay_seconds=0,
        max_pages=int(config.get("max_pages", 10)),
        max_category_depth=int(config.get("max_category_depth", 2)),
    )
    categories, products = crawler.run(
        config["roots"],
        discover_subcategories=bool(config.get("discover_subcategories", True)),
    )
    excluded = {str(node_id) for node_id in config.get("exclude_node_ids", [])}
    if excluded:
        categories = [category for category in categories if category.node_id not in excluded]
        products = [product for product in products if product.category_node_id not in excluded]
    date = _report_date(config)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    snapshot_path = output / f"snapshot_{date}.json"
    category_path = output / f"categories_{date}.json"
    db = SQLiteStore(db_path)
    try:
        new_products = products if dry_run else db.record_products(products)
        db.export_json(products, snapshot_path)
        category_path.write_text(
            json.dumps([category.__dict__ for category in categories], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        db.export_csv(new_products, output / f"new_products_{date}.csv")
    finally:
        db.close()
    return {
        "categories": len(categories),
        "products": len(products),
        "new_products": len(new_products),
        "snapshot": str(snapshot_path),
        "report": str(output / f"new_products_{date}.csv"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect Amazon Australia New Releases for Pilates and Yoga.")
    parser.add_argument("--config", help="JSON configuration file")
    parser.add_argument("--fixture-dir", help="Use local HTML fixtures instead of network requests")
    parser.add_argument("--db", default="data/amazon_release.sqlite3", help="SQLite database path")
    parser.add_argument("--output-dir", default="data/reports", help="Output directory")
    parser.add_argument("--delay-seconds", type=float, help="Override request delay in seconds")
    parser.add_argument("--timezone", help="Override report timezone, e.g. Asia/Shanghai")
    parser.add_argument("--timeout-seconds", type=float, help="Override HTTP timeout")
    parser.add_argument("--max-retries", type=int, help="Override HTTP retry count")
    parser.add_argument("--max-pages", type=int, help="Override maximum pages per category")
    parser.add_argument("--max-category-depth", type=int, help="Override category discovery depth")
    parser.add_argument("--dry-run", action="store_true", help="Do not compare with prior database state")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    if args.delay_seconds is not None:
        config["delay_seconds"] = args.delay_seconds
    if args.timezone:
        config["timezone"] = args.timezone
    if args.timeout_seconds is not None:
        config["timeout_seconds"] = args.timeout_seconds
    if args.max_retries is not None:
        config["max_retries"] = args.max_retries
    if args.max_pages is not None:
        config["max_pages"] = args.max_pages
    if args.max_category_depth is not None:
        config["max_category_depth"] = args.max_category_depth
    result = run_once(
        config,
        fixture_dir=args.fixture_dir,
        db_path=args.db,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
