-- Wave-B / B1: 虚拟货源数据层三表落地
-- 目标表：virtual_goods_products / virtual_goods_orders / virtual_goods_callbacks
-- 约束规则：
--   1) external_event_id 可空唯一（NULL 可重复）
--   2) 当 external_event_id 缺失时，dedupe_key 唯一（partial unique index）
--   3) status 字段使用 virtual_goods 目标状态词并通过 CHECK 约束

BEGIN;

CREATE TABLE IF NOT EXISTS virtual_goods_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    xianyu_product_id TEXT NOT NULL UNIQUE,
    supply_goods_no TEXT,
    supply_type TEXT,
    delivery_mode TEXT,
    price_policy_json TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS virtual_goods_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    xianyu_order_id TEXT NOT NULL UNIQUE,
    xianyu_product_id TEXT,
    supply_order_no TEXT UNIQUE,
    session_id TEXT,
    order_status TEXT NOT NULL,
    fulfillment_status TEXT NOT NULL DEFAULT 'pending',
    callback_status TEXT NOT NULL DEFAULT 'none',
    manual_takeover INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK(order_status IN ('pending_payment','paid_waiting_delivery','delivered','delivery_failed','refund_pending','refunded','closed')),
    CHECK(fulfillment_status IN ('pending','delivering','fulfilled','failed','manual')),
    CHECK(callback_status IN ('none','received','processed','failed'))
);

CREATE TABLE IF NOT EXISTS virtual_goods_callbacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    callback_type TEXT NOT NULL,
    external_event_id TEXT UNIQUE,
    dedupe_key TEXT,
    xianyu_order_id TEXT,
    payload_json TEXT NOT NULL,
    raw_body TEXT NOT NULL,
    headers_json TEXT,
    signature TEXT,
    verify_passed INTEGER NOT NULL DEFAULT 0,
    verify_error TEXT,
    processed INTEGER NOT NULL DEFAULT 0,
    processed_at TEXT,
    created_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_vg_callbacks_dedupe_no_event
ON virtual_goods_callbacks(dedupe_key)
WHERE external_event_id IS NULL AND dedupe_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_vg_products_enabled_updated
ON virtual_goods_products(enabled, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_vg_orders_status_updated
ON virtual_goods_orders(order_status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_vg_orders_callback_status_updated
ON virtual_goods_orders(callback_status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_vg_callbacks_order_created
ON virtual_goods_callbacks(xianyu_order_id, created_at DESC);

COMMIT;
