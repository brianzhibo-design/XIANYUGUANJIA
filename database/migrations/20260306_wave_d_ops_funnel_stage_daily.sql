BEGIN;

CREATE TABLE IF NOT EXISTS ops_funnel_stage_daily (
    stat_date TEXT NOT NULL,
    stage TEXT NOT NULL,
    xianyu_product_id TEXT NOT NULL DEFAULT '',
    xianyu_listing_id TEXT NOT NULL DEFAULT '',
    metric_count INTEGER NOT NULL DEFAULT 0 CHECK(metric_count >= 0),
    updated_at TEXT NOT NULL,
    PRIMARY KEY (stat_date, stage, xianyu_product_id, xianyu_listing_id)
);

CREATE INDEX IF NOT EXISTS idx_ops_funnel_stage_date
ON ops_funnel_stage_daily(stage, stat_date DESC);

COMMIT;
