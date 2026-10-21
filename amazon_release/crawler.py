from __future__ import annotations

import time
from collections import deque
from typing import Any, Protocol

from .client import validate_amazon_url
from .models import CategoryLink, ProductRecord
from .parser import extract_category_links, extract_next_page_url, parse_product_cards


class PageFetcher(Protocol):
    def fetch(self, url: str) -> str: ...


class NewReleaseCrawler:
    def __init__(
        self,
        fetcher: PageFetcher,
        *,
        marketplace_id: str = "A39IBJ37TRP1C6",
        allowed_domain: str = "amazon.com.au",
        delay_seconds: float = 1.0,
        max_pages: int = 10,
        max_category_depth: int = 2,
    ) -> None:
        self.fetcher = fetcher
        self.marketplace_id = marketplace_id
        self.allowed_domain = allowed_domain
        self.delay_seconds = max(0.0, delay_seconds)
        self.max_pages = max(1, max_pages)
        self.max_category_depth = max(0, max_category_depth)

    def _validate_url(self, url: str) -> None:
        validate_amazon_url(url, self.allowed_domain)

    def _sleep(self) -> None:
        if self.delay_seconds:
            time.sleep(self.delay_seconds)

    @staticmethod
    def _category(value: CategoryLink | dict[str, Any], depth: int = 0) -> CategoryLink:
        if isinstance(value, CategoryLink):
            return value
        return CategoryLink(
            name=str(value["name"]),
            node_id=str(value["node_id"]),
            url=str(value["url"]),
            parent_node_id=value.get("parent_node_id"),
            depth=int(value.get("depth", depth)),
        )

    def discover_categories(self, roots: list[CategoryLink]) -> list[CategoryLink]:
        categories: list[CategoryLink] = []
        seen: set[str] = set()
        queue = deque(roots)
        while queue:
            category = queue.popleft()
            if category.node_id in seen:
                continue
            self._validate_url(category.url)
            seen.add(category.node_id)
            categories.append(category)
            if category.depth >= self.max_category_depth:
                continue
            self._sleep()
            html = self.fetcher.fetch(category.url)
            for child in extract_category_links(html, category.url, category.node_id, category.depth):
                if child.node_id not in seen:
                    queue.append(child)
        return categories

    def crawl_category(self, category: CategoryLink) -> list[ProductRecord]:
        page_url = category.url
        seen_pages: set[str] = set()
        products: list[ProductRecord] = []
        for _ in range(self.max_pages):
            self._validate_url(page_url)
            if page_url in seen_pages:
                break
            seen_pages.add(page_url)
            self._sleep()
            html = self.fetcher.fetch(page_url)
            products.extend(parse_product_cards(
                html,
                source_url=page_url,
                category_name=category.name,
                category_node_id=category.node_id,
                marketplace_id=self.marketplace_id,
            ))
            next_url = extract_next_page_url(html, page_url)
            if not next_url:
                break
            page_url = next_url
        return products

    def run(
        self,
        roots: list[CategoryLink | dict[str, Any]],
        *,
        discover_subcategories: bool = True,
    ) -> tuple[list[CategoryLink], list[ProductRecord]]:
        normalized = [self._category(root) for root in roots]
        categories = self.discover_categories(normalized) if discover_subcategories else normalized
        products: list[ProductRecord] = []
        seen: set[tuple[str, str, str]] = set()
        for category in categories:
            for product in self.crawl_category(category):
                key = (product.marketplace_id, product.asin)
                if key not in seen:
                    seen.add(key)
                    products.append(product)
        return categories, products
