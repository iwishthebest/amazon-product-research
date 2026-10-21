from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Callable, Iterable, Optional
from urllib.parse import urljoin, urlparse

from .models import CategoryLink, ProductRecord


_NODE_RE = re.compile(r"/(?:gp/)?new-releases/[^/?#]*/(\d{4,})", re.I)
_ASIN_RE = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?#]|$)", re.I)


@dataclass
class _Node:
    tag: str
    attrs: dict[str, str]
    parent: Optional["_Node"] = None
    children: list["_Node"] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)

    def text(self) -> str:
        parts = list(self.text_parts)
        for child in self.children:
            parts.append(child.text())
        return " ".join(" ".join(parts).split())


class _TreeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("root", {})
        self.current = self.root

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        node = _Node(tag.lower(), {key.lower(): value or "" for key, value in attrs}, self.current)
        self.current.children.append(node)
        if tag.lower() not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.current = node

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        cursor = self.current
        while cursor is not self.root:
            if cursor.tag == tag.lower():
                self.current = cursor.parent or self.root
                return
            cursor = cursor.parent or self.root

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.current.text_parts.append(data)


def _parse(html: str) -> _Node:
    parser = _TreeParser()
    parser.feed(html)
    parser.close()
    return parser.root


def _walk(node: _Node) -> Iterable[_Node]:
    for child in node.children:
        yield child
        yield from _walk(child)


def _class_tokens(node: _Node) -> set[str]:
    return set(node.attrs.get("class", "").split())


def _find(node: _Node, predicate: Callable[[_Node], bool]) -> Optional[_Node]:
    return next((candidate for candidate in _walk(node) if predicate(candidate)), None)


def _find_all(node: _Node, predicate: Callable[[_Node], bool]) -> list[_Node]:
    return [candidate for candidate in _walk(node) if predicate(candidate)]


def _absolute_url(href: str, base_url: str) -> str:
    return urljoin(base_url, href.strip())


def _safe_product_url(href: str, asin: str, base_url: str) -> str:
    candidate = _absolute_url(href, base_url)
    host = urlparse(candidate).netloc.lower()
    if host not in {"amazon.com.au", "www.amazon.com.au"}:
        return _absolute_url(f"/dp/{asin}", base_url)
    return candidate


def _safe_image_url(value: str | None) -> str | None:
    if not value:
        return None
    host = urlparse(value).netloc.lower()
    if host == "m.media-amazon.com" or host.endswith(".media-amazon.com") or host.endswith(".images-amazon.com"):
        return value
    return None


def extract_category_links(html: str, base_url: str, parent_node_id: str | None = None, depth: int = 0) -> list[CategoryLink]:
    """Extract unique New Releases category links from a page."""
    root = _parse(html)
    candidates: list[tuple[str, str, str, bool]] = []
    for anchor in _find_all(root, lambda node: node.tag == "a" and "/new-releases/" in node.attrs.get("href", "").lower()):
        href = anchor.attrs.get("href", "")
        match = _NODE_RE.search(urlparse(href).path)
        if not match:
            continue
        node_id = match.group(1)
        if parent_node_id and node_id == parent_node_id:
            continue
        name = anchor.text().strip()
        if not name:
            continue
        parent_marker = bool(parent_node_id and f"_{parent_node_id}" in href)
        candidates.append((name, node_id, _absolute_url(href, base_url), parent_marker))
    if parent_node_id and any(candidate[3] for candidate in candidates):
        candidates = [candidate for candidate in candidates if candidate[3]]
    result: list[CategoryLink] = []
    seen: set[str] = set()
    for name, node_id, url, _ in candidates:
        if node_id in seen:
            continue
        seen.add(node_id)
        result.append(CategoryLink(name, node_id, url, parent_node_id, depth + 1))
    return result


def _extract_asin(node: _Node) -> Optional[str]:
    value = node.attrs.get("data-asin", "").strip().upper()
    if re.fullmatch(r"[A-Z0-9]{10}", value):
        return value
    for anchor in _find_all(node, lambda child: child.tag == "a"):
        match = _ASIN_RE.search(anchor.attrs.get("href", ""))
        if match:
            return match.group(1).upper()
    return None


def _parse_float(text: str) -> Optional[float]:
    match = re.search(r"\d+(?:[.,]\d+)?", text.replace(",", ""))
    return float(match.group(0)) if match else None


def _parse_int(text: str) -> Optional[int]:
    match = re.search(r"\d[\d,]*", text)
    return int(match.group(0).replace(",", "")) if match else None


def _first_text(node: _Node, predicate: Callable[[_Node], bool]) -> str:
    found = _find(node, predicate)
    return found.text().strip() if found else ""


def parse_product_cards(
    html: str,
    source_url: str,
    category_name: str,
    category_node_id: str,
    marketplace_id: str = "A39IBJ37TRP1C6",
    crawl_time=None,
) -> list[ProductRecord]:
    """Parse product cards while tolerating minor Amazon markup changes."""
    from datetime import datetime, timezone

    root = _parse(html)
    cards: list[_Node] = []
    seen_asins: set[str] = set()
    for node in _walk(root):
        classes = _class_tokens(node)
        if "data-asin" not in node.attrs and not (classes & {"zg-grid-general-faceout", "gridItemRoot"}):
            continue
        asin = _extract_asin(node)
        if not asin or asin in seen_asins:
            continue
        seen_asins.add(asin)
        cards.append(node)

    products: list[ProductRecord] = []
    for index, card in enumerate(cards, 1):
        asin = _extract_asin(card)
        if not asin:
            continue
        title_node = _find(card, lambda node: (
            bool(_class_tokens(node) & {"p13n-sc-truncate", "a-size-base-plus"})
            or any(token.startswith("p13n-sc") for token in _class_tokens(node))
        ) and bool(node.text().strip()))
        title = title_node.text().strip() if title_node else ""
        if not title:
            title = _first_text(card, lambda node: node.tag == "a" and "/dp/" in node.attrs.get("href", ""))
        href_node = _find(card, lambda node: node.tag == "a" and _ASIN_RE.search(node.attrs.get("href", "")) is not None)
        product_url = _safe_product_url(href_node.attrs.get("href", ""), asin, source_url) if href_node else _absolute_url(f"/dp/{asin}", source_url)
        image_node = _find(card, lambda node: node.tag == "img" and bool(node.attrs.get("src") or node.attrs.get("data-src")))
        image_url = _safe_image_url((image_node.attrs.get("src") or image_node.attrs.get("data-src")) if image_node else None)
        price_text = _first_text(card, lambda node: "a-price" in _class_tokens(node) or "a-offscreen" in _class_tokens(node))
        rating_text = _first_text(card, lambda node: "a-icon-alt" in _class_tokens(node))
        review_text = _first_text(card, lambda node: "a-size-small" in _class_tokens(node) and bool(re.search(r"\d", node.text())))
        rank_text = _first_text(card, lambda node: "zg-bdg-text" in _class_tokens(node))
        products.append(ProductRecord(
            marketplace_id=marketplace_id,
            category_name=category_name,
            category_node_id=category_node_id,
            rank=_parse_int(rank_text),
            asin=asin,
            title=title,
            product_url=product_url,
            image_url=image_url,
            price=_parse_float(price_text),
            currency="AUD" if "$" in price_text else None,
            rating=_parse_float(rating_text),
            review_count=_parse_int(review_text),
            source_url=source_url,
            crawl_time=crawl_time or datetime.now(timezone.utc),
        ))
    return products


def extract_next_page_url(html: str, base_url: str) -> Optional[str]:
    root = _parse(html)
    anchors = _find_all(root, lambda node: node.tag == "a" and bool(node.attrs.get("href")))
    for anchor in anchors:
        label = " ".join([anchor.attrs.get("aria-label", ""), anchor.text()]).lower()
        if "next" in label or anchor.attrs.get("rel", "").lower() == "next":
            return _absolute_url(anchor.attrs["href"], base_url)
    return None
