-- dialect:postgresql
CREATE TABLE IF NOT EXISTS submissions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL CHECK (source IN ('bp_timer', 'bpsr_logs', 'manual', 'other')),
    category TEXT NOT NULL CHECK (category IN ('combat', 'heal', 'boss_event', 'trade')),
    region TEXT NULL,
    boss_name TEXT NULL,
    payload JSONB NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_submissions_category_ingested_at
    ON submissions (category, ingested_at DESC);

CREATE TABLE IF NOT EXISTS api_keys (
    key TEXT PRIMARY KEY,
    label TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- dialect:sqlite
CREATE TABLE IF NOT EXISTS submissions (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    category TEXT NOT NULL,
    region TEXT NULL,
    boss_name TEXT NULL,
    payload TEXT NOT NULL,
    ingested_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_submissions_category_ingested_at
    ON submissions (category, ingested_at DESC);

CREATE TABLE IF NOT EXISTS api_keys (
    key TEXT PRIMARY KEY,
    label TEXT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
