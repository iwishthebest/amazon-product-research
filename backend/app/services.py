from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from .domain import ProductSnapshot


CENT = Decimal("0.01")
SCORE_STEP = Decimal("0.01")
WEIGHTS = {
    "demand": Decimal("0.25"),
    "trend": Decimal("0.20"),
    "profit": Decimal("0.25"),
    "competition": Decimal("0.20"),
    "risk": Decimal("0.10"),
}


@dataclass(frozen=True)
class ProfitResult:
    revenue: Decimal
    total_cost: Decimal
    profit: Decimal
    profit_margin: Decimal
    roi: Decimal
    is_scenario: bool = True


@dataclass(frozen=True)
class ScoreResult:
    score: Decimal
    confidence: Decimal
    known_components: tuple[str, ...]
    missing_components: tuple[str, ...]


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_profit(
    *,
    price: Decimal,
    purchase_cost: Decimal,
    inbound_shipping: Decimal = Decimal("0"),
    platform_fee: Decimal = Decimal("0"),
    fba_fee: Decimal = Decimal("0"),
    packaging_cost: Decimal = Decimal("0"),
    ad_cost: Decimal = Decimal("0"),
    return_reserve: Decimal = Decimal("0"),
    tax_cost: Decimal = Decimal("0"),
) -> ProfitResult:
    costs = (
        purchase_cost,
        inbound_shipping,
        platform_fee,
        fba_fee,
        packaging_cost,
        ad_cost,
        return_reserve,
        tax_cost,
    )
    revenue = _money(price)
    total_cost = _money(sum((Decimal(value) for value in costs), Decimal("0")))
    profit = _money(revenue - total_cost)
    margin = (profit / revenue).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if revenue else Decimal("0")
    roi = (profit / total_cost).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if total_cost else Decimal("0")
    return ProfitResult(revenue, total_cost, profit, margin, roi)


def score_product(
    snapshot: ProductSnapshot,
    *,
    demand: Optional[Decimal],
    trend: Optional[Decimal],
    profit: Optional[Decimal],
    competition: Optional[Decimal],
    risk: Optional[Decimal],
) -> ScoreResult:
    values = {
        "demand": demand,
        "trend": trend,
        "profit": profit,
        "competition": competition,
        "risk": risk,
    }
    known = tuple(name for name, value in values.items() if value is not None)
    missing = tuple(name for name, value in values.items() if value is None)
    if not known:
        return ScoreResult(Decimal("0"), Decimal("0"), known, missing)
    weight_sum = sum((WEIGHTS[name] for name in known), Decimal("0"))
    raw = sum((Decimal(values[name]) * WEIGHTS[name] for name in known), Decimal("0"))
    score = (raw / weight_sum).quantize(SCORE_STEP, rounding=ROUND_HALF_UP)
    confidence = (weight_sum / sum(WEIGHTS.values())).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return ScoreResult(score, confidence, known, missing)
