from amazon_release.parser import (
    extract_category_links,
    extract_next_page_url,
    parse_product_cards,
)


HTML = """
<html><body>
  <nav>
    <a href="/gp/new-releases/sporting-goods/5044228051">Pilates</a>
    <a href="/gp/new-releases/sporting-goods/5044231051">Yoga</a>
    <a href="/gp/new-releases/sporting-goods/5044228051">Duplicate</a>
  </nav>
  <div data-asin="B0ABC12345" class="zg-grid-general-faceout">
    <span class="zg-bdg-text">#1</span>
    <a class="a-link-normal" href="/dp/B0ABC12345"><span class="p13n-sc-truncate">Pilates Ring</span></a>
    <img src="https://images.example/ring.jpg" />
    <span class="a-price"><span class="a-offscreen">$29.99</span></span>
    <span class="a-icon-alt">4.5 out of 5 stars</span>
    <a class="a-size-small">12</a>
  </div>
  <a aria-label="Next page" href="/gp/new-releases/sporting-goods/5044228051?pg=2">Next</a>
</body></html>
"""


def test_extract_category_links_deduplicates_and_keeps_node_ids():
    links = extract_category_links(
        HTML,
        "https://www.amazon.com.au/gp/new-releases/sporting-goods/5043942051",
        parent_node_id="5043942051",
    )

    assert [(link.name, link.node_id) for link in links] == [
        ("Pilates", "5044228051"),
        ("Yoga", "5044231051"),
    ]


def test_extract_category_links_prefers_current_parent_marker_when_present():
    html = """
    <a href="/gp/new-releases/sporting-goods/11111111/ref=zg_bsnr_nav_sporting-goods_3_5044228051">Reformers</a>
    <a href="/gp/new-releases/sporting-goods/22222222/ref=zg_bsnr_nav_sporting-goods_2_5043942051">Sports sibling</a>
    """
    links = extract_category_links(
        html,
        "https://www.amazon.com.au/gp/new-releases/sporting-goods/5044228051",
        parent_node_id="5044228051",
    )
    assert [(link.name, link.node_id) for link in links] == [("Reformers", "11111111")]


def test_parse_product_cards_extracts_rank_and_product_fields():
    products = parse_product_cards(
        HTML,
        source_url="https://www.amazon.com.au/gp/new-releases/sporting-goods/5044228051",
        category_name="Pilates",
        category_node_id="5044228051",
    )

    assert len(products) == 1
    product = products[0]
    assert product.asin == "B0ABC12345"
    assert product.title == "Pilates Ring"
    assert product.rank == 1
    assert product.price == 29.99
    assert product.currency == "AUD"
    assert product.rating == 4.5
    assert product.review_count == 12


def test_parse_product_cards_can_find_asin_from_product_link_without_data_attribute():
    html = '<div class="zg-grid-general-faceout"><a href="/dp/B0LINK1234"><span class="p13n-sc-truncate">Linked product</span></a></div>'
    products = parse_product_cards(
        html,
        source_url="https://www.amazon.com.au/gp/new-releases/sporting-goods/5044228051",
        category_name="Pilates",
        category_node_id="5044228051",
    )
    assert [product.asin for product in products] == ["B0LINK1234"]


def test_parser_does_not_emit_external_product_or_image_urls_and_does_not_fake_rank():
    html = '<div class="zg-grid-general-faceout"><a href="https://evil.example/dp/B0LINK1234"><span class="p13n-sc-truncate">Linked product</span></a><img src="https://evil.example/image.jpg"></div>'
    product = parse_product_cards(
        html,
        source_url="https://www.amazon.com.au/gp/new-releases/sporting-goods/5044228051",
        category_name="Pilates",
        category_node_id="5044228051",
    )[0]
    assert product.product_url == "https://www.amazon.com.au/dp/B0LINK1234"
    assert product.image_url is None
    assert product.rank is None


def test_extract_next_page_url_returns_absolute_url():
    assert extract_next_page_url(
        HTML, "https://www.amazon.com.au/gp/new-releases/sporting-goods/5044228051"
    ) == "https://www.amazon.com.au/gp/new-releases/sporting-goods/5044228051?pg=2"
