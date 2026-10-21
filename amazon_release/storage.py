from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .models import ProductRecord


class SQLiteStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self._initialize()

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                marketplace_id TEXT NOT NULL,
                category_node_id TEXT NOT NULL,
                category_name TEXT NOT NULL,
                asin TEXT NOT NULL,
                rank INTEGER,
                title TEXT NOT NULL,
                product_url TEXT NOT NULL,
                image_url TEXT,
                price REAL,
                currency TEXT,
                rating REAL,
                review_count INTEGER,
                source_url TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                PRIMARY KEY (marketplace_id, asin)
            );
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                marketplace_id TEXT NOT NULL,
                category_node_id TEXT NOT NULL,
                asin TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                rank INTEGER,
                price REAL,
                currency TEXT,
                source_url TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def record_products(self, products: Iterable[ProductRecord]) -> list[ProductRecord]:
        new_products: list[ProductRecord] = []
        for product in products:
            observed_at = product.crawl_time.astimezone(timezone.utc).isoformat()
            key = (product.marketplace_id, product.asin)
            existing = self.connection.execute(
                "SELECT 1 FROM products WHERE marketplace_id=? AND asin=?",
                key,
            ).fetchone()
            if existing is None:
                self.connection.execute(
                    """INSERT INTO products (
                        marketplace_id, category_node_id, category_name, asin, rank, title,
                        product_url, image_url, price, currency, rating, review_count,
                        source_url, first_seen_at, last_seen_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        product.marketplace_id, product.category_node_id, product.category_name,
                        product.asin, product.rank, product.title, product.product_url,
                        product.image_url, product.price, product.currency, product.rating,
                        product.review_count, product.source_url, observed_at, observed_at,
                    ),
                )
                new_products.append(product)
            else:
                self.connection.execute(
                    """UPDATE products SET category_name=?, category_node_id=?, rank=?, title=?, product_url=?,
                       image_url=?, price=?, currency=?, rating=?, review_count=?, source_url=?,
                       last_seen_at=? WHERE marketplace_id=? AND asin=?""",
                    (
                        product.category_name, product.category_node_id, product.rank, product.title, product.product_url,
                        product.image_url, product.price, product.currency, product.rating,
                        product.review_count, product.source_url, observed_at, *key,
                    ),
                )
            self.connection.execute(
                """INSERT INTO observations (
                    marketplace_id, category_node_id, asin, observed_at, rank, price, currency, source_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (product.marketplace_id, product.category_node_id, product.asin, observed_at,
                 product.rank, product.price, product.currency, product.source_url),
            )
        self.connection.commit()
        return new_products

    @staticmethod
    def _csv_row(product: ProductRecord) -> dict[str, object]:
        row = asdict(product)
        row["first_seen_at"] = row.pop("crawl_time").isoformat()
        return row

    @staticmethod
    def _observed_row(product: ProductRecord) -> dict[str, object]:
        row = asdict(product)
        row["observed_at"] = row.pop("crawl_time").isoformat()
        return row

    def export_csv(self, products: Iterable[ProductRecord], path: str | Path) -> Path:
        rows = [self._csv_row(product) for product in products]
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "marketplace_id", "category_name", "category_node_id", "rank", "asin", "title",
            "product_url", "image_url", "price", "currency", "rating", "review_count",
            "source_url", "first_seen_at",
        ]
        with output.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return output

    def export_json(self, products: Iterable[ProductRecord], path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        payload = [self._observed_row(product) for product in products]
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return output

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "SQLiteStore":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
