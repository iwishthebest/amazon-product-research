from datetime import datetime, timezone
import csv

from amazon_release.models import ProductRecord
from amazon_release.storage import SQLiteStore


def product(asin: str, *, crawl_time: datetime | None = None) -> ProductRecord:
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
        crawl_time=crawl_time or datetime(2026, 10, 20, 0, 0, tzinfo=timezone.utc),
    )


def test_first_observation_is_new_and_repeat_is_not(tmp_path):
    store = SQLiteStore(tmp_path / "products.sqlite3")
    try:
        assert [item.asin for item in store.record_products([product("B0ABC12345")])] == ["B0ABC12345"]
        assert store.record_products([product("B0ABC12345")]) == []
        assert [item.asin for item in store.record_products([product("B0DEF67890")])] == ["B0DEF67890"]
    finally:
        store.close()


def test_export_csv_writes_expected_columns(tmp_path):
    store = SQLiteStore(tmp_path / "products.sqlite3")
    try:
        rows = store.record_products([product("B0ABC12345")])
        output = tmp_path / "daily.csv"
        store.export_csv(rows, output)
    finally:
        store.close()

    with output.open(newline="", encoding="utf-8-sig") as handle:
        record = next(csv.DictReader(handle))
    assert record["asin"] == "B0ABC12345"
    assert record["first_seen_at"]
    assert record["marketplace_id"] == "A39IBJ37TRP1C6"


def test_export_json_labels_capture_time_as_observed_at(tmp_path):
    store = SQLiteStore(tmp_path / "products.sqlite3")
    try:
        output = tmp_path / "snapshot.json"
        store.export_json([product("B0ABC12345")], output)
    finally:
        store.close()
    import json
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "observed_at" in payload[0]
    assert "first_seen_at" not in payload[0]


def test_weekly_export_merges_daily_observations_and_labels_first_seen_date(tmp_path):
    store = SQLiteStore(tmp_path / "products.sqlite3")
    try:
        store.record_products([product("B0ABC12345", crawl_time=datetime(2026, 10, 20, tzinfo=timezone.utc))])
        store.record_products([product("B0ABC12345", crawl_time=datetime(2026, 10, 21, tzinfo=timezone.utc))])
        output = tmp_path / "weekly.csv"
        store.export_weekly_csv("2026-10-19", "2026-10-25", output)
    finally:
        store.close()
    rows = list(csv.DictReader(output.open(newline="", encoding="utf-8-sig")))
    assert len(rows) == 1
    assert rows[0]["category_name"] == "Pilates"
    assert rows[0]["observed_at"].startswith("2026-10-21")
    assert rows[0]["first_seen_date"] == "2026-10-20"
    assert rows[0]["week_first_observed_date"] == "2026-10-20"
    assert rows[0]["observed_dates"] == "2026-10-20,2026-10-21"
    assert rows[0]["observation_count"] == "2"


def test_weekly_export_uses_local_timezone_for_week_boundaries(tmp_path):
    store = SQLiteStore(tmp_path / "products.sqlite3")
    try:
        store.record_products([
            product("B0ABC12345", crawl_time=datetime(2026, 10, 26, 0, 30, tzinfo=timezone.utc)),
        ])
        output = tmp_path / "weekly.csv"
        store.export_weekly_csv(
            "2026-10-19",
            "2026-10-25",
            output,
            timezone_name="America/New_York",
        )
    finally:
        store.close()
    rows = list(csv.DictReader(output.open(newline="", encoding="utf-8-sig")))
    assert len(rows) == 1
    assert rows[0]["first_seen_date"] == "2026-10-25"
    assert rows[0]["observed_dates"] == "2026-10-25"
