from dataclasses import dataclass

import pytest

from amazon_release.client import AmazonFetchError, validate_amazon_url
from amazon_release.crawler import NewReleaseCrawler


ROOT_URL = "https://www.amazon.com.au/gp/new-releases/sporting-goods/5043942051"
PILATES_URL = "https://www.amazon.com.au/gp/new-releases/sporting-goods/5044228051"


ROOT_HTML = """
<a href="/gp/new-releases/sporting-goods/5044228051">Pilates</a>
<a href="/gp/new-releases/sporting-goods/5044228051">Pilates again</a>
"""
PRODUCT_HTML = """
<div data-asin="B0ABC12345"><a href="/dp/B0ABC12345"><span class="p13n-sc-truncate">Ring</span></a></div>
"""


@dataclass
class FakeFetcher:
    pages: dict[str, str]
    calls: list[str]

    def fetch(self, url: str) -> str:
        self.calls.append(url)
        if url not in self.pages:
            raise AmazonFetchError(f"missing fixture: {url}")
        return self.pages[url]


def test_validate_amazon_url_rejects_other_domains():
    with pytest.raises(ValueError):
        validate_amazon_url("https://example.com/gp/new-releases/sporting-goods/1")


def test_crawler_discovers_categories_follows_pages_and_deduplicates_products():
    fetcher = FakeFetcher(
        {
            ROOT_URL: ROOT_HTML,
            PILATES_URL: PRODUCT_HTML + '<a aria-label="Next page" href="?pg=2">Next</a>',
            "https://www.amazon.com.au/gp/new-releases/sporting-goods/5044228051?pg=2": PRODUCT_HTML,
        },
        [],
    )
    crawler = NewReleaseCrawler(fetcher, delay_seconds=0, max_pages=5)

    categories, products = crawler.run(
        [
            {
                "name": "Pilates",
                "node_id": "5044228051",
                "url": PILATES_URL,
            }
        ],
        discover_subcategories=False,
    )

    assert len(categories) == 1
    assert len(products) == 1
    assert products[0].asin == "B0ABC12345"
    assert fetcher.calls[-1].endswith("pg=2")


def test_crawler_deduplicates_same_asin_across_categories():
    yoga_url = "https://www.amazon.com.au/gp/new-releases/sporting-goods/5044231051"
    fetcher = FakeFetcher({PILATES_URL: PRODUCT_HTML, yoga_url: PRODUCT_HTML}, [])
    crawler = NewReleaseCrawler(fetcher, delay_seconds=0)
    _, products = crawler.run([
        {"name": "Pilates", "node_id": "5044228051", "url": PILATES_URL},
        {"name": "Yoga", "node_id": "5044231051", "url": yoga_url},
    ], discover_subcategories=False)
    assert [product.asin for product in products] == ["B0ABC12345"]
