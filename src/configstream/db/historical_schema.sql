-- Enhanced schema for comprehensive historical tracking

-- Store individual test results
CREATE TABLE IF NOT EXISTS node_test_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_hash TEXT NOT NULL,
    test_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Node identification
    protocol TEXT,
    ip TEXT,
    port INTEGER,
    country_code TEXT,
    city TEXT,
    organization TEXT,

    -- Basic performance
    ping_ms INTEGER,
    test_success BOOLEAN,

    -- Advanced network quality
    packet_loss_percent REAL DEFAULT 0.0,
    jitter_ms REAL DEFAULT 0.0,
    quality_score REAL DEFAULT 0.0,
    network_stable BOOLEAN DEFAULT 0,

    -- Bandwidth (optional)
    download_mbps REAL DEFAULT 0.0,
    upload_mbps REAL DEFAULT 0.0,

    -- Security
    is_blocked BOOLEAN DEFAULT 0,
    reputation_score TEXT,
    cert_valid BOOLEAN DEFAULT 1,
    cert_days_until_expiry INTEGER DEFAULT 0,
    is_tor BOOLEAN DEFAULT 0,
    is_proxy BOOLEAN DEFAULT 0,

    -- Error tracking
    error_message TEXT
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_config_hash
    ON node_test_history(config_hash);
CREATE INDEX IF NOT EXISTS idx_timestamp
    ON node_test_history(test_timestamp);
CREATE INDEX IF NOT EXISTS idx_country
    ON node_test_history(country_code);
CREATE INDEX IF NOT EXISTS idx_protocol
    ON node_test_history(protocol);
CREATE INDEX IF NOT EXISTS idx_success
    ON node_test_history(test_success);

-- Aggregated reliability metrics
CREATE TABLE IF NOT EXISTS node_reliability (
    config_hash TEXT PRIMARY KEY,

    -- Test statistics
    total_tests INTEGER DEFAULT 0,
    successful_tests INTEGER DEFAULT 0,
    failed_tests INTEGER DEFAULT 0,

    -- Performance metrics (averages)
    avg_ping_ms REAL DEFAULT 0.0,
    min_ping_ms REAL DEFAULT 0.0,
    max_ping_ms REAL DEFAULT 0.0,
    avg_packet_loss REAL DEFAULT 0.0,
    avg_jitter REAL DEFAULT 0.0,
    avg_quality_score REAL DEFAULT 0.0,

    -- Bandwidth metrics
    avg_download_mbps REAL DEFAULT 0.0,
    avg_upload_mbps REAL DEFAULT 0.0,

    -- Reliability scores
    uptime_percent REAL DEFAULT 0.0,
    reliability_score REAL DEFAULT 0.0,
    stability_score REAL DEFAULT 0.0,

    -- Timestamps
    first_seen DATETIME,
    last_seen DATETIME,
    last_successful_test DATETIME,

    -- Node info (from most recent test)
    protocol TEXT,
    ip TEXT,
    port INTEGER,
    country_code TEXT,
    city TEXT
);

-- Performance summary by time period
CREATE TABLE IF NOT EXISTS performance_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    summary_date DATE NOT NULL,
    period_type TEXT NOT NULL,  -- 'hourly', 'daily', 'weekly'

    -- Aggregate statistics
    total_nodes_tested INTEGER DEFAULT 0,
    successful_nodes INTEGER DEFAULT 0,
    avg_ping_ms REAL DEFAULT 0.0,
    avg_quality_score REAL DEFAULT 0.0,

    -- Protocol distribution
    protocol_distribution TEXT,  -- JSON
    country_distribution TEXT,   -- JSON

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(summary_date, period_type)
);