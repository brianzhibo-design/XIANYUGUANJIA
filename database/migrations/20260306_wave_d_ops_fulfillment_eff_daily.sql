BEGIN;

CREATE TABLE IF NOT EXISTS ops_fulfillment_eff_daily (
    stat_date TEXT NOT NULL,
    xianyu_product_id TEXT NOT NULL DEFAULT '',
    xianyu_listing_id TEXT NOT NULL DEFAULT '',
    total_orders INTEGER NOT NULL DEFAULT 0 CHECK(total_orders >= 0),
    fulfilled_orders INTEGER NOT NULL DEFAULT 0 CHECK(fulfilled_orders >= 0),
    failed_orders INTEGER NOT NULL DEFAULT 0 CHECK(failed_orders >= 0),
    avg_fulfillment_seconds INTEGER NOT NULL DEFAULT 0 CHECK(avg_fulfillment_seconds >= 0),
    p95_fulfillment_seconds INTEGER NOT NULL DEFAULT 0 CHECK(p95_fulfillment_seconds >= 0),
    updated_at TEXT NOT NULL,
    PRIMARY KEY (stat_date, xianyu_product_id, xianyu_listing_id)
);

CREATE INDEX IF NOT EXISTS idx_ops_fulfillment_eff_date
ON ops_fulfillment_eff_daily(stat_date DESC);

COMMIT;
