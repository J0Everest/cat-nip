/*
=============================================================================
  CatAccum Schema Discovery Script
  Run this against your CatAccum database to identify which tables and
  columns already exist and how they map to what the app needs.
=============================================================================
*/
USE CatAccum;   -- change to your actual DB name if different
GO

-- ── 1. ALL TABLES IN THE DATABASE ────────────────────────────────────────────
SELECT
    t.TABLE_SCHEMA                        AS [Schema],
    t.TABLE_NAME                          AS [Table],
    COUNT(c.COLUMN_NAME)                  AS [Column Count],
    SUM(CASE WHEN p.rows IS NOT NULL
             THEN p.rows ELSE 0 END)      AS [Approx Row Count]
FROM INFORMATION_SCHEMA.TABLES  t
JOIN INFORMATION_SCHEMA.COLUMNS c ON c.TABLE_SCHEMA = t.TABLE_SCHEMA
                                  AND c.TABLE_NAME   = t.TABLE_NAME
LEFT JOIN sys.partitions p
       ON p.object_id = OBJECT_ID(t.TABLE_SCHEMA + '.' + t.TABLE_NAME)
      AND p.index_id IN (0,1)
WHERE t.TABLE_TYPE = 'BASE TABLE'
GROUP BY t.TABLE_SCHEMA, t.TABLE_NAME
ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME;
GO

-- ── 2. FULL COLUMN INVENTORY ─────────────────────────────────────────────────
SELECT
    TABLE_SCHEMA        AS [Schema],
    TABLE_NAME          AS [Table],
    ORDINAL_POSITION    AS [#],
    COLUMN_NAME         AS [Column],
    DATA_TYPE           AS [Type],
    CHARACTER_MAXIMUM_LENGTH AS [MaxLen],
    IS_NULLABLE         AS [Nullable]
FROM INFORMATION_SCHEMA.COLUMNS
ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION;
GO

-- ── 3. LOOK FOR PERIL-RELATED COLUMNS ────────────────────────────────────────
-- These feed the Copilot Ask and exposure map peril dimension
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE LOWER(COLUMN_NAME) LIKE '%peril%'
   OR LOWER(COLUMN_NAME) LIKE '%hazard%'
   OR LOWER(COLUMN_NAME) LIKE '%event_type%'
ORDER BY TABLE_NAME, COLUMN_NAME;
GO

-- ── 4. LOOK FOR GEOGRAPHY / LOCATION COLUMNS ─────────────────────────────────
-- These drive the exposure map (lat/lon, state, region)
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE LOWER(COLUMN_NAME) IN ('lat','lon','latitude','longitude',
                              'state','region','zone','country',
                              'territory','area','location')
   OR LOWER(COLUMN_NAME) LIKE '%_state'
   OR LOWER(COLUMN_NAME) LIKE '%_region'
   OR LOWER(COLUMN_NAME) LIKE '%_lat'
   OR LOWER(COLUMN_NAME) LIKE '%_lon'
ORDER BY TABLE_NAME, COLUMN_NAME;
GO

-- ── 5. LOOK FOR LOSS / IMPACT COLUMNS ────────────────────────────────────────
-- These populate KPIs (gross/net/ceded), loss distribution, and map bubble size
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE LOWER(COLUMN_NAME) LIKE '%loss%'
   OR LOWER(COLUMN_NAME) LIKE '%impact%'
   OR LOWER(COLUMN_NAME) LIKE '%gross%'
   OR LOWER(COLUMN_NAME) LIKE '%net%'
   OR LOWER(COLUMN_NAME) LIKE '%ceded%'
   OR LOWER(COLUMN_NAME) LIKE '%aal%'
   OR LOWER(COLUMN_NAME) LIKE '%tvar%'
   OR LOWER(COLUMN_NAME) LIKE '%pml%'
   OR LOWER(COLUMN_NAME) LIKE '%tiv%'
ORDER BY TABLE_NAME, COLUMN_NAME;
GO

-- ── 6. LOOK FOR RETURN PERIOD / PERCENTILE COLUMNS ───────────────────────────
-- These feed the P10/P50/P90 loss distribution chart
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE LOWER(COLUMN_NAME) LIKE '%return_period%'
   OR LOWER(COLUMN_NAME) LIKE '%percentile%'
   OR LOWER(COLUMN_NAME) LIKE '%exceedance%'
   OR LOWER(COLUMN_NAME) LIKE '%rp%'
   OR LOWER(COLUMN_NAME) IN ('p10','p50','p90','p100','p250')
ORDER BY TABLE_NAME, COLUMN_NAME;
GO

-- ── 7. LOOK FOR CONTRACT / CEDENT COLUMNS ────────────────────────────────────
-- These populate the contracts KPI and exposure map hover details
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE LOWER(COLUMN_NAME) LIKE '%cedent%'
   OR LOWER(COLUMN_NAME) LIKE '%contract%'
   OR LOWER(COLUMN_NAME) LIKE '%insured%'
   OR LOWER(COLUMN_NAME) LIKE '%policy%'
ORDER BY TABLE_NAME, COLUMN_NAME;
GO

-- ── 8. SAMPLE TOP 5 ROWS FROM EVERY TABLE ────────────────────────────────────
-- Run only on small tables to get a feel for data shapes.
-- Uncomment and replace <TableName> manually per table of interest:
/*
SELECT TOP 5 * FROM dbo.<TableName>;
*/
GO
