-- Wave-B / B4: callback 维度字段 + lease 抢占字段
-- 仅扩展 virtual_goods_callbacks，不改动业务数据

BEGIN;

ALTER TABLE virtual_goods_callbacks
    ADD COLUMN source_family TEXT NOT NULL DEFAULT 'unknown'
    CHECK(source_family IN ('open_platform','virtual_supply','unknown'));

ALTER TABLE virtual_goods_callbacks
    ADD COLUMN event_kind TEXT NOT NULL DEFAULT 'unknown'
    CHECK(event_kind IN ('order','refund','voucher','coupon','code','unknown'));

ALTER TABLE virtual_goods_callbacks
    ADD COLUMN claimed_by TEXT;

ALTER TABLE virtual_goods_callbacks
    ADD COLUMN claimed_at TEXT;

ALTER TABLE virtual_goods_callbacks
    ADD COLUMN claim_expires_at TEXT;

ALTER TABLE virtual_goods_callbacks
    ADD COLUMN last_process_error TEXT;

ALTER TABLE virtual_goods_callbacks
    ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0
    CHECK(attempt_count >= 0);

CREATE INDEX IF NOT EXISTS idx_vg_callbacks_claim_expires_at
ON virtual_goods_callbacks(claim_expires_at);

COMMIT;
