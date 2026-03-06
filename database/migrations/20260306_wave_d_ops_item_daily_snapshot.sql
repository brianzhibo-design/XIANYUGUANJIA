BEGIN;

CREATE TABLE IF NOT EXISTS ops_item_daily_snapshot (
    stat_date TEXT NOT NULL,
    xianyu_product_id TEXT NOT NULL DEFAULT '',
    xianyu_listing_id TEXT NOT NULL DEFAULT '',
    exposure_count INTEGER NOT NULL DEFAULT 0 CHECK(exposure_count >= 0),
    paid_order_count INTEGER NOT NULL DEFAULT 0 CHECK(paid_order_count >= 0),
    paid_amount_cents INTEGER NOT NULL DEFAULT 0 CHECK(paid_amount_cents >= 0),
    refund_order_count INTEGER NOT NULL DEFAULT 0 CHECK(refund_order_count >= 0),
    exception_count INTEGER NOT NULL DEFAULT 0 CHECK(exception_count >= 0),
    manual_takeover_count INTEGER NOT NULL DEFAULT 0 CHECK(manual_takeover_count >= 0),
    updated_at TEXT NOT NULL,
    PRIMARY KEY (stat_date, xianyu_product_id, xianyu_listing_id)
);

CREATE INDEX IF NOT EXISTS idx_ops_item_snapshot_date
ON ops_item_daily_snapshot(stat_date DESC);

COMMIT;
