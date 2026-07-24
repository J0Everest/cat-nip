import streamlit as st
import pandas as pd
from datetime import date


# ── helpers ───────────────────────────────────────────────────────────────────
def _latest_closed_quarter() -> str:
    """Return e.g. 'CatAccum2601' for the most recently closed calendar quarter."""
    today = date.today()
    y2 = today.year % 100
    closed = [(3, 1), (6, 4), (9, 7), (12, 10)]
    best_db = 1
    for qend_month, db_month in closed:
        if today.month > qend_month or (today.month == qend_month and today.day >= 15):
            best_db = db_month
    return f"CatAccum{y2:02d}{best_db:02d}"


def _build_event_search_sql(db, zone_filter, ind_lo, ind_hi, peril):
    lo = int(ind_lo * 1_000_000_000)
    hi = int(ind_hi * 1_000_000_000)
    peril_clause = f"  AND e.peril = '{peril}'" if peril != "All" else ""
    zone_like = zone_filter or "Caribbean"
    return f"""-- Auto-generated  |  Database: {db}
USE {db}; GO

IF object_id('tempdb..#ZoneFilter') IS NOT NULL DROP TABLE #ZoneFilter
GO
CREATE TABLE #ZoneFilter (Zone_cd nvarchar(64))
INSERT INTO #ZoneFilter (zone_cd)
  SELECT DISTINCT zone_cd
  FROM industry_dbo.Industry_Unadjusted_TVAR_11_All_Aug25_ZonePercent
  WHERE zone_cd LIKE '%{zone_like}%'
GO

-- Candidate events filtered by zone and industry loss range
SELECT DISTINCT
  e.EventID,
  e.MaxWind2          AS MaxMag_or_Wind,
  e.[Desc]            AS EventDescription,
  a.loss / 1e9        AS [Industry Loss ($B)]
FROM industry_dbo.[IndustryFinalView] a
JOIN #Events_NS1 e ON a.EventID = e.EventID
WHERE a.Zone IN (SELECT zone_cd FROM #ZoneFilter)
  AND a.loss BETWEEN {lo} AND {hi}{peril_clause}
ORDER BY a.loss DESC
GO"""


def _build_output_sql(db, low_id, med_id, high_id):
    return f"""-- Output SQL – feeds waterfall template  |  Database: {db}
USE {db}; GO

SELECT
  a.layerkey,
  CASE d.eventid
    WHEN {low_id}  THEN 'Low'
    WHEN {med_id}  THEN 'Med'
    WHEN {high_id} THEN 'High'
  END                             AS Scenario,
  a.Department, a.Company, a.SubType,
  a.UWS_Contract_Nbr              AS Contract,
  b.[Everest Limit]               AS [100% Limit],
  b.Retention, b.[Aggregate Deductible],
  b.Terms, b.ROL, b.Share,
  b.Inception AS [From], b.Expiration AS [To],
  d.loss / 1e9                    AS [Industry Loss ($B)],
  SUM(COALESCE(g.loss, 0)) / 1e6  AS [Gross Loss $M]
FROM dbo.All_Loss_Contract a
JOIN dbo.All_Contract b   ON a.layerkey = b.layerkey
JOIN #Events_NS2 d        ON a.eventid  = d.EventID
LEFT JOIN dbo.gross g     ON a.layerkey = g.layerkey AND a.eventid = g.eventid
WHERE d.eventid IN ({low_id}, {med_id}, {high_id})
GROUP BY a.layerkey, d.eventid, a.Department, a.Company, a.SubType,
         a.UWS_Contract_Nbr, b.[Everest Limit], b.Retention,
         b.[Aggregate Deductible], b.Terms, b.ROL, b.Share,
         b.Inception, b.Expiration, d.loss
ORDER BY a.layerkey, d.eventid
GO"""


# ── Page ──────────────────────────────────────────────────────────────────────
DB = _latest_closed_quarter()

st.title("📋 Event Response – Waterfall Builder")
st.caption(f"🗄️ Active CatAccum database: **{DB}** (auto-detected latest closed quarter)")

st.divider()

# ── Event metadata ────────────────────────────────────────────────────────────
st.markdown("### Event Details")
m1, m2, m3, m4 = st.columns(4)
with m1:
    event_name = st.text_input("Event Name", placeholder="e.g. Winter Storm Fern")
with m2:
    event_region = st.selectbox("Event Region", [
        "North America", "Caribbean", "South America",
        "Europe", "Asia Pacific", "Middle East / Africa",
    ])
with m3:
    st.date_input("Date Created", value=date.today())
with m4:
    st.date_input("Data As-Of Date", value=date.today())

st.divider()

# ── Event filters ─────────────────────────────────────────────────────────────
st.markdown("### Find Events")
f1, f2, f3 = st.columns(3)
with f1:
    peril = st.selectbox("Peril", ["All", "EQ", "Wind", "Flood", "Wildfire"])
with f2:
    zone_filter = st.text_input("Zone (partial match)", placeholder="e.g. Caribbean Jamaica")
with f3:
    ind_lo, ind_hi = st.slider("Industry Loss Range ($B)", 0.0, 300.0, (5.0, 100.0), 0.5)

with st.expander("🔍 View generated event-search SQL"):
    st.code(_build_event_search_sql(DB, zone_filter, ind_lo, ind_hi, peril), language="sql")

if st.button("Find Candidate Events", type="primary"):
    st.session_state["candidates"] = pd.DataFrame([
        {"✓": False, "EventID": 280066590, "Description": "Cat-4 Hurricane Jamaica",   "Max Wind (kt)": 135, "Industry Loss ($B)": 42.5},
        {"✓": False, "EventID": 280037801, "Description": "Cat-3 Hurricane Caribbean", "Max Wind (kt)": 115, "Industry Loss ($B)": 28.1},
        {"✓": False, "EventID": 280014790, "Description": "Cat-2 Hurricane Jamaica",   "Max Wind (kt)":  96, "Industry Loss ($B)": 12.4},
        {"✓": False, "EventID": 280098234, "Description": "Cat-3 Hurricane Haiti",     "Max Wind (kt)": 110, "Industry Loss ($B)": 19.7},
        {"✓": False, "EventID": 280011102, "Description": "Cat-1 Hurricane Caribbean", "Max Wind (kt)":  82, "Industry Loss ($B)":  7.3},
    ])

# ── Candidate table ───────────────────────────────────────────────────────────
if "candidates" in st.session_state:
    st.markdown("### Candidate Events")
    st.caption("Tick events to shortlist, then assign below to Low / Med / High")
    edited = st.data_editor(
        st.session_state["candidates"],
        use_container_width=True, hide_index=True, num_rows="fixed",
        column_config={
            "✓": st.column_config.CheckboxColumn(),
            "Industry Loss ($B)": st.column_config.NumberColumn(format="$%.1fB"),
        },
    )
    st.session_state["candidates"] = edited
    selected_ids = ["(none)"] + [str(r["EventID"]) for _, r in edited[edited["✓"]].iterrows()]

    st.divider()

    # ── Low / Med / High assignment (mirrors Input tab) ───────────────────────
    st.markdown("### Assign Scenarios  *(mirrors Input tab)*")
    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown("**Low**")
        low_pick = st.selectbox("From shortlist", selected_ids, key="low_pick")
        low_id   = st.number_input("EventID (Low)",  value=280066590, step=1, key="low_id",
                                   label_visibility="collapsed")
        if low_pick != "(none)": st.session_state["low_id"] = int(low_pick)
    with s2:
        st.markdown("**Med**")
        med_pick = st.selectbox("From shortlist", selected_ids, key="med_pick")
        med_id   = st.number_input("EventID (Med)",  value=280037801, step=1, key="med_id",
                                   label_visibility="collapsed")
        if med_pick != "(none)": st.session_state["med_id"] = int(med_pick)
    with s3:
        st.markdown("**High**")
        high_pick = st.selectbox("From shortlist", selected_ids, key="high_pick")
        high_id   = st.number_input("EventID (High)", value=280014790, step=1, key="high_id",
                                    label_visibility="collapsed")
        if high_pick != "(none)": st.session_state["high_id"] = int(high_pick)

    with st.expander("🔍 View generated output SQL (populates waterfall)"):
        st.code(_build_output_sql(DB, int(low_id), int(med_id), int(high_id)), language="sql")

    st.divider()

    # ── Actions ───────────────────────────────────────────────────────────────
    st.markdown("### Build Response Package")
    a1, a2 = st.columns(2)
    with a1:
        if st.button("▶ Run & Populate Template", use_container_width=True, type="primary"):
            st.info("(Live CatAccum query and Excel population will run here)")
    with a2:
        if st.button("⬇ Export Workbook (.xlsm)", use_container_width=True):
            st.info("(openpyxl export will trigger here)")
else:
    st.info("Set filters and click **Find Candidate Events** to begin.")
