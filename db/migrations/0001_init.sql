-- dialect:postgresql
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    hash TEXT NOT NULL UNIQUE,
    data JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_hash ON reports (hash);
CREATE INDEX IF NOT EXISTS idx_reports_source_ingested_at ON reports (source, ingested_at DESC);

-- dialect:sqlite
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    ingested_at TEXT NOT NULL DEFAULT (datetime('now')),
    hash TEXT NOT NULL UNIQUE,
    data TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_hash ON reports (hash);
CREATE INDEX IF NOT EXISTS idx_reports_source_ingested_at ON reports (source, ingested_at DESC);
