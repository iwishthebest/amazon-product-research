import json
from pathlib import Path

import pytest

from amazon_release.gui import (
    build_gui_config,
    discover_result_files,
    discover_run_history,
    export_product_rows_csv,
    filter_product_rows,
    load_result_rows,
    run_gui_job,
    sort_product_rows,
)


def test_build_gui_config_validates_numeric_settings():
    config = build_gui_config({
        "config_path": "",
        "delay_seconds": "0.5",
        "timeout_seconds": "15",
        "max_retries": "2",
        "max_pages": "3",
        "max_category_depth": "1",
        "timezone": "Asia/Shanghai",
    })

    assert config["delay_seconds"] == 0.5
    assert config["timeout_seconds"] == 15.0
    assert config["max_retries"] == 2
    assert config["max_pages"] == 3
    assert config["max_category_depth"] == 1
    assert config["timezone"] == "Asia/Shanghai"


def test_build_gui_config_rejects_invalid_positive_number():
    with pytest.raises(ValueError, match="max_pages"):
        build_gui_config({"config_path": "", "max_pages": "0"})


def test_run_gui_job_reuses_fixture_pipeline(tmp_path):
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    (fixture_dir / "category_5044228051.html").write_text(
        '<div data-asin="B0ABC12345"><a href="/dp/B0ABC12345"><span class="p13n-sc-truncate">Pilates Ring</span></a></div>',
        encoding="utf-8",
    )
    config = {
        "marketplace_id": "A39IBJ37TRP1C6",
        "allowed_domain": "amazon.com.au",
        "timezone": "Asia/Shanghai",
        "roots": [{
            "name": "Pilates",
            "node_id": "5044228051",
            "url": "https://www.amazon.com.au/gp/new-releases/sporting-goods/5044228051",
        }],
        "discover_subcategories": False,
        "delay_seconds": 0,
    }

    result = run_gui_job(config, fixture_dir, tmp_path / "db.sqlite3", tmp_path / "reports")

    assert result["products"] == 1
    assert (tmp_path / "reports").exists()
    assert Path(result["html"]).exists()


def test_discover_and_load_latest_result_files(tmp_path):
    output = tmp_path / "reports"
    output.mkdir()
    snapshot = output / "snapshot_2026-10-21.json"
    snapshot.write_text(json.dumps([{
        "asin": "B0ABC12345",
        "title": "Pilates Ring 4.5 out of 5 stars",
        "category_name": "Pilates",
        "rank": 2,
        "rating": 4.5,
        "review_count": 12,
        "product_url": "https://www.amazon.com.au/dp/B0ABC12345",
    }]), encoding="utf-8")
    csv_path = output / "new_products_2026-10-21.csv"
    csv_path.write_text("asin\nB0ABC12345\n", encoding="utf-8-sig")
    html_path = output / "release_2026-10-21.html"
    html_path.write_text("<html></html>", encoding="utf-8")

    found = discover_result_files(output)
    rows = load_result_rows(found["snapshot"], found["new_products"])

    assert found["html"] == html_path
    assert rows[0]["asin"] == "B0ABC12345"
    assert rows[0]["is_new"] is True
    assert rows[0]["title"] == "Pilates Ring"


def _sample_rows():
    return [
        {"asin": "A1", "title": "Blue Pilates Ring", "category_name": "Pilates", "score": 82, "is_new": True, "rank": 2},
        {"asin": "A2", "title": "Yoga Mat", "category_name": "Yoga", "score": 45, "is_new": False, "rank": 8},
        {"asin": "A3", "title": "Red Pilates Ball", "category_name": "Pilates", "score": 68, "is_new": True, "rank": 5},
    ]


def test_filter_and_sort_product_rows_are_composable_without_mutation():
    rows = _sample_rows()

    filtered = filter_product_rows(rows, query="pilates", category="Pilates", new_only=True, min_score=70)
    sorted_rows = sort_product_rows(rows, key="score", descending=True)

    assert [row["asin"] for row in filtered] == ["A1"]
    assert [row["asin"] for row in sorted_rows] == ["A1", "A3", "A2"]
    assert [row["asin"] for row in rows] == ["A1", "A2", "A3"]


def test_discover_run_history_and_export_csv(tmp_path):
    output = tmp_path / "reports"
    output.mkdir()
    (output / "snapshot_2026-10-20.json").write_text("[]", encoding="utf-8")
    (output / "new_products_2026-10-20.csv").write_text("asin\n", encoding="utf-8-sig")
    (output / "release_2026-10-20.html").write_text("<html></html>", encoding="utf-8")
    (output / "snapshot_2026-10-21.json").write_text("[]", encoding="utf-8")

    history = discover_run_history(output)
    exported = export_product_rows_csv(_sample_rows(), output / "filtered.csv")

    assert history[0]["date"] == "2026-10-21"
    assert history[0]["has_html"] is False
    assert history[1]["has_html"] is True
    assert exported.exists()
    assert "Blue Pilates Ring" in exported.read_text(encoding="utf-8-sig")


def test_gui_smoke_exposes_polished_navigation():
    import tkinter as tk

    from amazon_release.gui import AmazonReleaseApp

    root = tk.Tk()
    root.withdraw()
    app = AmazonReleaseApp(root)
    try:
        assert app.theme_name == "seller-light"
        tab_titles = [app.notebook.tab(tab, "text") for tab in app.notebook.tabs()]
        assert tab_titles == ["概览", "商品工作台", "运行历史", "设置"]
        assert app.start_button.cget("text") == "开始采集"
    finally:
        root.destroy()
