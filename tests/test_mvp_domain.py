from decimal import Decimal

import pytest

from backend.app.config import DEFAULT_MARKETPLACES, MarketplaceConfig, get_marketplace
from backend.app.domain import ProductSnapshot, SalesMetricType
from backend.app.services import calculate_profit, score_product


def test_default_marketplaces_keep_us_and_au_isolated():
    us = get_marketplace("US")
    au = get_marketplace("AU")

    assert us.code == "US"
    assert us.amazon_marketplace_id == "ATVPDKIKX0DER"
    assert us.currency == "USD"
    assert us.frontend_domain == "amazon.com"
    assert us.sp_api_region == "na"
    assert au.code == "AU"
    assert au.amazon_marketplace_id == "A39IBJ37TRP1C6"
    assert au.currency == "AUD"
    assert au.frontend_domain == "amazon.com.au"
    assert au.sp_api_region == "fe"
    assert us != au


def test_marketplace_config_rejects_cross_site_currency():
    with pytest.raises(ValueError, match="currency"):
        MarketplaceConfig(
            code="US",
            amazon_marketplace_id="ATVPDKIKX0DER",
            frontend_domain="amazon.com",
            seller_central_domain="sellercentral.amazon.com",
            sp_api_endpoint="sellingpartnerapi-na.amazon.com",
            sp_api_region="na",
            currency="AUD",
            locale="en-US",
            timezone="America/Los_Angeles",
        )


def test_profit_calculation_is_explicit_and_uses_user_cost_scenario():
    result = calculate_profit(
        price=Decimal("100"),
        purchase_cost=Decimal("30"),
        inbound_shipping=Decimal("5"),
        platform_fee=Decimal("15"),
        fba_fee=Decimal("10"),
        packaging_cost=Decimal("2"),
        ad_cost=Decimal("8"),
        return_reserve=Decimal("3"),
        tax_cost=Decimal("4"),
    )

    assert result.profit == Decimal("23")
    assert result.profit_margin == Decimal("0.23")
    assert result.is_scenario is True


def test_score_renormalizes_known_components_and_drops_confidence_when_missing():
    snapshot = ProductSnapshot(
        marketplace_code="US",
        asin="B000000001",
        price=Decimal("50"),
        rating=Decimal("4.5"),
        review_count=100,
        sales_rank=1000,
        estimated_monthly_sales=None,
        sales_metric_type=SalesMetricType.UNAVAILABLE,
        source="csv",
    )

    result = score_product(snapshot, demand=Decimal("0.8"), trend=None, profit=Decimal("0.7"), competition=Decimal("0.6"), risk=Decimal("0.9"))

    assert result.score == Decimal("0.73")
    assert result.known_components == ("demand", "profit", "competition", "risk")
    assert result.confidence < Decimal("1")
    assert "trend" in result.missing_components


def test_product_snapshot_requires_a_sales_metric_type():
    with pytest.raises(ValueError):
        ProductSnapshot(
            marketplace_code="AU",
            asin="B000000002",
            price=Decimal("10"),
            source="csv",
        )
