-- =========================================================
-- Schema PostgreSQL - UrbanHub / Smart City
-- Tables :
--   - traffic_readings
--   - pollution_readings
--   - alerts
--   - correlations
-- =========================================================

BEGIN;

-- Optionnel : extension pour UUID si vous voulez l’utiliser plus tard
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========================================================
-- Table : traffic_readings
-- =========================================================
CREATE TABLE IF NOT EXISTS traffic_readings (
    id              BIGSERIAL PRIMARY KEY,
    timestamp       TIMESTAMPTZ NOT NULL,
    city            VARCHAR(100) NOT NULL,
    zone            VARCHAR(100),
    street          VARCHAR(255) NOT NULL,
    section_id      VARCHAR(100) NOT NULL,
    q               DOUBLE PRECISION NOT NULL,
    etat_trafic     VARCHAR(50),
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    upstream_name   VARCHAR(255),
    downstream_name VARCHAR(255),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index utiles
CREATE INDEX IF NOT EXISTS idx_traffic_readings_timestamp
    ON traffic_readings (timestamp);

CREATE INDEX IF NOT EXISTS idx_traffic_readings_city_zone_timestamp
    ON traffic_readings (city, zone, timestamp);

CREATE INDEX IF NOT EXISTS idx_traffic_readings_section_timestamp
    ON traffic_readings (section_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_traffic_readings_street
    ON traffic_readings (street);

-- =========================================================
-- Table : pollution_readings
-- =========================================================
CREATE TABLE IF NOT EXISTS pollution_readings (
    id          BIGSERIAL PRIMARY KEY,
    timestamp   TIMESTAMPTZ NOT NULL,
    city        VARCHAR(100) NOT NULL,
    zone        VARCHAR(100),
    pollutant   VARCHAR(50) NOT NULL,
    value       DOUBLE PRECISION NOT NULL,
    unit        VARCHAR(50),
    latitude    DOUBLE PRECISION,
    longitude   DOUBLE PRECISION,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index utiles
CREATE INDEX IF NOT EXISTS idx_pollution_readings_timestamp
    ON pollution_readings (timestamp);

CREATE INDEX IF NOT EXISTS idx_pollution_readings_city_zone_timestamp
    ON pollution_readings (city, zone, timestamp);

CREATE INDEX IF NOT EXISTS idx_pollution_readings_pollutant_timestamp
    ON pollution_readings (pollutant, timestamp);

CREATE INDEX IF NOT EXISTS idx_pollution_readings_city_pollutant
    ON pollution_readings (city, pollutant);

-- =========================================================
-- Table : alerts
-- =========================================================
CREATE TABLE IF NOT EXISTS alerts (
    id          BIGSERIAL PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    type        VARCHAR(50) NOT NULL,      -- traffic, pollution, correlation
    level       VARCHAR(20) NOT NULL,      -- WARNING, CRITICAL
    city        VARCHAR(100),
    zone        VARCHAR(100),
    title       VARCHAR(255) NOT NULL,
    message     TEXT NOT NULL,
    street      VARCHAR(255),
    pollutant   VARCHAR(50),
    value       DOUBLE PRECISION,
    status      VARCHAR(30) NOT NULL DEFAULT 'OPEN', -- OPEN, ACK, CLOSED
    source      VARCHAR(50),               -- pipeline, manual, rule_engine
    metadata    JSONB DEFAULT '{}'::jsonb
);

-- Index utiles
CREATE INDEX IF NOT EXISTS idx_alerts_created_at
    ON alerts (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_alerts_type_level
    ON alerts (type, level);

CREATE INDEX IF NOT EXISTS idx_alerts_city_zone
    ON alerts (city, zone);

CREATE INDEX IF NOT EXISTS idx_alerts_status
    ON alerts (status);

-- =========================================================
-- Table : correlations
-- =========================================================
CREATE TABLE IF NOT EXISTS correlations (
    id              BIGSERIAL PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    window_start    TIMESTAMPTZ NOT NULL,
    window_end      TIMESTAMPTZ NOT NULL,
    city            VARCHAR(100) NOT NULL,
    zone            VARCHAR(100),
    pollutant       VARCHAR(50) NOT NULL,
    metric          VARCHAR(50) NOT NULL DEFAULT 'pearson', -- pearson, spearman, etc.
    corr_value      DOUBLE PRECISION NOT NULL,
    p_value         DOUBLE PRECISION,
    sample_size     INTEGER NOT NULL DEFAULT 0,
    traffic_metric  VARCHAR(50) NOT NULL DEFAULT 'q',
    pollution_metric VARCHAR(50) NOT NULL DEFAULT 'value',
    details         JSONB DEFAULT '{}'::jsonb
);

-- Index utiles
CREATE INDEX IF NOT EXISTS idx_correlations_created_at
    ON correlations (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_correlations_city_zone_window
    ON correlations (city, zone, window_start, window_end);

CREATE INDEX IF NOT EXISTS idx_correlations_pollutant_metric
    ON correlations (pollutant, metric);

-- =========================================================
-- Contraintes optionnelles
-- =========================================================

ALTER TABLE alerts
    ADD CONSTRAINT chk_alerts_level
    CHECK (level IN ('WARNING', 'CRITICAL'));

ALTER TABLE alerts
    ADD CONSTRAINT chk_alerts_status
    CHECK (status IN ('OPEN', 'ACK', 'CLOSED'));

ALTER TABLE correlations
    ADD CONSTRAINT chk_correlations_metric
    CHECK (metric IN ('pearson', 'spearman', 'kendall'));

-- =========================================================
-- Vues pratiques (optionnelles)
-- =========================================================

CREATE OR REPLACE VIEW v_latest_traffic AS
SELECT DISTINCT ON (city, zone, section_id)
    *
FROM traffic_readings
ORDER BY city, zone, section_id, timestamp DESC;

CREATE OR REPLACE VIEW v_latest_pollution AS
SELECT DISTINCT ON (city, zone, pollutant)
    *
FROM pollution_readings
ORDER BY city, zone, pollutant, timestamp DESC;

COMMIT;