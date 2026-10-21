from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class CategoryLink:
    name: str
    node_id: str
    url: str
    parent_node_id: Optional[str] = None
    depth: int = 0


@dataclass(frozen=True)
class ProductRecord:
    marketplace_id: str
    category_name: str
    category_node_id: str
    rank: Optional[int]
    asin: str
    title: str
    product_url: str
    image_url: Optional[str]
    price: Optional[float]
    currency: Optional[str]
    rating: Optional[float]
    review_count: Optional[int]
    source_url: str
    crawl_time: datetime
