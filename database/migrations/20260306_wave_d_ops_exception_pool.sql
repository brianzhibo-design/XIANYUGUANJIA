BEGIN;

CREATE TABLE IF NOT EXISTS ops_exception_pool (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    xianyu_order_id TEXT,
    event_kind TEXT NOT NULL,
    exception_code TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'P2' CHECK(severity IN ('P0','P1','P2','P3')),
    status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','investigating','resolved','ignored')),
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    occurrence_count INTEGER NOT NULL DEFAULT 1 CHECK(occurrence_count >= 1),
    detail_json TEXT,
    resolved_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ops_exception_pool_priority
ON ops_exception_pool(status, severity, last_seen_at DESC);

CREATE INDEX IF NOT EXISTS idx_ops_exception_pool_order
ON ops_exception_pool(xianyu_order_id, last_seen_at DESC);

COMMIT;
