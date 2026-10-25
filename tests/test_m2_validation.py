import json

from backend.app.validation import parse_product_page, select_sample_rows
from scripts.run_m2_validation import _extract_asins_from_html, _load_keywords


def test_parse_product_page_extracts_auditable_fields_without_claiming_sales():
    html = """
    <html><head><title>Sample Mat: Amazon.com.au</title></head><body>
      <span id="productTitle"> Sample Mat </span>
      <span id="acrPopover" title="4.4 out of 5 stars">4.4 out of 5 stars</span>
      <span id="acrCustomerReviewText">123 ratings</span>
      <span class="a-price"><span class="a-offscreen">$29.90</span></span>
      <div>Best Sellers Rank: #1,234 in Sports</div>
    </body></html>
    """

    row = parse_product_page(html, marketplace_code="AU", asin="B000000001", status_code=200, latency_ms=123)

    assert row["title"] == "Sample Mat"
    assert row["price"] == "29.90"
    assert row["currency"] == "AUD"
    assert row["rating"] == "4.4"
    assert row["review_count"] == 123
    assert row["sales_rank"] == 1234
    assert row["sales_metric_type"] == "unavailable"
    assert row["latency_ms"] == 123


def test_select_sample_rows_balances_root_categories_and_deduplicates(tmp_path):
    snapshot = [
        {"asin": f"B000000{i:03d}", "category_name": "Pilates" if i % 2 else "Yoga", "rank": i}
        for i in range(1, 9)
    ]
    categories = [
        {"name": "Pilates", "node_id": "p"},
        {"name": "Yoga", "node_id": "y"},
    ]
    rows = select_sample_rows(snapshot, categories, sample_size=6)

    assert len(rows) == 6
    assert {row["sample_category"] for row in rows} == {"Pilates", "Yoga"}
    assert len({row["asin"] for row in rows}) == 6
    assert all(row["source_evidence"] == "legacy_snapshot_2026-10-21" for row in rows)


def test_load_keywords_uses_confirmed_config_and_rejects_unconfirmed(tmp_path):
    categories = [{"name": "Legacy category"}]
    confirmed = tmp_path / "keywords.json"
    confirmed.write_text(
        json.dumps({"status": "confirmed", "categories": {"Mats": ["mat", "yoga"]}, "exclude_terms": ["offer"]}),
        encoding="utf-8",
    )

    terms, source = _load_keywords(confirmed, categories)

    assert terms == ["mat", "yoga", "offer"]
    assert source == str(confirmed)

    unconfirmed = tmp_path / "pending.json"
    unconfirmed.write_text(json.dumps({"status": "candidate", "categories": {"Mats": ["mat"]}}), encoding="utf-8")
    try:
        _load_keywords(unconfirmed, categories)
    except ValueError as exc:
        assert "not confirmed" in str(exc)
    else:
        raise AssertionError("unconfirmed keyword configuration was accepted")


def test_extract_asins_from_amazon_category_html_deduplicates_valid_asins():
    html = '''
    <div data-asin="B000000001"></div>
    <div data-asin="b000000001"></div>
    <a href="/dp/B000000002">item</a>
    <div data-asin="TOO_SHORT"></div>
    '''

    assert _extract_asins_from_html(html) == ["B000000001", "B000000002"]
