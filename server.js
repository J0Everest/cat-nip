require("dotenv").config();
const path = require("path");
const express = require("express");
const { sql, getPool, getCatAccumPool } = require("./db");

const app = express();
const PORT = Number(process.env.PORT || 3000);

app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

const PERIL_KEYWORDS = [
  "hurricane",
  "windstorm",
  "earthquake",
  "wildfire",
  "flood",
  "hail",
  "tornado",
  "typhoon",
  "storm surge"
];

const REGION_KEYWORDS = [
  "florida",
  "california",
  "texas",
  "new york",
  "gulf coast",
  "southeast",
  "northeast",
  "midwest",
  "japan",
  "europe",
  "uk"
];

function detectKeyword(question, list) {
  const lower = String(question || "").toLowerCase();
  return list.find((item) => lower.includes(item)) || null;
}

// ── US state centroids + common CAT zone region fallbacks ──────────────────
const US_STATE_GEO = {
  AL:{lat:32.8,lon:-86.8},  AK:{lat:64.2,lon:-153.4}, AZ:{lat:34.0,lon:-111.1},
  AR:{lat:34.8,lon:-92.2},  CA:{lat:36.8,lon:-119.4},  CO:{lat:39.1,lon:-105.4},
  CT:{lat:41.6,lon:-72.7},  DE:{lat:39.0,lon:-75.5},   FL:{lat:27.8,lon:-81.8},
  GA:{lat:32.2,lon:-83.4},  HI:{lat:20.3,lon:-156.4},  ID:{lat:44.1,lon:-114.5},
  IL:{lat:40.0,lon:-89.2},  IN:{lat:39.8,lon:-86.1},   IA:{lat:42.1,lon:-93.5},
  KS:{lat:38.5,lon:-98.4},  KY:{lat:37.7,lon:-85.0},   LA:{lat:30.5,lon:-91.7},
  ME:{lat:45.3,lon:-69.2},  MD:{lat:38.9,lon:-76.6},   MA:{lat:42.2,lon:-71.5},
  MI:{lat:44.3,lon:-85.4},  MN:{lat:46.0,lon:-94.3},   MS:{lat:32.4,lon:-89.7},
  MO:{lat:38.4,lon:-92.5},  MT:{lat:46.9,lon:-110.5},  NE:{lat:41.5,lon:-99.9},
  NV:{lat:38.5,lon:-117.1}, NH:{lat:43.7,lon:-71.6},   NJ:{lat:40.1,lon:-74.5},
  NM:{lat:34.5,lon:-106.2}, NY:{lat:42.7,lon:-74.9},   NC:{lat:35.6,lon:-79.4},
  ND:{lat:47.5,lon:-100.4}, OH:{lat:40.4,lon:-82.8},   OK:{lat:35.6,lon:-97.5},
  OR:{lat:43.9,lon:-120.6}, PA:{lat:40.8,lon:-77.8},   RI:{lat:41.7,lon:-71.5},
  SC:{lat:33.9,lon:-81.0},  SD:{lat:44.4,lon:-100.2},  TN:{lat:35.8,lon:-86.3},
  TX:{lat:31.0,lon:-97.7},  UT:{lat:39.3,lon:-111.5},  VT:{lat:44.1,lon:-72.7},
  VA:{lat:37.8,lon:-79.5},  WA:{lat:47.4,lon:-120.6},  WV:{lat:38.7,lon:-80.7},
  WI:{lat:44.3,lon:-89.6},  WY:{lat:42.8,lon:-107.6},
  // Region fallbacks
  GULF:{lat:29.5,lon:-89.5},      USGULF:{lat:29.5,lon:-89.5},
  SOUTHEAST:{lat:32.0,lon:-84.0}, NORTHEAST:{lat:42.0,lon:-74.0},
  MIDWEST:{lat:41.0,lon:-93.0},   WESTCOAST:{lat:37.0,lon:-120.0},
  PACIFIC:{lat:37.0,lon:-120.0},  JAPAN:{lat:36.2,lon:138.3},
  JPN:{lat:36.2,lon:138.3},       EUROPE:{lat:50.0,lon:10.0},
  UK:{lat:52.0,lon:-1.5},         AUS:{lat:-25.3,lon:133.8}
};

function zoneToGeo(zone) {
  if (!zone) return null;
  const z = String(zone).toUpperCase().trim();
  if (US_STATE_GEO[z]) return US_STATE_GEO[z];
  const parts = z.split(/[-_\s,;]+/);
  for (const part of [...parts].reverse()) {
    if (part.length >= 2 && US_STATE_GEO[part]) return US_STATE_GEO[part];
  }
  return null;
}

app.get("/api/health", async (req, res) => {
  try {
    const pool = await getPool();
    await pool.request().query("SELECT 1 AS ok");
    res.json({ ok: true });
  } catch (error) {
    res.status(500).json({ ok: false, error: error.message });
  }
});

app.get("/api/placements", async (req, res) => {
  try {
    const pool = await getPool();
    const result = await pool.request().query(`
      SELECT
        CAST(group_no AS INT) AS [group],
        CONVERT(VARCHAR(10), as_of_date, 101) AS asOfDate,
        [status],
        layer_desc AS layerDesc,
        terms,
        curr,
        reinst,
        rol,
        cr,
        sdf,
        roe,
        final_share AS finalShare,
        our_limit AS ourLimit,
        our_premium AS ourPremium,
        final_rate AS finalRate,
        subject_base AS subjectBase,
        contract,
        [user_name] AS [user]
      FROM dbo.pricing_history
      ORDER BY group_no,
        CASE [status]
          WHEN 'Quoted' THEN 1
          WHEN 'Authorized' THEN 2
          WHEN 'Bound' THEN 3
          ELSE 4
        END,
        as_of_date;
    `);

    res.json(result.recordset);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ── /api/schema-check ─────────────────────────────────────────────────────
app.get("/api/schema-check", async (req, res) => {
  try {
    const pool = await getCatAccumPool();
    const check = await pool.request().query(`
      SELECT
        OBJECT_ID('dbo.All_Loss',         'U') AS has_All_Loss,
        OBJECT_ID('dbo.All_Contract',     'U') AS has_All_Contract,
        OBJECT_ID('dbo.All_Contract_AAL', 'U') AS has_All_Contract_AAL,
        OBJECT_ID('dbo.ReinsLoss',        'U') AS has_ReinsLoss
    `);
    const t = check.recordset[0];
    const allOk = Object.values(t).every((v) => v !== null);
    res.json({ ok: allOk, tables: t });
  } catch (error) {
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ── /api/cataccum/kpis ─────────────────────────────────────────────────────
// Portfolio-level AAL KPIs sourced from dbo.All_Contract_AAL (101K rows)
app.get("/api/cataccum/kpis", async (req, res) => {
  try {
    const pool = await getCatAccumPool();
    const result = await pool.request().query(`
      SELECT
        SUM(GrossAAL)                                  / 1e6 AS total_gross_aal_m,
        SUM(NetofRIPAAL)                               / 1e6 AS total_net_aal_m,
        SUM(GrossAAL - ISNULL(NetofRIPAAL, 0))         / 1e6 AS total_ceded_m,
        MIN(NULLIF(GrossAAL, 0))                       / 1e6 AS min_gross_aal_m,
        MAX(GrossAAL)                                  / 1e6 AS max_gross_aal_m,
        MIN(NULLIF(NetofRIPAAL, 0))                    / 1e6 AS min_net_aal_m,
        MAX(NetofRIPAAL)                               / 1e6 AS max_net_aal_m,
        COUNT(DISTINCT layerkey)                            AS contract_count
      FROM dbo.All_Contract_AAL WITH (NOLOCK)
    `);
    res.json(result.recordset[0]);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ── /api/cataccum/exposure-map ─────────────────────────────────────────────
// Top 200 peril-zone avg annual gross losses from dbo.All_Loss, with geo coords
app.get("/api/cataccum/exposure-map", async (req, res) => {
  try {
    const pool = await getCatAccumPool();
    const result = await pool.request().query(`
      SELECT TOP 200
        peril,
        zone,
        COUNT(DISTINCT layerkey)                                    AS contract_count,
        SUM(grloss) / NULLIF(COUNT(DISTINCT [year]), 0) / 1e6      AS avg_annual_loss_m
      FROM dbo.All_Loss WITH (NOLOCK)
      WHERE grloss > 0
      GROUP BY peril, zone
      ORDER BY SUM(grloss) / NULLIF(COUNT(DISTINCT [year]), 0) DESC
    `);

    const items = result.recordset
      .map((row) => {
        const geo = zoneToGeo(row.zone);
        if (!geo) return null;
        return {
          peril:             row.peril,
          zone:              row.zone,
          lat:               geo.lat,
          lon:               geo.lon,
          contract_count:    Number(row.contract_count),
          avg_annual_loss_m: Math.round(Number(row.avg_annual_loss_m || 0) * 10) / 10
        };
      })
      .filter(Boolean);

    res.json(items);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ── /api/cataccum/ep-curve ─────────────────────────────────────────────────
// Annual aggregate gross loss percentiles from dbo.All_Loss YELT
app.get("/api/cataccum/ep-curve", async (req, res) => {
  try {
    const pool = await getCatAccumPool();
    const result = await pool.request().query(`
      WITH annual AS (
        SELECT [year], SUM(grloss) / 1e6 AS annual_loss_m
        FROM dbo.All_Loss WITH (NOLOCK)
        GROUP BY [year]
      ),
      pcts AS (
        SELECT
          PERCENTILE_CONT(0.10)  WITHIN GROUP (ORDER BY annual_loss_m) OVER () AS p10,
          PERCENTILE_CONT(0.50)  WITHIN GROUP (ORDER BY annual_loss_m) OVER () AS p50,
          PERCENTILE_CONT(0.90)  WITHIN GROUP (ORDER BY annual_loss_m) OVER () AS p90,
          PERCENTILE_CONT(0.996) WITHIN GROUP (ORDER BY annual_loss_m) OVER () AS p250,
          COUNT(*) OVER () AS sim_years
        FROM annual
      )
      SELECT DISTINCT p10, p50, p90, p250, sim_years FROM pcts
    `);
    const row = result.recordset[0] || {};
    res.json({
      p10:       Math.round(Number(row.p10  || 0)),
      p50:       Math.round(Number(row.p50  || 0)),
      p90:       Math.round(Number(row.p90  || 0)),
      p250:      Math.round(Number(row.p250 || 0)),
      sim_years: Number(row.sim_years || 0)
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ── /api/copilot/ask ──────────────────────────────────────────────────────
// Filters dbo.All_Loss by peril (peril column) and region (zone column)
app.post("/api/copilot/ask", async (req, res) => {
  const question = String(req.body?.question || "").trim();
  if (!question) return res.status(400).json({ error: "A question is required." });

  const detectedPeril  = detectKeyword(question, PERIL_KEYWORDS);
  const detectedRegion = detectKeyword(question, REGION_KEYWORDS);

  const perilFilter  = detectedPeril  ? `%${detectedPeril}%`  : null;
  const regionFilter = detectedRegion ? `%${detectedRegion}%` : null;

  try {
    const pool = await getCatAccumPool();
    const result = await pool.request()
      .input("perilFilter",  sql.NVarChar(150), perilFilter)
      .input("regionFilter", sql.NVarChar(150), regionFilter)
      .query(`
        SELECT TOP 10
          al.peril,
          al.zone,
          COUNT(DISTINCT al.layerkey)                                  AS contract_count,
          SUM(al.grloss) / NULLIF(COUNT(DISTINCT al.[year]), 0) / 1e6 AS avg_annual_loss_m
        FROM dbo.All_Loss al WITH (NOLOCK)
        WHERE al.grloss > 0
          AND (@perilFilter  IS NULL OR al.peril LIKE @perilFilter)
          AND (@regionFilter IS NULL OR al.zone  LIKE @regionFilter)
        GROUP BY al.peril, al.zone
        ORDER BY SUM(al.grloss) / NULLIF(COUNT(DISTINCT al.[year]), 0) DESC
      `);

    const items = result.recordset.map((row) => ({
      peril:         row.peril,
      region:        row.zone,
      contractCount: Number(row.contract_count),
      totalImpact:   Math.round(Number(row.avg_annual_loss_m || 0) * 10) / 10
    }));

    const grandTotal = items.reduce((s, r) => s + r.totalImpact, 0);
    const summary = items.length
      ? `Found ${items.length} peril-zone combinations. Avg annual gross loss: $${grandTotal.toFixed(1)}M.`
      : "No matching records in CatAccum for the detected peril/region.";

    res.json({
      summary,
      detected: { peril: detectedPeril, region: detectedRegion },
      source:   { table: "dbo.All_Loss", metric: "avg annual gross loss ($M)" },
      items
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.get("*", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

app.listen(PORT, () => {
  console.log(`App running at http://localhost:${PORT}`);
});
