from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import asdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

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

    @staticmethod
    def _weekly_utc_bounds(start_date: str, end_date: str, timezone_name: str) -> tuple[str, str]:
        local_zone = ZoneInfo(timezone_name)
        start = datetime.combine(date.fromisoformat(start_date), time.min, tzinfo=local_zone)
        end = datetime.combine(date.fromisoformat(end_date), time.min, tzinfo=local_zone)
        end = end + timedelta(days=1)
        return start.astimezone(timezone.utc).isoformat(), end.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _local_date(value: str | None, timezone_name: str) -> str:
        if not value:
            return ""
        observed = datetime.fromisoformat(value)
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        return observed.astimezone(ZoneInfo(timezone_name)).date().isoformat()

    def weekly_products(
        self,
        start_date: str,
        end_date: str,
        *,
        timezone_name: str = "UTC",
    ) -> list[dict[str, object]]:
        """Return one row per product observed during the inclusive local date range."""
        utc_start, utc_end = self._weekly_utc_bounds(start_date, end_date, timezone_name)
        rows = self.connection.execute(
            """WITH scoped AS (
                    SELECT o.id, o.marketplace_id, o.category_node_id, p.category_name, o.asin,
                           o.observed_at, o.rank, p.title, p.product_url, p.image_url,
                           o.price, o.currency, p.rating, p.review_count, o.source_url,
                           p.first_seen_at,
                           ROW_NUMBER() OVER (
                               PARTITION BY o.marketplace_id, o.asin
                               ORDER BY o.observed_at DESC, o.id DESC
                           ) AS latest_rank
                      FROM observations o
                      JOIN products p
                        ON p.marketplace_id=o.marketplace_id AND p.asin=o.asin
                     WHERE o.observed_at >= ? AND o.observed_at < ?
                ), aggregates AS (
                    SELECT marketplace_id, asin,
                           MIN(observed_at) AS week_first_observed_at,
                           COUNT(*) AS observation_count,
                           GROUP_CONCAT(observed_at, '|') AS observed_at_values
                      FROM scoped
                     GROUP BY marketplace_id, asin
                )
                SELECT latest.observed_at, latest.marketplace_id, latest.category_node_id,
                       latest.category_name, latest.asin, latest.rank, latest.title,
                       latest.product_url, latest.image_url, latest.price, latest.currency,
                       latest.rating, latest.review_count, latest.source_url,
                       latest.first_seen_at, aggregates.week_first_observed_at,
                       aggregates.observation_count, aggregates.observed_at_values
                  FROM scoped latest
                  JOIN aggregates
                    ON aggregates.marketplace_id=latest.marketplace_id
                   AND aggregates.asin=latest.asin
                 WHERE latest.latest_rank=1
                 ORDER BY latest.category_name,
                          CASE WHEN latest.rank IS NULL THEN 999999 ELSE latest.rank END,
                          latest.asin""",
            (utc_start, utc_end),
        ).fetchall()
        products: list[dict[str, object]] = []
        for row in rows:
            product = dict(row)
            observed_values = str(product.pop("observed_at_values") or "").split("|")
            local_dates = sorted({
                self._local_date(value, timezone_name)
                for value in observed_values
                if value
            })
            product["first_seen_date"] = self._local_date(product.get("first_seen_at"), timezone_name)
            product["week_first_observed_date"] = self._local_date(
                product.get("week_first_observed_at"), timezone_name
            )
            product["observed_dates"] = ",".join(local_dates)
            products.append(product)
        return products

    def export_weekly_csv(
        self,
        start_date: str,
        end_date: str,
        path: str | Path,
        *,
        timezone_name: str = "UTC",
    ) -> Path:
        rows = self.weekly_products(start_date, end_date, timezone_name=timezone_name)
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        fields = [
            "marketplace_id", "asin", "title", "category_name", "category_node_id",
            "first_seen_date", "first_seen_at", "week_first_observed_date", "week_first_observed_at",
            "observed_dates", "observation_count", "observed_at", "rank", "price",
            "currency", "rating", "review_count", "product_url", "image_url", "source_url",
        ]
        with output.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        return output

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "SQLiteStore":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
