-- Enhanced schema for historical tracking

CREATE TABLE IF NOT EXISTS node_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_hash TEXT NOT NULL,
    test_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    protocol TEXT,
    ip TEXT,
    port INTEGER,
    country_code TEXT,
    city TEXT,
    organization TEXT,

    -- Performance metrics
    ping_ms INTEGER,
    packet_loss_percent REAL,
    jitter_ms REAL,
    download_mbps REAL,
    upload_mbps REAL,

    -- Security
    is_blocked BOOLEAN,
    reputation_score TEXT,
    cert_valid BOOLEAN,

    -- Availability
    test_success BOOLEAN,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_config_hash ON node_tests(config_hash);
CREATE INDEX IF NOT EXISTS idx_timestamp ON node_tests(test_timestamp);
CREATE INDEX IF NOT EXISTS idx_country ON node_tests(country_code);

-- Reliability scores (aggregated)
CREATE TABLE IF NOT EXISTS node_reliability (
    config_hash TEXT PRIMARY KEY,
    total_tests INTEGER DEFAULT 0,
    successful_tests INTEGER DEFAULT 0,
    avg_ping_ms REAL,
    avg_packet_loss REAL,
    uptime_percent REAL,
    last_seen DATETIME,
    first_seen DATETIME,
    reliability_score REAL
);