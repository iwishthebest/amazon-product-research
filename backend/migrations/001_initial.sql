CREATE TABLE IF NOT EXISTS marketplaces (
    code VARCHAR(2) PRIMARY KEY,
    amazon_marketplace_id VARCHAR(32) NOT NULL UNIQUE,
    frontend_domain TEXT NOT NULL,
    seller_central_domain TEXT NOT NULL,
    sp_api_endpoint TEXT NOT NULL,
    sp_api_region VARCHAR(8) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    locale VARCHAR(16) NOT NULL,
    timezone TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS products (
    id BIGSERIAL PRIMARY KEY,
    marketplace_code VARCHAR(2) NOT NULL REFERENCES marketplaces(code),
    asin VARCHAR(10) NOT NULL,
    parent_asin VARCHAR(10),
    title TEXT,
    brand TEXT,
    category_id TEXT,
    category_path TEXT,
    image_url TEXT,
    variation_attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    UNIQUE (marketplace_code, asin)
);

CREATE TABLE IF NOT EXISTS product_snapshots (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    price NUMERIC(14, 2),
    shipping_cost NUMERIC(14, 2),
    currency VARCHAR(3),
    rating NUMERIC(3, 2),
    review_count INTEGER,
    sales_rank INTEGER,
    estimated_monthly_sales INTEGER,
    sales_metric_type VARCHAR(16) NOT NULL CHECK (sales_metric_type IN ('actual', 'estimated', 'proxy', 'unavailable')),
    offer_count INTEGER,
    fba_fee_estimate NUMERIC(14, 2),
    source TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    raw_payload_hash CHAR(64)
);

CREATE TABLE IF NOT EXISTS product_history (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL,
    metric_value NUMERIC(18, 6) NOT NULL,
    unit TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL,
    confidence NUMERIC(5, 4)
);

CREATE TABLE IF NOT EXISTS cost_profiles (
    id BIGSERIAL PRIMARY KEY,
    marketplace_code VARCHAR(2) NOT NULL REFERENCES marketplaces(code),
    product_id BIGINT REFERENCES products(id) ON DELETE CASCADE,
    category_id TEXT,
    purchase_cost NUMERIC(14, 2) NOT NULL DEFAULT 0,
    inbound_shipping NUMERIC(14, 2) NOT NULL DEFAULT 0,
    packaging_cost NUMERIC(14, 2) NOT NULL DEFAULT 0,
    platform_fee NUMERIC(14, 2) NOT NULL DEFAULT 0,
    fba_fee NUMERIC(14, 2) NOT NULL DEFAULT 0,
    ad_cost NUMERIC(14, 2) NOT NULL DEFAULT 0,
    return_reserve NUMERIC(14, 2) NOT NULL DEFAULT 0,
    tax_cost NUMERIC(14, 2) NOT NULL DEFAULT 0,
    effective_from TIMESTAMPTZ NOT NULL,
    CHECK (product_id IS NOT NULL OR category_id IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS research_tasks (
    id UUID PRIMARY KEY,
    marketplace_code VARCHAR(2) NOT NULL REFERENCES marketplaces(code),
    category_id TEXT,
    keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    asin_list JSONB NOT NULL DEFAULT '[]'::jsonb,
    filters_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(24) NOT NULL,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error_summary TEXT
);

CREATE TABLE IF NOT EXISTS source_sync_jobs (
    id UUID PRIMARY KEY,
    source TEXT NOT NULL,
    marketplace_code VARCHAR(2) NOT NULL REFERENCES marketplaces(code),
    request_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    rate_limit_count INTEGER NOT NULL DEFAULT 0,
    missing_field_count INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    status VARCHAR(24) NOT NULL
);

INSERT INTO marketplaces (code, amazon_marketplace_id, frontend_domain, seller_central_domain, sp_api_endpoint, sp_api_region, currency, locale, timezone)
VALUES
    ('US', 'ATVPDKIKX0DER', 'amazon.com', 'sellercentral.amazon.com', 'sellingpartnerapi-na.amazon.com', 'na', 'USD', 'en-US', 'America/Los_Angeles'),
    ('AU', 'A39IBJ37TRP1C6', 'amazon.com.au', 'sellercentral.amazon.com.au', 'sellingpartnerapi-fe.amazon.com', 'fe', 'AUD', 'en-AU', 'Australia/Sydney')
ON CONFLICT (code) DO NOTHING;
