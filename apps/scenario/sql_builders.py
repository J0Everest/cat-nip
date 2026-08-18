from apps.scenario.services import industry_peril_clause


def build_event_search_sql(db, zone_filter, ind_lo, ind_hi, peril, filter_mode="Industry Loss", event_keyword=""):
    lo = int(ind_lo * 1_000_000_000)
    hi = int(ind_hi * 1_000_000_000)
    zone_like = (zone_filter.strip() or "Zone").split()[0].replace("'", "''")
    event_keyword = (event_keyword or "").strip().replace("'", "''")
    peril_clause = f"  {industry_peril_clause(peril)}" if peril and peril != "All" else ""
    use_industry = filter_mode in ("Industry Loss", "Both")
    use_characteristics = filter_mode in ("Event Characteristics", "Both")
    industry_range_is_set = not (float(ind_lo) <= 0.0 and float(ind_hi) >= 300.0)
    where_char = f"WHERE EventDesc LIKE '%{event_keyword}%'" if (use_characteristics and event_keyword) else ""
    having_clause = (
        f"HAVING SUM(iu.Loss) BETWEEN {lo} AND {hi}"
        if (use_industry and industry_range_is_set)
        else ""
    )

    return f"""
IF OBJECT_ID('tempdb..#ZoneFilter') IS NOT NULL DROP TABLE #ZoneFilter;
SELECT DISTINCT [Zone]
INTO #ZoneFilter
FROM [Industry].[dbo].[Industry_Unadjusted_V21_ZonePercent]
WHERE [Zone] LIKE '%{zone_like}%';

IF OBJECT_ID('tempdb..#Events_NS1') IS NOT NULL DROP TABLE #Events_NS1;
SELECT iu.EventID,
       iu.Peril,
       SUM(iu.Loss) AS Industry_Loss,
       CONCAT('Model ', MAX(iu.Model), ' Event ', MAX(iu.Event),
              ' (Y', MAX(iu.[Year]), ', D', MAX(iu.[Day]), ')') AS EventDesc
INTO #Events_NS1
FROM [Industry].[dbo].[Industry_Unadjusted_V21_ZonePercent] iu
WHERE iu.[Zone] IN (SELECT [Zone] FROM #ZoneFilter){peril_clause}
  AND EXISTS (SELECT 1 FROM dbo.All_Loss al WHERE al.EventID = iu.EventID)
GROUP BY iu.EventID, iu.Peril
{having_clause};

SELECT EventID,
       EventDesc AS [Description],
       Peril,
       ROUND(Industry_Loss / 1e9, 2) AS [Industry Loss ($B)]
FROM #Events_NS1
{where_char}
ORDER BY Industry_Loss DESC;
"""


def build_output_sql(db, low_id, med_id, high_id):
    return f"""
IF OBJECT_ID('tempdb..#Events_NS2') IS NOT NULL DROP TABLE #Events_NS2;
SELECT iu.EventID,
       ROUND(SUM(iu.Loss) / 1e9, 2) AS Industry_Loss_B,
       CASE iu.EventID
         WHEN {low_id} THEN 'Low'
         WHEN {med_id} THEN 'Med'
         WHEN {high_id} THEN 'High'
       END AS Scenario
INTO #Events_NS2
FROM [Industry].[dbo].[Industry_Unadjusted_V21_ZonePercent] iu
WHERE iu.EventID IN ({low_id}, {med_id}, {high_id})
GROUP BY iu.EventID;

IF OBJECT_ID('tempdb..#NetofLogan') IS NOT NULL DROP TABLE #NetofLogan;
SELECT lc.layerkey,
       ns.EventID,
       ns.Scenario,
       SUM(COALESCE(lc.grloss, 0)) AS Gross_Loss
INTO #NetofLogan
FROM dbo.All_Loss lc
JOIN #Events_NS2 ns ON lc.eventid = ns.EventID
GROUP BY lc.layerkey, ns.EventID, ns.Scenario;

IF OBJECT_ID('tempdb..#Netigan_And_Cessions') IS NOT NULL DROP TABLE #Netigan_And_Cessions;
SELECT nl.layerkey,
       nl.EventID,
       nl.Scenario,
       nl.Gross_Loss,
       CAST(0 AS float) AS Reins_Recovery,
       nl.Gross_Loss AS Net_Loss
INTO #Netigan_And_Cessions
FROM #NetofLogan nl;

SELECT c.layerkey,
       nc.Scenario,
       c.Department,
       c.Company,
       c.SubType,
       c.UWS_Contract_Nbr AS [Contract #],
       c.[Everest Limit] AS [100% Limit ($)],
       c.Terms,
       c.ROL,
       c.Share,
       c.Inception AS [From],
       c.Expiration AS [To],
       ns.Industry_Loss_B AS [Industry Loss ($B)],
       ROUND(nc.Gross_Loss / 1e6, 4) AS [Gross Loss $M],
       ROUND(nc.Reins_Recovery / 1e6, 4) AS [Reins Recovery $M],
       ROUND(nc.Net_Loss / 1e6, 4) AS [Net Loss $M]
FROM #Netigan_And_Cessions nc
JOIN dbo.All_Contract c ON c.layerkey = nc.layerkey AND c.status_ind = 'B'
JOIN #Events_NS2 ns ON ns.EventID = nc.EventID
ORDER BY nc.Scenario, c.Department, c.Company, c.layerkey;
"""
