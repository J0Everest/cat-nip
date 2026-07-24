import streamlit as st
import pandas as pd
import re
from datetime import date
from _db import init_db_state, run_sql
from config import AIR_EVENTS_DB


# ── shared DB state ───────────────────────────────────────────────────────────
init_db_state()


PERIL_ALIASES = {
    "eq": "EQ",
    "earthquake": "EQ",
    "wind": "Wind",
    "hurricane": "Wind",
    "typhoon": "Wind",
    "flood": "Flood",
    "wildfire": "Wildfire",
    "fire": "Wildfire",
    "fi": "FI",
}


def _parse_scenario_query(text: str):
    q = (text or "").strip().lower()
    out = {
        "peril": None,
        "zone": None,
        "loss_lo": None,
        "loss_hi": None,
        "model": None,
        "event": None,
        "year": None,
        "day": None,
        "event_keyword": None,
    }
    if not q:
        return out

    tokens = [t for t in q.replace(",", " ").split() if t]
    for t in tokens:
        if t in PERIL_ALIASES:
            out["peril"] = PERIL_ALIASES[t]
            break

    import re

    m_zone = re.search(r"(?:zone|region|location)\s*[:=]?\s*([a-z0-9\-\s]+)", q)
    if m_zone:
        out["zone"] = m_zone.group(1).strip()

    m_rng = re.search(r"(\d+(?:\.\d+)?)\s*(?:to|\-)\s*(\d+(?:\.\d+)?)\s*b", q)
    if m_rng:
        out["loss_lo"] = float(m_rng.group(1))
        out["loss_hi"] = float(m_rng.group(2))

    for key, pat in {
        "model": r"model\s*(\d+)",
        "event": r"event\s*(\d+)",
        "year": r"year\s*(\d+)",
        "day": r"day\s*(\d+)",
    }.items():
        m = re.search(pat, q)
        if m:
            out[key] = int(m.group(1))

    m_evt = re.search(r"(?:description|desc|keyword)\s*[:=]?\s*([a-z0-9\-\s]+)", q)
    if m_evt:
        out["event_keyword"] = m_evt.group(1).strip()

    return out


def _pick_col(col_map: dict, aliases: list[str]):
    for a in aliases:
        if a in col_map:
            return col_map[a]
    return None


@st.cache_data(show_spinner=False, ttl=600)
def _discover_air_event_tables(server: str, database: str):
    q = f"""
SELECT c.TABLE_SCHEMA, c.TABLE_NAME, c.COLUMN_NAME
FROM [{AIR_EVENTS_DB}].INFORMATION_SCHEMA.COLUMNS c
JOIN [{AIR_EVENTS_DB}].INFORMATION_SCHEMA.TABLES t
  ON c.TABLE_SCHEMA = t.TABLE_SCHEMA
 AND c.TABLE_NAME = t.TABLE_NAME
WHERE t.TABLE_TYPE = 'BASE TABLE'
ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION;
"""
    try:
        df = run_sql(server, database, q)
    except Exception:
        return []
    if df is None or df.empty:
        return []

    profiles = []
    for (schema, table), g in df.groupby(["TABLE_SCHEMA", "TABLE_NAME"], dropna=False):
        col_map = {str(c).lower(): str(c) for c in g["COLUMN_NAME"].tolist()}
        event_id_col = _pick_col(col_map, ["eventid", "event_id", "eventidnumber"])
        if not event_id_col:
            continue

        profile = {
            "schema": str(schema),
            "table": str(table),
            "event_id_col": event_id_col,
            "model_col": _pick_col(col_map, ["model", "modelno", "model_num", "modelnumber"]),
            "event_col": _pick_col(col_map, ["event", "eventno", "event_num", "eventnumber"]),
            "year_col": _pick_col(col_map, ["year", "eventyear"]),
            "day_col": _pick_col(col_map, ["day", "eventday"]),
            "desc_col": _pick_col(col_map, ["eventdescription", "eventdesc", "description", "desc", "name"]),
            "loc_col": _pick_col(col_map, ["location", "region", "zone", "country", "state", "city"]),
            "mag_col": _pick_col(col_map, ["magnitude", "mag", "maxmagnitude", "intensity"]),
        }

        model_hint = None
        m = re.search(r"(\d{1,4})", str(table))
        if m:
            try:
                model_hint = int(m.group(1))
            except Exception:
                model_hint = None
        profile["model_hint"] = model_hint
        profiles.append(profile)

    return profiles


def _fetch_air_event_details(server: str, database: str, event_ids: list[int], profile: dict):
    if not event_ids or not profile:
        return pd.DataFrame()

    schema = profile["schema"]
    table = profile["table"]
    event_id_col = profile["event_id_col"]
    if not event_id_col:
        return pd.DataFrame()

    ids_csv = ", ".join(str(int(v)) for v in sorted(set(event_ids)))

    select_cols = [f"TRY_CONVERT(bigint, [{event_id_col}]) AS EventID"]
    if profile.get("model_col"):
        select_cols.append(f"TRY_CONVERT(int, [{profile['model_col']}]) AS AIR_Model")
    if profile.get("event_col"):
        select_cols.append(f"TRY_CONVERT(int, [{profile['event_col']}]) AS AIR_Event")
    if profile.get("year_col"):
        select_cols.append(f"TRY_CONVERT(int, [{profile['year_col']}]) AS AIR_Year")
    if profile.get("day_col"):
        select_cols.append(f"TRY_CONVERT(int, [{profile['day_col']}]) AS AIR_Day")
    if profile.get("desc_col"):
        select_cols.append(f"CAST([{profile['desc_col']}] AS nvarchar(4000)) AS AIR_Description")
    if profile.get("loc_col"):
        select_cols.append(f"CAST([{profile['loc_col']}] AS nvarchar(4000)) AS AIR_Location")
    if profile.get("mag_col"):
        select_cols.append(f"TRY_CONVERT(float, [{profile['mag_col']}]) AS AIR_Magnitude")

    q = f"""
SELECT DISTINCT
  {", ".join(select_cols)}
FROM [{AIR_EVENTS_DB}].[{schema}].[{table}]
WHERE TRY_CONVERT(bigint, [{event_id_col}]) IN ({ids_csv});
"""
    try:
        df = run_sql(server, database, q)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    return df

# ─────────────────────────────────────────────────────────────────────────────
# SQL builders  (mirror the Excel waterfall tool logic)
# ─────────────────────────────────────────────────────────────────────────────

def _build_event_search_sql(
    db,
    zone_filter,
    ind_lo,
    ind_hi,
    peril,
    filter_mode="Industry Loss",
    model_no=None,
    event_no=None,
    event_year=None,
    event_day=None,
    event_keyword="",
    location_keyword="",
):
    """
    Builds candidate-event SQL in two modes:
      1) Industry Loss window mode
      2) Event Characteristics mode
    """
    lo = int(ind_lo * 1_000_000_000)
    hi = int(ind_hi * 1_000_000_000)
    zone_like = (zone_filter.strip() or "Zone").split()[0]
    zone_like = zone_like.replace("'", "''")
    event_keyword = (event_keyword or "").strip().replace("'", "''")
    location_keyword = (location_keyword or "").strip().replace("'", "''")
    peril_clause = f"  AND iu.Peril = '{peril}'" if peril and peril != "All" else ""

    if filter_mode == "Event Characteristics":
        char_filters = []
        if model_no is not None:
            char_filters.append(f"ModelNo = {int(model_no)}")
        if event_no is not None:
            char_filters.append(f"EventNo = {int(event_no)}")
        if event_year is not None:
            char_filters.append(f"EventYear = {int(event_year)}")
        if event_day is not None:
            char_filters.append(f"EventDay = {int(event_day)}")
        if event_keyword:
            char_filters.append(f"EventDesc LIKE '%{event_keyword}%'")
        if location_keyword:
            char_filters.append(f"ZoneSample LIKE '%{location_keyword}%'")
        where_char = "WHERE " + " AND ".join(char_filters) if char_filters else ""
        return f"""-- ── Step 1 : Zone filter ────────────────────────────────────────────────────
IF OBJECT_ID('tempdb..#ZoneFilter') IS NOT NULL DROP TABLE #ZoneFilter;
SELECT DISTINCT [Zone]
INTO   #ZoneFilter
FROM   [Industry].[dbo].[Industry_Unadjusted_V21_ZonePercent]
WHERE  [Zone] LIKE '%{zone_like}%';

-- ── Step 2 : Candidate events (characteristics mode) ─────────────────────────
IF OBJECT_ID('tempdb..#Events_NS1') IS NOT NULL DROP TABLE #Events_NS1;
SELECT   iu.EventID,
         iu.Peril,
         MIN(iu.Model)          AS ModelNo,
         MIN(iu.Event)          AS EventNo,
         MIN(iu.[Year])         AS EventYear,
         MIN(iu.[Day])          AS EventDay,
         MIN(iu.[Zone])         AS ZoneSample,
         SUM(iu.Loss)           AS Industry_Loss,
         CONCAT('Model ', MAX(iu.Model), ' Event ', MAX(iu.Event),
                ' (Y', MAX(iu.[Year]), ', D', MAX(iu.[Day]), ')') AS EventDesc
INTO     #Events_NS1
FROM     [Industry].[dbo].[Industry_Unadjusted_V21_ZonePercent] iu
WHERE    iu.[Zone] IN (SELECT [Zone] FROM #ZoneFilter){peril_clause}
  AND    EXISTS (
           SELECT 1
           FROM dbo.All_Loss al
           WHERE al.EventID = iu.EventID
         )
GROUP BY iu.EventID, iu.Peril;

-- ── Step 3 : Return candidate list ───────────────────────────────────────────
SELECT   EventID,
         EventDesc                         AS [Description],
         Peril,
         ModelNo                           AS [Model],
         EventNo                           AS [Event],
         EventYear                         AS [Year],
         EventDay                          AS [Day],
         ZoneSample                        AS [Location],
         ROUND(Industry_Loss / 1e9, 2)     AS [Industry Loss ($B)]
FROM     #Events_NS1
{where_char}
ORDER BY Industry_Loss DESC;"""

    return f"""-- ── Step 1 : Zone filter ────────────────────────────────────────────────────
IF OBJECT_ID('tempdb..#ZoneFilter') IS NOT NULL DROP TABLE #ZoneFilter;
SELECT DISTINCT [Zone]
INTO   #ZoneFilter
FROM   [Industry].[dbo].[Industry_Unadjusted_V21_ZonePercent]
WHERE  [Zone] LIKE '%{zone_like}%';

-- ── Step 2 : Candidate events (industry loss range + zone) ────────────────────
IF OBJECT_ID('tempdb..#Events_NS1') IS NOT NULL DROP TABLE #Events_NS1;
SELECT   iu.EventID,
         iu.Peril,
         SUM(iu.Loss)           AS Industry_Loss,
         CONCAT('Model ', MAX(iu.Model), ' Event ', MAX(iu.Event),
                ' (Y', MAX(iu.[Year]), ', D', MAX(iu.[Day]), ')') AS EventDesc
INTO     #Events_NS1
FROM     [Industry].[dbo].[Industry_Unadjusted_V21_ZonePercent] iu
WHERE    iu.[Zone] IN (SELECT [Zone] FROM #ZoneFilter){peril_clause}
    AND    EXISTS (
                     SELECT 1
                     FROM dbo.All_Loss al
                     WHERE al.EventID = iu.EventID
                 )
GROUP BY iu.EventID, iu.Peril
HAVING   SUM(iu.Loss) BETWEEN {lo} AND {hi};

-- ── Step 3 : Return candidate list ───────────────────────────────────────────
SELECT   EventID,
         EventDesc                         AS [Description],
         Peril,
         ROUND(Industry_Loss / 1e9, 2)     AS [Industry Loss ($B)]
FROM     #Events_NS1
ORDER BY Industry_Loss DESC;"""


def _build_output_sql(db, low_id, med_id, high_id):
    """
    Mirrors the Excel output SQL sheet:
      1. #Events_NS2  – the three selected events with scenario labels
            2. #NetofLogan  – gross loss by layer/event
            3. #Netigan_And_Cessions – net view (recovery placeholder = 0)
      4. Final waterfall SELECT joining All_Contract for terms/ROL/share
    """
    return f"""-- ── Step 1 : Selected scenarios ─────────────────────────────────────────────
IF OBJECT_ID('tempdb..#Events_NS2') IS NOT NULL DROP TABLE #Events_NS2;
SELECT iu.EventID,
       ROUND(SUM(iu.Loss) / 1e9, 2) AS Industry_Loss_B,
       CASE iu.EventID
         WHEN {low_id}  THEN 'Low'
         WHEN {med_id}  THEN 'Med'
         WHEN {high_id} THEN 'High'
       END AS Scenario,
       CONCAT('Model ', MAX(iu.Model), ' Event ', MAX(iu.Event),
              ' (Y', MAX(iu.[Year]), ', D', MAX(iu.[Day]), ')') AS EventDesc
INTO   #Events_NS2
FROM   [Industry].[dbo].[Industry_Unadjusted_V21_ZonePercent] iu
WHERE  iu.EventID IN ({low_id}, {med_id}, {high_id})
GROUP BY iu.EventID;

-- ── Step 2 : Gross loss per layer per scenario ────────────────────────────────
IF OBJECT_ID('tempdb..#NetofLogan') IS NOT NULL DROP TABLE #NetofLogan;
SELECT   lc.layerkey,
         ns.EventID,
         ns.Scenario,
         SUM(COALESCE(lc.grloss, 0)) AS Gross_Loss
INTO     #NetofLogan
FROM     dbo.All_Loss lc
JOIN     #Events_NS2 ns ON lc.eventid = ns.EventID
GROUP BY lc.layerkey, ns.EventID, ns.Scenario;

-- ── Step 3 : Net-of-cessions ──────────────────────────────────────────────────
IF OBJECT_ID('tempdb..#Netigan_And_Cessions') IS NOT NULL DROP TABLE #Netigan_And_Cessions;
SELECT   nl.layerkey,
         nl.EventID,
         nl.Scenario,
         nl.Gross_Loss,
         CAST(0 AS float) AS Reins_Recovery,
         nl.Gross_Loss AS Net_Loss
INTO     #Netigan_And_Cessions
FROM     #NetofLogan nl;

-- ── Step 4 : Final waterfall output ──────────────────────────────────────────
SELECT   c.layerkey,
         nc.Scenario,
         c.Department,
         c.Company,
         c.SubType,
         c.UWS_Contract_Nbr                    AS [Contract #],
         c.[Everest Limit]                     AS [100% Limit ($)],
         c.Terms,
         c.ROL,
         c.Share,
         c.Inception                           AS [From],
         c.Expiration                          AS [To],
         ns.Industry_Loss_B                    AS [Industry Loss ($B)],
         ROUND(nc.Gross_Loss / 1e6, 4)         AS [Gross Loss $M],
         ROUND(nc.Reins_Recovery / 1e6, 4)     AS [Reins Recovery $M],
         ROUND(nc.Net_Loss / 1e6, 4)           AS [Net Loss $M]
FROM     #Netigan_And_Cessions nc
JOIN     dbo.All_Contract c ON c.layerkey = nc.layerkey
                           AND c.status_ind = 'B'
JOIN     #Events_NS2 ns ON ns.EventID = nc.EventID
ORDER BY nc.Scenario, c.Department, c.Company, c.layerkey;"""


# ── Page ──────────────────────────────────────────────────────────────────────
DB = st.session_state.sql_database

st.title("📋 Event Response – Waterfall Builder")
st.caption(f"🗄️ Active CatAccum database: **{DB}** (shared with Scenario Explorer)")

st.divider()

# ── Scenario query (combined from Scenario Explorer) ─────────────────────────
st.markdown("### Scenario Query")
scenario_query = st.text_area(
    "Describe the event",
    key="er_scenario_query",
    height=90,
    placeholder="e.g. Wind in Caribbean Zone 08, 5-50B, model 5, year 38",
)
if st.button("Parse Query into Filters"):
    parsed = _parse_scenario_query(scenario_query)
    if parsed["peril"]:
        st.session_state["er_peril"] = parsed["peril"]
    if parsed["zone"]:
        st.session_state["er_zone"] = parsed["zone"]
    if parsed["loss_lo"] is not None and parsed["loss_hi"] is not None:
        st.session_state["er_loss_range"] = (float(parsed["loss_lo"]), float(parsed["loss_hi"]))
    if parsed["event_keyword"]:
        st.session_state["er_event_keyword"] = parsed["event_keyword"]
    st.success("Filters updated from scenario query.")

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
filter_mode = st.radio(
    "Filter Mode",
    ["Industry Loss", "Event Characteristics"],
    horizontal=True,
    key="er_filter_mode",
)
f1, f2, f3 = st.columns(3)
with f1:
    peril = st.selectbox("Peril", ["All", "EQ", "Wind", "Flood", "Wildfire", "FI"], key="er_peril")
with f2:
    zone_filter = st.text_input("Zone (partial match)", key="er_zone", placeholder="e.g. US  Zone 08")
with f3:
    ind_lo, ind_hi = st.slider("Industry Loss Range ($B)", 0.0, 300.0, (5.0, 100.0), 0.5, key="er_loss_range")

model_no = event_no = event_year = event_day = None
event_keyword = ""
location_keyword = ""
use_air_events = False
air_table_label = None
air_table_profiles = []
mag_lo = mag_hi = None
if filter_mode == "Event Characteristics":
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        model_no = st.number_input("Model #", min_value=0, value=st.session_state.get("er_model", 0), step=1, key="er_model")
        event_no = st.number_input("Event #", min_value=0, value=st.session_state.get("er_event", 0), step=1, key="er_event")
    with c2:
        event_year = st.number_input("Year", min_value=0, value=st.session_state.get("er_year", 0), step=1, key="er_year")
        event_day = st.number_input("Day", min_value=0, value=st.session_state.get("er_day", 0), step=1, key="er_day")
    with c3:
        event_keyword = st.text_input("Event Description keyword", value=st.session_state.get("er_event_keyword", ""), key="er_event_keyword")
        location_keyword = st.text_input("Location keyword", value=st.session_state.get("er_location_keyword", ""), key="er_location_keyword")
    with c4:
        mag_lo, mag_hi = st.slider("Magnitude Range", 0.0, 12.0, (0.0, 12.0), 0.1, key="er_mag_range")
        use_air_events = st.checkbox("Use AIREvents2025_TS13", value=True, key="er_use_air")

    if use_air_events:
        SRV = st.session_state.sql_server
        air_table_profiles = _discover_air_event_tables(SRV, DB)
        if air_table_profiles:
            if model_no and int(model_no) > 0:
                filtered_profiles = [
                    p for p in air_table_profiles
                    if p.get("model_hint") == int(model_no) or str(int(model_no)) in p.get("table", "")
                ]
                air_table_profiles = filtered_profiles or air_table_profiles

            labels = [
                f"{p['schema']}.{p['table']}" + (f"  (model hint {p['model_hint']})" if p.get("model_hint") else "")
                for p in air_table_profiles
            ]
            air_table_label = st.selectbox("AIREvents table", labels, key="er_air_table")
            st.caption("Tables are discovered from AIREvents2025_TS13 and mapped by available columns.")
        else:
            st.warning("No compatible tables discovered in AIREvents2025_TS13.")

    # convert zero -> no filter
    model_no = int(model_no) if int(model_no) > 0 else None
    event_no = int(event_no) if int(event_no) > 0 else None
    event_year = int(event_year) if int(event_year) > 0 else None
    event_day = int(event_day) if int(event_day) > 0 else None

with st.expander("🔍 View generated event-search SQL"):
    st.code(
        _build_event_search_sql(
            DB,
            zone_filter,
            ind_lo,
            ind_hi,
            peril,
            filter_mode,
            model_no,
            event_no,
            event_year,
            event_day,
            "" if use_air_events else event_keyword,
            "" if use_air_events else location_keyword,
        ),
        language="sql",
    )

if st.button("Find Candidate Events", type="primary"):
    try:
        SRV = st.session_state.sql_server
        df_raw = run_sql(
            SRV,
            DB,
            _build_event_search_sql(
                DB,
                zone_filter,
                ind_lo,
                ind_hi,
                peril,
                filter_mode,
                model_no,
                event_no,
                event_year,
                event_day,
                "" if use_air_events else event_keyword,
                "" if use_air_events else location_keyword,
            ),
        )

        # Optional enrichment and filtering from AIREvents2025_TS13
        if (
            filter_mode == "Event Characteristics"
            and use_air_events
            and air_table_profiles
            and air_table_label
            and df_raw is not None
            and not df_raw.empty
        ):
            selected_profile = None
            for p in air_table_profiles:
                lbl = f"{p['schema']}.{p['table']}" + (f"  (model hint {p['model_hint']})" if p.get("model_hint") else "")
                if lbl == air_table_label:
                    selected_profile = p
                    break

            if selected_profile is not None:
                air_df = _fetch_air_event_details(
                    SRV,
                    DB,
                    [int(v) for v in df_raw["EventID"].dropna().tolist()],
                    selected_profile,
                )
                if air_df is not None and not air_df.empty:
                    df_raw = df_raw.merge(air_df, on="EventID", how="left")

                    if model_no is not None and "AIR_Model" in df_raw.columns:
                        df_raw = df_raw[df_raw["AIR_Model"].fillna(-1).astype(int) == int(model_no)]
                    if event_no is not None and "AIR_Event" in df_raw.columns:
                        df_raw = df_raw[df_raw["AIR_Event"].fillna(-1).astype(int) == int(event_no)]
                    if event_year is not None and "AIR_Year" in df_raw.columns:
                        df_raw = df_raw[df_raw["AIR_Year"].fillna(-1).astype(int) == int(event_year)]
                    if event_day is not None and "AIR_Day" in df_raw.columns:
                        df_raw = df_raw[df_raw["AIR_Day"].fillna(-1).astype(int) == int(event_day)]
                    if event_keyword and "AIR_Description" in df_raw.columns:
                        df_raw = df_raw[
                            df_raw["AIR_Description"].astype(str).str.contains(event_keyword, case=False, na=False)
                        ]
                    if location_keyword and "AIR_Location" in df_raw.columns:
                        df_raw = df_raw[
                            df_raw["AIR_Location"].astype(str).str.contains(location_keyword, case=False, na=False)
                        ]
                    if "AIR_Magnitude" in df_raw.columns and mag_lo is not None and mag_hi is not None:
                        df_raw = df_raw[
                            (pd.to_numeric(df_raw["AIR_Magnitude"], errors="coerce") >= float(mag_lo))
                            & (pd.to_numeric(df_raw["AIR_Magnitude"], errors="coerce") <= float(mag_hi))
                        ]

        if df_raw is not None and not df_raw.empty:
            df_raw.insert(0, "✓", False)
            st.session_state["candidates"] = df_raw
        else:
            st.warning("No events found matching those filters.")
            st.session_state.pop("candidates", None)
    except Exception as exc:
        st.error(f"Query failed: {exc}")
        st.session_state.pop("candidates", None)

# ── Candidate table ───────────────────────────────────────────────────────────
if "candidates" in st.session_state:
    st.markdown("### Candidate Events")
    st.caption("Tick events to shortlist, then assign below to Low / Med / High")
    cand = st.session_state["candidates"]
    col_cfg = {"✓": st.column_config.CheckboxColumn()}
    if "Industry Loss ($B)" in cand.columns:
        col_cfg["Industry Loss ($B)"] = st.column_config.NumberColumn(format="$%.2fB")
    edited = st.data_editor(
        cand,
        use_container_width=True, hide_index=True, num_rows="fixed",
        column_config=col_cfg,
    )
    st.session_state["candidates"] = edited

    # Use shortlist if checked rows exist; otherwise use all candidates.
    shortlist = edited[edited["✓"]] if edited["✓"].any() else edited
    selected_event_ids = [int(v) for v in shortlist["EventID"].tolist()]
    selected_ids = ["(none)"] + [str(v) for v in selected_event_ids]

    # Default Low / Med / High = lowest / median / highest by industry loss.
    if "Industry Loss ($B)" in shortlist.columns and len(shortlist) > 0:
        ranked = shortlist.sort_values("Industry Loss ($B)", ascending=True)
    else:
        ranked = shortlist.sort_values("EventID", ascending=True)

    ranked_ids = [str(int(v)) for v in ranked["EventID"].tolist()] if len(ranked) else []
    default_low = ranked_ids[0] if ranked_ids else "(none)"
    default_med = ranked_ids[len(ranked_ids) // 2] if ranked_ids else "(none)"
    default_high = ranked_ids[-1] if ranked_ids else "(none)"

    if st.session_state.get("low_pick") not in selected_ids:
        st.session_state["low_pick"] = default_low
    if st.session_state.get("med_pick") not in selected_ids:
        st.session_state["med_pick"] = default_med
    if st.session_state.get("high_pick") not in selected_ids:
        st.session_state["high_pick"] = default_high

    st.divider()

    # ── Low / Med / High assignment ───────────────────────────────────────────
    st.markdown("### Assign Scenarios")
    s1, s2, s3 = st.columns(3)
    with s1:
        st.markdown("**Low**")
        low_pick = st.selectbox("From shortlist", selected_ids, key="low_pick")
        if low_pick == "(none)":
            low_id_manual = st.number_input(
                "EventID (Low)", min_value=0, value=0, step=1, key="low_id_manual",
                label_visibility="collapsed"
            )
            low_id = int(low_id_manual)
        else:
            low_id = int(low_pick)
    with s2:
        st.markdown("**Med**")
        med_pick = st.selectbox("From shortlist", selected_ids, key="med_pick")
        if med_pick == "(none)":
            med_id_manual = st.number_input(
                "EventID (Med)", min_value=0, value=0, step=1, key="med_id_manual",
                label_visibility="collapsed"
            )
            med_id = int(med_id_manual)
        else:
            med_id = int(med_pick)
    with s3:
        st.markdown("**High**")
        high_pick = st.selectbox("From shortlist", selected_ids, key="high_pick")
        if high_pick == "(none)":
            high_id_manual = st.number_input(
                "EventID (High)", min_value=0, value=0, step=1, key="high_id_manual",
                label_visibility="collapsed"
            )
            high_id = int(high_id_manual)
        else:
            high_id = int(high_pick)

    with st.expander("🔍 View generated output SQL (populates waterfall)"):
        st.code(_build_output_sql(DB, int(low_id), int(med_id), int(high_id)), language="sql")

    st.divider()

    # ── Actions ───────────────────────────────────────────────────────────────
    st.markdown("### Build Response Package")
    a1, a2 = st.columns(2)
    with a1:
        if st.button("▶ Run & Populate Template", use_container_width=True, type="primary"):
            with st.spinner("Running waterfall query…"):
                SRV = st.session_state.sql_server
                try:
                    df_out = run_sql(SRV, DB, _build_output_sql(DB, int(low_id), int(med_id), int(high_id)))
                    if df_out is not None and not df_out.empty:
                        summary_df = (
                            df_out.groupby("Scenario", dropna=False)
                            .agg(
                                impacted_contracts=("Contract #", "nunique"),
                                industry_loss_b=("Industry Loss ($B)", "max"),
                                gross_loss_m=("Gross Loss $M", "sum"),
                            )
                            .reset_index()
                            .rename(
                                columns={
                                    "Scenario": "Scenario",
                                    "impacted_contracts": "Impacted Contracts",
                                    "industry_loss_b": "Industry Loss ($B)",
                                    "gross_loss_m": "Gross Loss $M",
                                }
                            )
                        )

                        loss_by_contract = (
                            df_out.pivot_table(
                                index=["layerkey", "Contract #", "Department", "Company", "SubType"],
                                columns="Scenario",
                                values="Gross Loss $M",
                                aggfunc="sum",
                                fill_value=0.0,
                            )
                            .reset_index()
                        )
                        loss_by_contract.columns = [str(c) for c in loss_by_contract.columns]
                        for sc in ["Low", "Med", "High"]:
                            if sc not in loss_by_contract.columns:
                                loss_by_contract[sc] = 0.0
                        loss_by_contract = loss_by_contract[
                            ["layerkey", "Contract #", "Department", "Company", "SubType", "Low", "Med", "High"]
                        ].rename(
                            columns={
                                "Low": "Low Gross Loss $M",
                                "Med": "Med Gross Loss $M",
                                "High": "High Gross Loss $M",
                            }
                        )

                        st.markdown("#### Event Summary")
                        st.dataframe(summary_df, use_container_width=True, hide_index=True)

                        st.markdown("#### Loss by Contract (Low / Med / High)")
                        st.dataframe(loss_by_contract, use_container_width=True, hide_index=True)

                        st.success(f"✅ {len(df_out):,} rows returned")
                        st.dataframe(df_out, use_container_width=True, hide_index=True)
                        st.session_state["waterfall_df"] = df_out
                    else:
                        st.warning("Query returned no rows for these event IDs.")
                except Exception as exc:
                    st.error(f"Waterfall query failed: {exc}")
    with a2:
        if st.button("⬇ Export Workbook (.xlsm)", use_container_width=True):
            if "waterfall_df" in st.session_state:
                st.info("(openpyxl export will trigger here)")
            else:
                st.warning("Run the query first before exporting.")
else:
    st.info("Set filters and click **Find Candidate Events** to begin.")
