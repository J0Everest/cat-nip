/*
=============================================================================
  CatAccum Recommended Schema
  These are the tables and columns the Cat Scenario Explorer app needs.
  Use the cataccum_discovery.sql script to map your real table names
  to the aliases below, then update db_map.json accordingly.
=============================================================================
*/
USE CatAccum;
GO

-- ── TABLE 1: exposures ────────────────────────────────────────────────────────
-- Drives: Exposure Map (bubbles + hover), Impacted Contracts KPI
-- One row per cedent-peril-location combination
IF OBJECT_ID('dbo.exposures','U') IS NOT NULL DROP TABLE dbo.exposures;
GO
CREATE TABLE dbo.exposures (
    exposure_id      INT IDENTITY(1,1) PRIMARY KEY,
    cedent_name      VARCHAR(200)   NOT NULL,   -- hover: cedent label on map
    peril_code       VARCHAR(50)    NOT NULL,   -- e.g. "Hurricane", "Earthquake"
    state_code       VARCHAR(10)    NOT NULL,   -- 2-char US state or country ISO
    region           VARCHAR(100)   NULL,        -- broader region label
    latitude         DECIMAL(9,6)   NOT NULL,   -- map bubble position
    longitude        DECIMAL(9,6)   NOT NULL,   -- map bubble position
    tiv_m            DECIMAL(18,2)  NULL,        -- total insured value ($M)
    gross_loss_m     DECIMAL(18,2)  NULL,        -- gross expected loss ($M)  → bubble size
    net_loss_m       DECIMAL(18,2)  NULL,        -- net expected loss ($M)
    ceded_loss_m     DECIMAL(18,2)  NULL,        -- ceded recovery ($M)
    contract_count   INT            NULL,        -- # contracts at this location
    as_of_date       DATE           NOT NULL    -- snapshot date for filtering
);
GO

-- ── TABLE 2: loss_scenarios ───────────────────────────────────────────────────
-- Drives: KPI summary cards (Gross/Net/Ceded ranges, Impacted Contracts)
--         Copilot Ask aggregations (peril + region filter)
-- One row per scenario (peril × region × return period)
IF OBJECT_ID('dbo.loss_scenarios','U') IS NOT NULL DROP TABLE dbo.loss_scenarios;
GO
CREATE TABLE dbo.loss_scenarios (
    scenario_id        INT IDENTITY(1,1) PRIMARY KEY,
    peril_code         VARCHAR(50)   NOT NULL,   -- "Hurricane", "Earthquake", …
    region             VARCHAR(100)  NOT NULL,   -- "Florida", "Gulf Coast", …
    return_period_yrs  INT           NULL,        -- 100, 250, 500 …
    percentile         VARCHAR(10)   NULL,        -- "P10", "P50", "P90"
    gross_loss_m       DECIMAL(18,2) NULL,        -- gross loss estimate ($M)
    net_loss_m         DECIMAL(18,2) NULL,        -- net loss after reinsurance ($M)
    ceded_recovery_m   DECIMAL(18,2) NULL,        -- ceded recovery ($M)
    impacted_contracts INT           NULL,        -- # contracts affected
    as_of_date         DATE          NOT NULL
);
GO

-- ── TABLE 3: ep_curve ─────────────────────────────────────────────────────────
-- Drives: Loss Distribution bar chart (P10 / P50 / P90)
-- Exceedance probability curve points per peril
IF OBJECT_ID('dbo.ep_curve','U') IS NOT NULL DROP TABLE dbo.ep_curve;
GO
CREATE TABLE dbo.ep_curve (
    ep_id              INT IDENTITY(1,1) PRIMARY KEY,
    peril_code         VARCHAR(50)   NOT NULL,
    region             VARCHAR(100)  NULL,
    return_period_yrs  INT           NOT NULL,   -- 10, 50, 100, 250, 500 …
    exceedance_prob    DECIMAL(6,4)  NULL,        -- 0.10, 0.02, 0.004 …
    gross_loss_m       DECIMAL(18,2) NULL,
    net_loss_m         DECIMAL(18,2) NULL,
    as_of_date         DATE          NOT NULL
);
GO

-- ── SAMPLE DATA ───────────────────────────────────────────────────────────────
INSERT INTO dbo.exposures
    (cedent_name, peril_code, state_code, region, latitude, longitude,
     tiv_m, gross_loss_m, net_loss_m, ceded_loss_m, contract_count, as_of_date)
VALUES
    ('Cedent A',  'Hurricane',  'FL', 'Southeast',   25.77, -80.19,  4200, 210, 95,  115, 28, '2026-07-01'),
    ('Cedent B',  'Hurricane',  'FL', 'Southeast',   30.33, -81.65,  3100, 155, 70,   85, 19, '2026-07-01'),
    ('Cedent C',  'Hurricane',  'LA', 'Gulf Coast',  29.95, -90.07,  2600, 130, 58,   72, 15, '2026-07-01'),
    ('Cedent D',  'Hurricane',  'TX', 'Gulf Coast',  29.76, -95.36,  1900,  95, 42,   53, 12, '2026-07-01'),
    ('Cedent E',  'Earthquake', 'CA', 'West Coast',  34.05,-118.24,  3700, 185, 84,  101, 22, '2026-07-01'),
    ('Cedent F',  'Earthquake', 'CA', 'West Coast',  37.77,-122.41,  2800, 140, 63,   77, 17, '2026-07-01'),
    ('Cedent G',  'Earthquake', 'OR', 'West Coast',  45.52,-122.68,  1200,  60, 27,   33,  8, '2026-07-01'),
    ('Cedent H',  'Wildfire',   'CA', 'West Coast',  38.58,-121.49,  1800,  90, 41,   49, 11, '2026-07-01'),
    ('Cedent I',  'Wildfire',   'CO', 'Mountain',    39.73,-104.98,   900,  45, 20,   25,  6, '2026-07-01'),
    ('Cedent J',  'Hail',       'TX', 'South-Central',32.77,-96.79, 1400,  70, 32,   38,  9, '2026-07-01'),
    ('Cedent K',  'Hail',       'OK', 'South-Central',35.47,-97.51, 1100,  55, 25,   30,  7, '2026-07-01'),
    ('Cedent L',  'Hail',       'KS', 'Midwest',     39.05, -95.68,  800,  40, 18,   22,  5, '2026-07-01');
GO

INSERT INTO dbo.loss_scenarios
    (peril_code, region, return_period_yrs, percentile,
     gross_loss_m, net_loss_m, ceded_recovery_m, impacted_contracts, as_of_date)
VALUES
    ('Hurricane',  'Southeast',    100, 'P50',  420, 180, 190, 68,  '2026-07-01'),
    ('Hurricane',  'Southeast',    250, 'P90',  680, 290, 310, 143, '2026-07-01'),
    ('Hurricane',  'Gulf Coast',   100, 'P50',  310, 135, 145, 47,  '2026-07-01'),
    ('Earthquake', 'West Coast',   100, 'P50',  380, 165, 175, 62,  '2026-07-01'),
    ('Earthquake', 'West Coast',   250, 'P90',  600, 265, 285, 105, '2026-07-01'),
    ('Wildfire',   'West Coast',   100, 'P50',  195,  85,  90, 38,  '2026-07-01'),
    ('Hail',       'South-Central',100, 'P50',  160,  70,  75, 30,  '2026-07-01');
GO

INSERT INTO dbo.ep_curve
    (peril_code, region, return_period_yrs, exceedance_prob,
     gross_loss_m, net_loss_m, as_of_date)
VALUES
    ('All Perils', NULL, 10,  0.1000, 180, 82,  '2026-07-01'),
    ('All Perils', NULL, 50,  0.0200, 320, 140, '2026-07-01'),
    ('All Perils', NULL, 100, 0.0100, 480, 210, '2026-07-01'),
    ('All Perils', NULL, 250, 0.0040, 680, 290, '2026-07-01'),
    ('All Perils', NULL, 500, 0.0020, 900, 385, '2026-07-01');
GO
