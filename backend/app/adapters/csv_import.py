from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from ..config import get_marketplace
from ..domain import ProductSnapshot, SalesMetricType


@dataclass(frozen=True)
class CsvImportResult:
    items: list[dict[str, Any]]
    errors: list[dict[str, Any]]


def parse_product_csv(content: bytes, *, marketplace_code: str, source: str = "csv") -> CsvImportResult:
    marketplace = get_marketplace(marketplace_code)
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    items: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for line_number, row in enumerate(reader, start=2):
        try:
            metric_type = row.get("sales_metric_type", "").strip().lower()
            if not metric_type:
                raise ValueError("sales_metric_type is required; use actual, estimated, proxy or unavailable")
            price = _decimal(row.get("price"))
            currency = (row.get("currency") or marketplace.currency).strip().upper()
            if currency != marketplace.currency:
                raise ValueError(f"currency must be {marketplace.currency} for {marketplace.code}")
            snapshot = ProductSnapshot(
                marketplace_code=marketplace.code,
                asin=(row.get("asin") or "").strip().upper(),
                price=price,
                currency=currency,
                estimated_monthly_sales=_integer(row.get("estimated_monthly_sales")),
                sales_metric_type=SalesMetricType(metric_type),
                source=source,
            )
            payload = snapshot.model_dump(mode="json")
            payload["title"] = (row.get("title") or "").strip()
            items.append(payload)
        except (ValueError, InvalidOperation) as exc:
            errors.append({"line": line_number, "message": str(exc)})
    return CsvImportResult(items=items, errors=errors)


def _decimal(value: str | None) -> Decimal | None:
    if value is None or not value.strip():
        return None
    return Decimal(value.strip())


def _integer(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    return int(value.strip())
