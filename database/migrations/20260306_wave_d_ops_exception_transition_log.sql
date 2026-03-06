BEGIN;

CREATE TABLE IF NOT EXISTS ops_exception_transition_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exception_id INTEGER NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    operator TEXT,
    reason TEXT,
    detail_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ops_exception_transition_exception_created
ON ops_exception_transition_log(exception_id, created_at DESC);

COMMIT;
