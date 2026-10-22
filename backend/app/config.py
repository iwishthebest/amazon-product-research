from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class MarketplaceConfig:
    code: str
    amazon_marketplace_id: str
    frontend_domain: str
    seller_central_domain: str
    sp_api_endpoint: str
    sp_api_region: str
    currency: str
    locale: str
    timezone: str
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.code != self.code.upper() or len(self.code) != 2:
            raise ValueError("marketplace code must be a two-letter uppercase code")
        if self.currency not in {"USD", "AUD"}:
            raise ValueError("currency must be USD or AUD")
        expected_currency = {"US": "USD", "AU": "AUD"}.get(self.code)
        if expected_currency and self.currency != expected_currency:
            raise ValueError(f"currency for {self.code} must be {expected_currency}")
        if not self.amazon_marketplace_id.strip():
            raise ValueError("amazon_marketplace_id is required")
        if not self.frontend_domain.strip() or not self.seller_central_domain.strip():
            raise ValueError("Amazon domains are required")


DEFAULT_MARKETPLACES: Final[dict[str, MarketplaceConfig]] = {
    "US": MarketplaceConfig(
        code="US",
        amazon_marketplace_id="ATVPDKIKX0DER",
        frontend_domain="amazon.com",
        seller_central_domain="sellercentral.amazon.com",
        sp_api_endpoint="sellingpartnerapi-na.amazon.com",
        sp_api_region="na",
        currency="USD",
        locale="en-US",
        timezone="America/Los_Angeles",
    ),
    "AU": MarketplaceConfig(
        code="AU",
        amazon_marketplace_id="A39IBJ37TRP1C6",
        frontend_domain="amazon.com.au",
        seller_central_domain="sellercentral.amazon.com.au",
        sp_api_endpoint="sellingpartnerapi-fe.amazon.com",
        sp_api_region="fe",
        currency="AUD",
        locale="en-AU",
        timezone="Australia/Sydney",
    ),
}


def get_marketplace(code: str) -> MarketplaceConfig:
    normalized = str(code).strip().upper()
    try:
        return DEFAULT_MARKETPLACES[normalized]
    except KeyError as exc:
        raise ValueError(f"unsupported marketplace: {code}") from exc
