from amazon_release.report import build_product_view, build_seller_analysis, render_html


def test_build_seller_analysis_separates_heat_signal_from_sales_claim():
    hot = build_seller_analysis({"rank": 1, "rating": 4.8, "review_count": 12}, is_new=True)
    cold = build_seller_analysis({"rank": 80, "rating": 3.6, "review_count": 900}, is_new=False)

    assert hot["score"] > cold["score"]
    assert hot["heat_label"] == "高热度信号"
    assert hot["sales_claim"] == "未确认销量"
    assert "评论壁垒较低" in hot["competition"]


def test_build_seller_analysis_produces_actionable_improvement_advice():
    analysis = build_seller_analysis({"rank": 20, "rating": 3.8, "review_count": 18, "price": 29.99}, is_new=True)

    assert "低评分" in analysis["improvement"]
    assert "评论量较低" in analysis["improvement"]


def test_build_product_view_cleans_metadata_and_recovers_price():
    view = build_product_view({
        "asin": "B0ABC12345",
        "title": "Pilates Ring 3.6 out of 5 stars 4 1 offer from $39.99",
        "price": None,
        "currency": None,
        "image_url": None,
        "category_name": "Pilates",
    }, new_asins={"B0ABC12345"})

    assert view["title"] == "Pilates Ring"
    assert view["price"] == "39.99"
    assert view["currency"] == "AUD"
    assert view["is_new"] is True
    assert "B0ABC12345" in view["image_url"]


def test_render_html_contains_category_cards_and_safe_links(tmp_path):
    output = tmp_path / "release.html"
    render_html([
        {"asin": "B0ABC12345", "title": "Pilates <Ring>", "category_name": "Pilates", "price": 29.99,
         "currency": "AUD", "image_url": None, "product_url": "https://www.amazon.com.au/dp/B0ABC12345"}
    ], output, report_date="2026-10-20", new_asins={"B0ABC12345"})

    html = output.read_text(encoding="utf-8")
    assert "Amazon AU New Releases" in html
    assert "Pilates" in html
    assert "B0ABC12345" in html
    assert "&lt;Ring&gt;" in html
    assert "New today" in html


def test_render_html_contains_seller_dashboard_fields(tmp_path):
    output = tmp_path / "release.html"
    render_html([
        {"asin": "B0ABC12345", "title": "Pilates Ring", "category_name": "Pilates", "rank": 1,
         "price": 29.99, "currency": "AUD", "rating": 4.8, "review_count": 12,
         "image_url": "images/B0ABC12345.jpg", "product_url": "https://www.amazon.com.au/dp/B0ABC12345",
         "observed_at": "2026-10-20T23:00:00+08:00"}
    ], output, report_date="2026-10-20", new_asins={"B0ABC12345"})

    html = output.read_text(encoding="utf-8")
    assert "产品开发选品分析" in html
    assert "小卖家" not in html
    assert "新品榜热度信号（非销量确认）" in html
    assert "机会评分" in html
    assert "重点候选" in html
    assert "竞品对比" in html
    assert "卡片视图" in html
    assert "对比表" in html
    assert "sortTable" in html
    assert "改进方向" in html
    assert "评论壁垒较低" in html
