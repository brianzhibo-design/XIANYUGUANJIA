-- Wave C: virtual goods 订单事件与异常指标表（升级路径）

BEGIN;

CREATE TABLE IF NOT EXISTS virtual_goods_order_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    xianyu_order_id TEXT,
    event_type TEXT NOT NULL,
    event_kind TEXT NOT NULL,
    callback_id INTEGER,
    from_status TEXT,
    to_status TEXT,
    result TEXT,
    error_code TEXT,
    is_exception INTEGER NOT NULL DEFAULT 0 CHECK(is_exception IN (0, 1)),
    detail_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_vg_order_events_order_created
ON virtual_goods_order_events(xianyu_order_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_vg_order_events_exception_created
ON virtual_goods_order_events(is_exception, created_at DESC);

COMMIT;
