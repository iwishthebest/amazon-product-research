from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SalesMetricType(StrEnum):
    ACTUAL = "actual"
    ESTIMATED = "estimated"
    PROXY = "proxy"
    UNAVAILABLE = "unavailable"


class ProductSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    marketplace_code: str
    asin: str
    price: Optional[Decimal] = None
    shipping_cost: Optional[Decimal] = None
    currency: Optional[str] = None
    rating: Optional[Decimal] = None
    review_count: Optional[int] = None
    sales_rank: Optional[int] = None
    estimated_monthly_sales: Optional[int] = None
    sales_metric_type: SalesMetricType
    source: str
    fetched_at: Optional[str] = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.marketplace_code != self.marketplace_code.upper():
            raise ValueError("marketplace_code must be uppercase")
        if len(self.asin) != 10:
            raise ValueError("ASIN must contain 10 characters")


class ProductHistoryPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    marketplace_code: str
    asin: str
    metric_name: str
    metric_value: Decimal
    unit: str
    observed_at: str
    source: str
    confidence: Optional[Decimal] = None
