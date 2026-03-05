-- Xianyu-OpenClaw Database Schema
-- 闲鱼自动化工具数据库结构
-- SQLite 兼容

-- ============================================
-- 1. 合规审计数据库 (data/compliance.db)
-- ============================================
CREATE TABLE IF NOT EXISTS compliance_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    actor TEXT,
    account_id TEXT,
    session_id TEXT,
    action TEXT NOT NULL,
    content TEXT,
    decision TEXT NOT NULL,
    blocked INTEGER NOT NULL,
    hits_json TEXT,
    policy_scope TEXT,
    policy_version TEXT,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_compliance_audit_time 
ON compliance_audit(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_compliance_audit_session
ON compliance_audit(session_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_compliance_audit_account
ON compliance_audit(account_id, created_at DESC);

-- ============================================
-- 2. 工作流数据库 (data/workflow.db)
-- ============================================
CREATE TABLE IF NOT EXISTS workflow_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,
    stage TEXT NOT NULL DEFAULT 'NEW',
    payload_json TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    lease_until TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_workflow_jobs_session 
ON workflow_jobs(session_id);

CREATE INDEX IF NOT EXISTS idx_workflow_jobs_stage 
ON workflow_jobs(stage);

CREATE INDEX IF NOT EXISTS idx_workflow_jobs_lease 
ON workflow_jobs(lease_until);

-- 会话状态跟踪
CREATE TABLE IF NOT EXISTS session_states (
    session_id TEXT PRIMARY KEY,
    current_state TEXT NOT NULL DEFAULT 'NEW',
    context_json TEXT,
    quote_data_json TEXT,
    last_action TEXT,
    manual_takeover INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_session_states_takeover 
ON session_states(manual_takeover);

-- ============================================
-- 3. 订单数据库 (data/orders.db)
-- ============================================
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    session_id TEXT,
    quote_snapshot_json TEXT,
    item_type TEXT NOT NULL DEFAULT 'virtual',
    status TEXT NOT NULL,
    manual_takeover INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_session 
ON orders(session_id);

CREATE INDEX IF NOT EXISTS idx_orders_status 
ON orders(status);

CREATE INDEX IF NOT EXISTS idx_orders_created 
ON orders(created_at DESC);

-- 订单事件日志
CREATE TABLE IF NOT EXISTS order_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    status TEXT,
    detail_json TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_order_events_order_time
ON order_events(order_id, created_at DESC);

-- 订单回调去重（幂等性）
CREATE TABLE IF NOT EXISTS order_callback_dedup (
    external_event_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_callback_dedup_order 
ON order_callback_dedup(order_id);

-- ============================================
-- 4. 消息去重数据库 (data/dedup.db)
-- ============================================
CREATE TABLE IF NOT EXISTS message_dedup_exact (
    digest TEXT PRIMARY KEY,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS message_dedup_content (
    digest TEXT PRIMARY KEY,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dedup_exact_time 
ON message_dedup_exact(created_at);

CREATE INDEX IF NOT EXISTS idx_dedup_content_time 
ON message_dedup_content(created_at);

-- ============================================
-- 5. 数据分析数据库 (data/analytics.db)
-- ============================================
CREATE TABLE IF NOT EXISTS operations_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    item_id TEXT,
    account_id TEXT,
    detail_json TEXT,
    result TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_operations_action 
ON operations_log(action, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_operations_account 
ON operations_log(account_id, created_at DESC);

-- 报价记录
CREATE TABLE IF NOT EXISTS quote_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    origin TEXT,
    destination TEXT,
    weight REAL,
    courier TEXT,
    total_fee REAL,
    cache_hit INTEGER,
    fallback_used INTEGER,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_quote_session 
ON quote_logs(session_id);

CREATE INDEX IF NOT EXISTS idx_quote_created 
ON quote_logs(created_at DESC);

-- ============================================
-- 6. 跟进/回访数据库 (data/followup.db)
-- ============================================
CREATE TABLE IF NOT EXISTS followup_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    trigger_reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    scheduled_at INTEGER NOT NULL,
    executed_at INTEGER,
    result TEXT,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_followup_scheduled 
ON followup_tasks(scheduled_at);

CREATE INDEX IF NOT EXISTS idx_followup_status 
ON followup_tasks(status);

-- DND (勿扰) 列表
CREATE TABLE IF NOT EXISTS dnd_sessions (
    session_id TEXT PRIMARY KEY,
    reason TEXT,
    expires_at INTEGER,
    created_at INTEGER NOT NULL
);

-- ============================================
-- 7. 增长实验数据库 (data/growth.db)
-- ============================================
CREATE TABLE IF NOT EXISTS experiment_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    variant TEXT NOT NULL,
    assigned_at TEXT NOT NULL,
    UNIQUE(experiment_id, subject_id)
);

CREATE TABLE IF NOT EXISTS funnel_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id TEXT,
    subject_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    converted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_funnel_exp_subject 
ON funnel_events(experiment_id, subject_id);

-- ============================================
-- 8. 主应用数据库 (data/agent.db)
-- ============================================
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    name TEXT,
    cookie_encrypted TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    last_health_check TEXT,
    health_status TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_accounts_enabled 
ON accounts(enabled);

-- 商品信息缓存
CREATE TABLE IF NOT EXISTS listings (
    id TEXT PRIMARY KEY,
    account_id TEXT,
    title TEXT,
    price REAL,
    status TEXT,
    detail_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_listings_account 
ON listings(account_id);

CREATE INDEX IF NOT EXISTS idx_listings_status 
ON listings(status);
