from datetime import datetime, timezone
import csv

from amazon_release.models import ProductRecord
from amazon_release.storage import SQLiteStore


def product(asin: str) -> ProductRecord:
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
        crawl_time=datetime(2026, 10, 20, 0, 0, tzinfo=timezone.utc),
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
