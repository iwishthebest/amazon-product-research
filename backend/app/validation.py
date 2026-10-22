from __future__ import annotations

import html as html_lib
import re
from collections import defaultdict
from typing import Any, Iterable

from .config import get_marketplace


def _clean_markup(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html_lib.unescape(value).split())


def _first(patterns: Iterable[str], text: str, flags: int = re.I | re.S) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return match.group(1)
    return None


def parse_product_page(
    page_html: str,
    *,
    marketplace_code: str,
    asin: str,
    status_code: int,
    latency_ms: int,
) -> dict[str, Any]:
    marketplace = get_marketplace(marketplace_code)
    title_raw = _first(
        [r'id=["\']productTitle["\'][^>]*>(.*?)</', r'<title[^>]*>(.*?)</title>'],
        page_html,
    )
    title = _clean_markup(title_raw or "")
    price_raw = _first(
        [r'class=["\'][^"\']*a-offscreen[^"\']*["\'][^>]*>\s*([^<]+)', r'"priceAmount"\s*:\s*"?([0-9.,]+)'],
        page_html,
    )
    price = None
    if price_raw:
        match = re.search(r"\d+(?:[.,]\d+)?", price_raw.replace(",", ""))
        price = match.group(0) if match else None
    rating = _first([r'(\d(?:\.\d+)?)\s+out of 5 stars'], page_html)
    review_raw = _first([r'([\d,]+)\s+(?:ratings|reviews|global ratings)'], page_html)
    review_count = int(review_raw.replace(",", "")) if review_raw else None
    rank_raw = _first([r'Best Sellers Rank.{0,300}?#\s*([\d,]+)'], page_html)
    sales_rank = int(rank_raw.replace(",", "")) if rank_raw else None
    return {
        "marketplace_code": marketplace.code,
        "asin": asin,
        "http_status": status_code,
        "title": title or None,
        "price": price,
        "currency": marketplace.currency if price else None,
        "rating": rating,
        "review_count": review_count,
        "sales_rank": sales_rank,
        "sales_metric_type": "unavailable",
        "latency_ms": latency_ms,
    }


def select_sample_rows(
    snapshot: list[dict[str, Any]],
    categories: list[dict[str, Any]],
    *,
    sample_size: int = 50,
) -> list[dict[str, Any]]:
    if sample_size < 2:
        raise ValueError("sample_size must be at least 2 to balance root categories")
    root_names = [str(item["name"]) for item in categories if item.get("depth", 0) == 0]
    if not root_names:
        root_names = list(dict.fromkeys(str(item.get("category_name") or "TEMP") for item in snapshot))[:2]
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in snapshot:
        category = str(row.get("category_name") or "TEMP")
        groups[category].append(row)
    for values in groups.values():
        values.sort(key=lambda item: (item.get("rank") is None, item.get("rank") or 999999, str(item.get("asin"))))
    selected: list[dict[str, Any]] = []
    used: set[str] = set()
    per_root = sample_size // max(1, len(root_names))
    for root in root_names:
        candidates = groups.get(root, [])
        for row in candidates[:per_root]:
            asin = str(row.get("asin") or "").strip().upper()
            if len(asin) != 10 or asin in used:
                continue
            selected.append({
                "asin": asin,
                "sample_category": root,
                "category_name": row.get("category_name"),
                "category_node_id": row.get("category_node_id"),
                "rank": row.get("rank"),
                "title": row.get("title"),
                "source_evidence": "legacy_snapshot_2026-10-21",
            })
            used.add(asin)
    remaining = [row for row in snapshot if str(row.get("asin") or "").strip().upper() not in used]
    remaining.sort(key=lambda item: (item.get("rank") is None, item.get("rank") or 999999, str(item.get("asin"))))
    for row in remaining:
        if len(selected) >= sample_size:
            break
        asin = str(row.get("asin") or "").strip().upper()
        if len(asin) != 10 or asin in used:
            continue
        selected.append({
            "asin": asin,
            "sample_category": str(row.get("category_name") or "TEMP"),
            "category_name": row.get("category_name"),
            "category_node_id": row.get("category_node_id"),
            "rank": row.get("rank"),
            "title": row.get("title"),
            "source_evidence": "legacy_snapshot_2026-10-21",
        })
        used.add(asin)
    return selected[:sample_size]
