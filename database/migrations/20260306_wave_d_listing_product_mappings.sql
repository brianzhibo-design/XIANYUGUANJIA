BEGIN;

DROP INDEX IF EXISTS idx_lpm_listing_active_updated;
DROP INDEX IF EXISTS idx_lpm_product_active_updated;
DROP INDEX IF EXISTS idx_lpm_internal_listing_id;
DROP INDEX IF EXISTS idx_lpm_mapping_status_updated;
DROP INDEX IF EXISTS idx_lpm_supply_goods_no_updated;

CREATE TABLE IF NOT EXISTS listing_product_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    xianyu_product_id TEXT NOT NULL UNIQUE,
    xianyu_listing_id TEXT,
    internal_listing_id TEXT,
    supply_goods_no TEXT,
    mapping_status TEXT,
    is_active INTEGER,
    last_sync_at TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS listing_product_mappings_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    xianyu_product_id TEXT NOT NULL UNIQUE,
    internal_listing_id TEXT,
    supply_goods_no TEXT,
    mapping_status TEXT NOT NULL,
    last_sync_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK(mapping_status IN ('unmapped','mapped','syncing','failed','disabled'))
);

INSERT INTO listing_product_mappings_new(
    xianyu_product_id,
    internal_listing_id,
    supply_goods_no,
    mapping_status,
    last_sync_at,
    created_at,
    updated_at
)
SELECT
    xianyu_product_id,
    CASE
        WHEN COALESCE(TRIM(xianyu_listing_id), '') != '' THEN TRIM(xianyu_listing_id)
        ELSE NULL
    END AS internal_listing_id,
    NULLIF(TRIM(COALESCE(supply_goods_no, '')), '') AS supply_goods_no,
    CASE
        WHEN is_active = 0 THEN 'disabled'
        WHEN COALESCE(TRIM(xianyu_listing_id), '') != '' THEN 'mapped'
        ELSE 'unmapped'
    END AS mapping_status,
    COALESCE(updated_at, created_at) AS last_sync_at,
    COALESCE(created_at, updated_at, CURRENT_TIMESTAMP) AS created_at,
    COALESCE(updated_at, created_at, CURRENT_TIMESTAMP) AS updated_at
FROM listing_product_mappings;

DROP TABLE IF EXISTS listing_product_mappings;
ALTER TABLE listing_product_mappings_new RENAME TO listing_product_mappings;

CREATE UNIQUE INDEX idx_lpm_internal_listing_id
ON listing_product_mappings(internal_listing_id)
WHERE internal_listing_id IS NOT NULL;

CREATE INDEX idx_lpm_mapping_status_updated
ON listing_product_mappings(mapping_status, updated_at DESC);

CREATE INDEX idx_lpm_supply_goods_no_updated
ON listing_product_mappings(supply_goods_no, updated_at DESC);

COMMIT;
