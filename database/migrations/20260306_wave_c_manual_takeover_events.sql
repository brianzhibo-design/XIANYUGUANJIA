-- Wave C: manual takeover 事件审计表（升级路径）

BEGIN;

CREATE TABLE IF NOT EXISTS virtual_goods_manual_takeover_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    xianyu_order_id TEXT NOT NULL,
    enabled INTEGER NOT NULL CHECK(enabled IN (0, 1)),
    reason TEXT,
    operator TEXT,
    detail_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_vg_manual_takeover_events_order_created
ON virtual_goods_manual_takeover_events(xianyu_order_id, created_at DESC);

COMMIT;
