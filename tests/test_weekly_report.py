import csv
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from amazon_release.models import ProductRecord
from amazon_release.storage import SQLiteStore
from scripts.weekly_report import main


def _product(asin: str, crawl_time: datetime) -> ProductRecord:
    return ProductRecord(
        marketplace_id="A39IBJ37TRP1C6",
        category_name="Pilates",
        category_node_id="5044228051",
        rank=1,
        asin=asin,
        title="Pilates Ring",
        product_url=f"https://www.amazon.com.au/dp/{asin}",
        image_url=None,
        price=29.99,
        currency="AUD",
        rating=4.5,
        review_count=12,
        source_url="https://www.amazon.com.au/gp/new-releases/sporting-goods/5044228051",
        crawl_time=crawl_time,
    )


def test_weekly_report_writes_one_merged_file_with_first_seen_date(tmp_path):
    db_path = tmp_path / "products.sqlite3"
    with SQLiteStore(db_path) as store:
        store.record_products([_product("B0ABC12345", datetime(2026, 10, 20, tzinfo=timezone.utc))])
        store.record_products([_product("B0ABC12345", datetime(2026, 10, 21, tzinfo=timezone.utc))])

    assert main([
        "--db", str(db_path),
        "--output-dir", str(tmp_path / "reports"),
        "--start", "2026-10-19",
        "--timezone", "UTC",
    ]) == 0

    reports = list((tmp_path / "reports").glob("weekly_new_products_2026-10-19_2026-10-25.csv"))
    assert len(reports) == 1
    html_report = tmp_path / "reports" / "weekly_new_products_2026-10-19_2026-10-25.html"
    assert html_report.exists()
    assert "Amazon 新品周报" in html_report.read_text(encoding="utf-8")
    with reports[0].open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 1
    assert rows[0]["first_seen_date"] == "2026-10-20"
    assert rows[0]["observed_dates"] == "2026-10-20,2026-10-21"


def test_weekly_report_script_can_show_help_without_pythonpath():
    result = subprocess.run(
        [sys.executable, "scripts/weekly_report.py", "--help"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "--timezone" in result.stdout


def test_tuesday_weekly_run_includes_monday_and_tuesday_products(tmp_path):
    db_path = tmp_path / "products.sqlite3"
    with SQLiteStore(db_path) as store:
        store.record_products([_product("B0MONDAY001", datetime(2026, 11, 9, tzinfo=timezone.utc))])
        store.record_products([_product("B0TUESDAY01", datetime(2026, 11, 10, tzinfo=timezone.utc))])

    assert main([
        "--db", str(db_path),
        "--output-dir", str(tmp_path / "reports"),
        "--start", "2026-11-10",
        "--timezone", "UTC",
    ]) == 0

    report = tmp_path / "reports" / "weekly_new_products_2026-11-09_2026-11-15.csv"
    with report.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["asin"] for row in rows} == {"B0MONDAY001", "B0TUESDAY01"}
