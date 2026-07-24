import re
import json
from datetime import date

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from _db import init_db_state, run_sql
from config import AIR_EVENTS_DB


init_db_state()

PERIL_ALIASES = {
    "eq": "EQ",
    "earthquake": "EQ",
    "wind": "Wind",
    "storm": "Wind",
    "winter": "Wind",
    "winterstorm": "Wind",
    "hurricane": "Wind",
    "typhoon": "Wind",
    "flood": "Flood",
    "wildfire": "Wildfire",
    "fire": "Wildfire",
    "fi": "FI",
}

ZONE_TOKEN_MAP = {
    "us": "US",
    "usa": "US",
    "u.s.": "US",
    "unitedstates": "US",
    "united states": "US",
    "venezuela": "Venezuela",
    "venezuelan": "Venezuela",
    "colombia": "Colombia",
    "colombian": "Colombia",
    "peru": "Peru",
    "peruvian": "Peru",
    "ecuador": "Ecuador",
    "ecuadorian": "Ecuador",
    "chile": "Chile",
    "chilean": "Chile",
    "mexico": "Mexico",
    "mexican": "Mexico",
    "japan": "Japan",
    "japanese": "Japan",
}

_QUERY_STOPWORDS = {
    "and", "or", "the", "a", "an", "for", "of", "in", "on", "to",
    "industry", "loss", "range", "event", "description", "keyword", "model",
    "with", "from",
}

_STATE_TOKENS = {
    "ny", "tx", "ma", "ct", "pa", "nj", "ca", "fl", "la", "ms", "al", "ga",
    "nc", "sc", "va", "md", "ri", "nh", "vt", "me", "wa", "or", "az", "nm",
    "co", "ut", "nv", "id", "mt", "wy", "nd", "sd", "ne", "ks", "ok", "mo",
    "ia", "mn", "wi", "il", "in", "mi", "oh", "ky", "tn", "ar", "wv", "de",
}


def _parse_scenario_query(text: str):
    q = (text or "").strip().lower()
    out = {
        "peril": None,
        "zone": None,
        "model_no": None,
        "loss_lo": None,
        "loss_hi": None,
        "mag_lo": None,
        "mag_hi": None,
        "event_keyword": None,
    }
    if not q:
        return out

    tokens = [t for t in q.replace(",", " ").split() if t]
    for t in tokens:
        if t in PERIL_ALIASES:
            out["peril"] = PERIL_ALIASES[t]
            break

    m_zone = re.search(r"(?:zone|region|location)\s*[:=]?\s*([a-z0-9\-\s]+)", q)
    if m_zone:
        out["zone"] = m_zone.group(1).strip()
    else:
        for t in tokens:
            if t in ZONE_TOKEN_MAP:
                out["zone"] = ZONE_TOKEN_MAP[t]
                break

    # Industry loss ranges, e.g. "3.25-5.5 Industry Loss" or "3.25 to 5.5b"
    m_rng = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:to|\-)\s*(\d+(?:\.\d+)?)(?:\s*(?:b|bn|billion))?\s*(?:industry\s*loss)?",
        q,
    )
    if m_rng:
        out["loss_lo"] = float(m_rng.group(1))
        out["loss_hi"] = float(m_rng.group(2))

    # Magnitude ranges like "magnitude 7.2-7.6" or "mag 6.5 to 7.0"
    m_mag = re.search(r"(?:magnitude|mag)\s*(\d+(?:\.\d+)?)\s*(?:to|\-)\s*(\d+(?:\.\d+)?)", q)
    if m_mag:
        out["mag_lo"] = float(m_mag.group(1))
        out["mag_hi"] = float(m_mag.group(2))

    m_model = re.search(r"(?:model|m)\s*#?\s*(\d{1,4})", q)
    if m_model:
        out["model_no"] = int(m_model.group(1))

    m_evt = re.search(r"(?:description|desc|keyword)\s*[:=]?\s*([a-z0-9\-\s]+)", q)
    if m_evt:
        out["event_keyword"] = m_evt.group(1).strip()

    return out


def _pick_col(col_map: dict, aliases: list[str]):
    for a in aliases:
        if a in col_map:
            return col_map[a]
    return None


def _peril_table_tokens(peril: str):
    p = (peril or "All").strip().lower()
    if p == "eq":
        return ["earthquake", "eq", "quake", "seismic"]
    if p == "wind":
        return ["hurricane", "typhoon", "cyclone", "tropical", "wind", "storm"]
    if p == "flood":
        return ["flood", "inland"]
    if p == "wildfire":
        return ["wildfire", "bushfire", "fire"]
    if p == "fi":
        return ["flood", "inland", "fire"]
    return []


def _prefilter_air_profiles_by_peril(profiles: list[dict], peril: str):
    tokens = _peril_table_tokens(peril)
    if not tokens:
        return profiles, False

    scored = []
    for p in profiles:
        label = f"{p['schema']}.{p['table']}".lower()
        score = sum(1 for t in tokens if t in label)
        if score > 0:
            scored.append((score, p))

    if not scored:
        return profiles, False

    scored.sort(key=lambda x: (-x[0], f"{x[1]['schema']}.{x[1]['table']}"))
    return [p for _, p in scored], True


@st.cache_data(show_spinner=False, ttl=300)
def _infer_model_from_industry(server: str, database: str, peril: str, zone_filter: str):
    peril = (peril or "All").replace("'", "''")
    zone_filter = (zone_filter or "").replace("'", "''").strip()
    peril_pred = "" if peril == "All" else f"AND iu.Peril = '{peril}'"
    zone_pred = "" if not zone_filter else f"AND iu.[Zone] LIKE '%{zone_filter}%'"
    q = f"""
SELECT TOP (1)
       TRY_CONVERT(int, iu.Model) AS ModelNo,
       SUM(iu.Loss) AS TotalLoss
FROM [Industry].[dbo].[Industry_Unadjusted_V21_ZonePercent] iu
WHERE 1=1
  {peril_pred}
  {zone_pred}
GROUP BY TRY_CONVERT(int, iu.Model)
ORDER BY SUM(iu.Loss) DESC;
"""
    try:
        df = run_sql(server, database, q)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    v = pd.to_numeric(df.iloc[0]["ModelNo"], errors="coerce")
    if pd.isna(v):
        return None
    return int(v)


def _match_table_by_model(labels: list[str], model_no: int | None):
    if not model_no or not labels:
        return None
    lower_labels = [x.lower() for x in labels]
    patterns = [
        rf"\btblmodel0*{int(model_no)}\b",
        rf"\bmodel[_\- ]?0*{int(model_no)}\b",
    ]
    for pattern in patterns:
        for i, lbl in enumerate(lower_labels):
            if re.search(pattern, lbl):
                return labels[i]
    return None


def _extract_query_keywords(text: str):
    q = (text or "").lower()
    toks = re.findall(r"[a-z0-9]+", q)
    out = []
    for t in toks:
        if t in _QUERY_STOPWORDS:
            continue
        if t.isdigit():
            continue
        if len(t) >= 3 or t in _STATE_TOKENS or t == "us":
            out.append(t)
    # preserve order, drop duplicates
    seen = set()
    uniq = []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


def _infer_table_by_keyword_match(server: str, database: str, profiles: list[dict], peril: str, zone_filter: str, scenario_text: str):
    if not profiles:
        return None
    keywords = _extract_query_keywords(scenario_text)
    if not keywords:
        return None

    # Keep SQL practical and specific.
    keywords = keywords[:6]
    peril_sql = (peril or "All").replace("'", "''")
    zone_sql = (zone_filter or "").replace("'", "''").strip()
    peril_pred = "" if peril_sql == "All" else f"AND iu.Peril = '{peril_sql}'"
    zone_pred = "" if not zone_sql else f"AND iu.[Zone] LIKE '%{zone_sql}%'"

    best_label = None
    best_score = -1

    for p in profiles:
        if not p.get("desc_col"):
            continue
        schema = p["schema"]
        table = p["table"]
        eid = p["event_id_col"]
        dcol = p["desc_col"]

        token_preds = []
        for kw in keywords:
            kw_sql = kw.replace("'", "''")
            token_preds.append(f"AND LOWER(CAST(a.[{dcol}] AS nvarchar(4000))) LIKE '%{kw_sql}%'")

        q = f"""
SELECT COUNT_BIG(*) AS Cnt
FROM [{AIR_EVENTS_DB}].[{schema}].[{table}] a
JOIN [Industry].[dbo].[Industry_Unadjusted_V21_ZonePercent] iu
  ON iu.EventID = TRY_CONVERT(bigint, a.[{eid}])
WHERE a.[{dcol}] IS NOT NULL
  {peril_pred}
  {zone_pred}
  {' '.join(token_preds)};
"""
        try:
            df = run_sql(server, database, q)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        cnt = pd.to_numeric(df.iloc[0]["Cnt"], errors="coerce")
        score = int(cnt) if pd.notna(cnt) else 0
        if score > best_score:
            best_score = score
            best_label = f"{schema}.{table}"

    return best_label if best_score > 0 else None


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

        profiles.append(
            {
                "schema": str(schema),
                "table": str(table),
                "event_id_col": event_id_col,
                "desc_col": _pick_col(col_map, ["eventdescription", "eventdesc", "description", "desc", "name"]),
                "mag_col": _pick_col(col_map, ["magnitude", "mag", "maxmagnitude", "intensity"]),
                "loc_col": _pick_col(col_map, ["location", "region", "zone", "country", "state", "city"]),
            }
        )
    return profiles


def _fetch_air_event_details(server: str, database: str, event_ids: list[int], profile: dict):
    if not event_ids or not profile:
        return pd.DataFrame()

    schema = profile["schema"]
    table = profile["table"]
    event_id_col = profile["event_id_col"]
    ids_csv = ", ".join(str(int(v)) for v in sorted(set(event_ids)))

    select_cols = [f"TRY_CONVERT(bigint, [{event_id_col}]) AS EventID"]
    if profile.get("desc_col"):
        select_cols.append(f"CAST([{profile['desc_col']}] AS nvarchar(4000)) AS AIR_Description")
    if profile.get("mag_col"):
        select_cols.append(f"TRY_CONVERT(float, [{profile['mag_col']}]) AS AIR_Magnitude")
    if profile.get("loc_col"):
        select_cols.append(f"CAST([{profile['loc_col']}] AS nvarchar(4000)) AS AIR_Location")

    q = f"""
SELECT DISTINCT {", ".join(select_cols)}
FROM [{AIR_EVENTS_DB}].[{schema}].[{table}]
WHERE TRY_CONVERT(bigint, [{event_id_col}]) IN ({ids_csv});
"""
    try:
        df = run_sql(server, database, q)
    except Exception:
        return pd.DataFrame()
    return df if df is not None else pd.DataFrame()


@st.cache_data(show_spinner=False, ttl=300)
def _fetch_air_descriptions_for_peril(
    server: str,
    database: str,
    profile: dict,
    peril: str,
    zone_filter: str = "",
    contains_text: str = "",
    limit: int = 500,
):
    if not profile or not profile.get("desc_col"):
        return []

    schema = profile["schema"]
    table = profile["table"]
    event_id_col = profile["event_id_col"]
    desc_col = profile["desc_col"]

    peril = (peril or "All").replace("'", "''")
    zone_filter = (zone_filter or "").replace("'", "''").strip()
    contains_text = (contains_text or "").replace("'", "''").strip()

    peril_pred = "" if peril == "All" else f"AND iu.Peril = '{peril}'"
    zone_pred = "" if not zone_filter else f"AND iu.[Zone] LIKE '%{zone_filter}%'"
    text_pred = "" if not contains_text else f"AND CAST(a.[{desc_col}] AS nvarchar(4000)) LIKE '%{contains_text}%'"

    q = f"""
SELECT TOP ({int(limit)})
       CAST(a.[{desc_col}] AS nvarchar(4000)) AS EventDescription,
       COUNT_BIG(*) AS Cnt
FROM [{AIR_EVENTS_DB}].[{schema}].[{table}] a
JOIN [Industry].[dbo].[Industry_Unadjusted_V21_ZonePercent] iu
  ON iu.EventID = TRY_CONVERT(bigint, a.[{event_id_col}])
WHERE a.[{desc_col}] IS NOT NULL
  AND LTRIM(RTRIM(CAST(a.[{desc_col}] AS nvarchar(4000)))) <> ''
  {peril_pred}
  {zone_pred}
  {text_pred}
GROUP BY CAST(a.[{desc_col}] AS nvarchar(4000))
ORDER BY Cnt DESC, EventDescription;
"""

    try:
        df = run_sql(server, database, q)
    except Exception:
        return []
    if df is None or df.empty:
        return []
    return [str(v) for v in df["EventDescription"].dropna().tolist()]


def _build_event_search_sql(db, zone_filter, ind_lo, ind_hi, peril, filter_mode="Industry Loss", event_keyword=""):
    lo = int(ind_lo * 1_000_000_000)
    hi = int(ind_hi * 1_000_000_000)
    zone_like = (zone_filter.strip() or "Zone").split()[0].replace("'", "''")
    event_keyword = (event_keyword or "").strip().replace("'", "''")
    peril_clause = f"  AND iu.Peril = '{peril}'" if peril and peril != "All" else ""
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


def _build_output_sql(db, low_id, med_id, high_id):
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


def _render_copy_button(df: pd.DataFrame, label: str, key: str):
        if df is None or df.empty:
                return
        payload = df.to_csv(index=False, sep="\t")
        js_text = json.dumps(payload)
        btn_id = f"copy_btn_{key}"
        html = f"""
<div style=\"margin: 0.15rem 0 0.5rem 0;\">
    <button id=\"{btn_id}\" style=\"
            background:#235CF4;color:#fff;border:none;border-radius:6px;
            padding:6px 10px;cursor:pointer;font-size:12px;\">
        {label}
    </button>
    <span id=\"{btn_id}_msg\" style=\"margin-left:8px;color:#2e7d32;font-size:12px;\"></span>
</div>
<script>
    const btn = document.getElementById('{btn_id}');
    const msg = document.getElementById('{btn_id}_msg');
    if (btn) {{
        btn.addEventListener('click', async () => {{
            try {{
                await navigator.clipboard.writeText({js_text});
                if (msg) msg.textContent = 'Copied';
                setTimeout(() => {{ if (msg) msg.textContent = ''; }}, 1500);
            }} catch (e) {{
                if (msg) msg.textContent = 'Clipboard blocked';
            }}
        }});
    }}
</script>
"""
        components.html(html, height=38)


def _plain_int_str(v):
    if pd.isna(v):
        return ""
    try:
        return str(int(float(v)))
    except Exception:
        return str(v).replace(",", "")


def _format_pct_series(values: pd.Series) -> pd.Series:
    vals = pd.to_numeric(values, errors="coerce")
    non_na = vals.dropna()
    if not non_na.empty and (non_na.abs() <= 1.0).all():
        vals = vals * 100.0
    return vals.map(lambda x: "" if pd.isna(x) else f"{x:.1f}%")


DB = st.session_state.sql_database
st.title("📋 Event Response")
st.caption(f"🗄️ Active CatAccum database: **{DB}**")

# keyed widget defaults (avoid passing both `value` and session_state values)
if "er_loss_range" not in st.session_state:
    st.session_state["er_loss_range"] = (0.0, 300.0)
if "er_mag_range" not in st.session_state:
    st.session_state["er_mag_range"] = (0.0, 12.0)
if "er_event_keyword" not in st.session_state:
    st.session_state["er_event_keyword"] = ""
if "er_filter_mode" not in st.session_state:
    st.session_state["er_filter_mode"] = "Both"

st.markdown("### Scenario Query")
scenario_query = st.text_area("Describe the event", key="er_scenario_query", height=90)
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
    if parsed["mag_lo"] is not None and parsed["mag_hi"] is not None:
        st.session_state["er_mag_range"] = (float(parsed["mag_lo"]), float(parsed["mag_hi"]))
    if parsed.get("model_no") is not None:
        st.session_state["er_model_hint"] = int(parsed["model_no"])
        st.session_state["er_model_hint_manual"] = True
    else:
        st.session_state.pop("er_model_hint", None)
        st.session_state["er_model_hint_manual"] = False
    st.success("Filters updated from scenario query.")

st.divider()
st.markdown("### Event Details")
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.text_input("Event Name", placeholder="e.g. Winter Storm Fern")
with m2:
    st.selectbox("Event Region", ["North America", "Caribbean", "South America", "Europe", "Asia Pacific", "Middle East / Africa"])
with m3:
    st.date_input("Date Created", value=date.today())
with m4:
    st.date_input("Data As-Of Date", value=date.today())

st.divider()
st.markdown("### Find Events")
filter_mode = st.radio("Filter Mode", ["Industry Loss", "Event Characteristics", "Both"], horizontal=True, key="er_filter_mode")

f1, f2, f3 = st.columns(3)
with f1:
    peril = st.selectbox("Peril", ["All", "EQ", "Wind", "Flood", "Wildfire", "FI"], key="er_peril")
with f2:
    zone_filter = st.text_input("Zone (partial match)", key="er_zone", placeholder="e.g. US  Zone 08")
with f3:
    ind_lo, ind_hi = st.slider("Industry Loss Range ($B)", 0.0, 300.0, step=0.5, key="er_loss_range")

event_keyword = ""
use_air_events = False
air_table_profiles = []
air_table_label = None
mag_lo, mag_hi = 0.0, 12.0
desc_search_text = ""

if filter_mode in ("Event Characteristics", "Both"):
    c1, c2 = st.columns(2)
    with c1:
        event_keyword = st.text_input("Event Description keyword", key="er_event_keyword")
    with c2:
        mag_lo, mag_hi = st.slider("Magnitude Range", 0.0, 12.0, step=0.1, key="er_mag_range")
        use_air_events = st.checkbox("Use AIREvents2025_TS13", value=True, key="er_use_air")

    if use_air_events:
        SRV = st.session_state.sql_server
        all_profiles = _discover_air_event_tables(SRV, DB)
        air_table_profiles, was_prefiltered = _prefilter_air_profiles_by_peril(all_profiles, peril)
        if air_table_profiles:
            if was_prefiltered:
                st.caption(f"AIREvents tables prefiltered for peril: {peril}")

            model_hint = st.session_state.get("er_model_hint") if st.session_state.get("er_model_hint_manual", False) else None
            if not model_hint:
                inferred = _infer_model_from_industry(SRV, DB, peril, zone_filter)
                if inferred:
                    model_hint = int(inferred)
                    st.session_state["er_model_hint"] = model_hint
                    st.session_state["er_model_hint_manual"] = False

            labels = [f"{p['schema']}.{p['table']}" for p in air_table_profiles]
            auto_label = None
            if not st.session_state.get("er_model_hint_manual", False):
                keyword_label = _infer_table_by_keyword_match(SRV, DB, air_table_profiles, peril, zone_filter, scenario_query)
                if keyword_label:
                    auto_label = keyword_label
                    st.caption(f"Auto-selected table from scenario text: {keyword_label}")

            if not auto_label:
                best_model_label = _match_table_by_model(labels, model_hint)
                if best_model_label:
                    auto_label = best_model_label
                    st.caption(f"Auto-selected table for model {model_hint}: {best_model_label}")

            if auto_label:
                st.session_state["er_air_table"] = auto_label
            elif st.session_state.get("er_air_table") not in labels:
                st.session_state["er_air_table"] = labels[0]
            air_table_label = st.selectbox("AIREvents table", labels, key="er_air_table")

            profile = next((p for p in air_table_profiles if f"{p['schema']}.{p['table']}" == air_table_label), None)
            if profile and profile.get("desc_col"):
                desc_search_text = st.text_input(
                    "Description contains (optional)",
                    value=st.session_state.get("er_desc_search", ""),
                    key="er_desc_search",
                    placeholder="Type to narrow description options",
                )
                desc_options = _fetch_air_descriptions_for_peril(
                    st.session_state.sql_server,
                    DB,
                    profile,
                    peril,
                    zone_filter,
                    desc_search_text,
                    500,
                )
                if desc_options:
                    picked_desc = st.selectbox(
                        "Description (from selected peril)",
                        ["(none)"] + desc_options,
                        key="er_desc_pick",
                    )
                    if picked_desc != "(none)":
                        event_keyword = picked_desc
                        st.session_state["er_event_keyword"] = picked_desc
                else:
                    st.info("No description options found for the selected peril/zone/table.")

with st.expander("🔍 View generated event-search SQL"):
    st.code(_build_event_search_sql(DB, zone_filter, ind_lo, ind_hi, peril, filter_mode, event_keyword), language="sql")

if st.button("Find Candidate Events", type="primary"):
    with st.spinner("Querying CatAccum…"):
        SRV = st.session_state.sql_server
        try:
            df_raw = run_sql(SRV, DB, _build_event_search_sql(DB, zone_filter, ind_lo, ind_hi, peril, filter_mode, "" if use_air_events else event_keyword))

            if filter_mode in ("Event Characteristics", "Both") and use_air_events and air_table_profiles and air_table_label and df_raw is not None and not df_raw.empty:
                profile = next((p for p in air_table_profiles if f"{p['schema']}.{p['table']}" == air_table_label), None)
                if profile:
                    air_df = _fetch_air_event_details(SRV, DB, [int(v) for v in df_raw["EventID"].dropna().tolist()], profile)
                    if air_df is not None and not air_df.empty:
                        df_raw = df_raw.merge(air_df, on="EventID", how="left")
                        if event_keyword and "AIR_Description" in df_raw.columns:
                            df_raw = df_raw[df_raw["AIR_Description"].astype(str).str.contains(event_keyword, case=False, na=False)]
                        mag_filter_is_set = not (float(mag_lo) <= 0.0 and float(mag_hi) >= 12.0)
                        if "AIR_Magnitude" in df_raw.columns and mag_filter_is_set:
                            mag_vals = pd.to_numeric(df_raw["AIR_Magnitude"], errors="coerce")
                            df_raw = df_raw[(mag_vals >= float(mag_lo)) & (mag_vals <= float(mag_hi))]

            if df_raw is not None and not df_raw.empty:
                df_raw.insert(0, "✓", False)
                st.session_state["candidates"] = df_raw
            else:
                st.warning("No events found matching those filters.")
                st.session_state.pop("candidates", None)
        except Exception as exc:
            st.error(f"Query failed: {exc}")
            st.session_state.pop("candidates", None)

if "candidates" in st.session_state:
    st.markdown("### Candidate Events")
    cand = st.session_state["candidates"].copy()
    if "EventID" in cand.columns:
        cand["EventID"] = cand["EventID"].map(_plain_int_str)
    col_cfg = {"✓": st.column_config.CheckboxColumn()}
    if "Industry Loss ($B)" in cand.columns:
        col_cfg["Industry Loss ($B)"] = st.column_config.NumberColumn(format="$%.2fB")
    edited = st.data_editor(cand, use_container_width=True, hide_index=True, num_rows="fixed", column_config=col_cfg)
    st.session_state["candidates"] = edited

    shortlist = edited[edited["✓"]] if edited["✓"].any() else edited
    selected_ids = ["(none)"] + [str(int(v)) for v in shortlist["EventID"].tolist()]
    ranked = shortlist.sort_values("Industry Loss ($B)", ascending=True) if "Industry Loss ($B)" in shortlist.columns else shortlist.sort_values("EventID", ascending=True)
    ranked_ids = [str(int(v)) for v in ranked["EventID"].tolist()] if len(ranked) else []

    if st.session_state.get("low_pick") not in selected_ids:
        st.session_state["low_pick"] = ranked_ids[0] if ranked_ids else "(none)"
    if st.session_state.get("med_pick") not in selected_ids:
        st.session_state["med_pick"] = ranked_ids[len(ranked_ids) // 2] if ranked_ids else "(none)"
    if st.session_state.get("high_pick") not in selected_ids:
        st.session_state["high_pick"] = ranked_ids[-1] if ranked_ids else "(none)"

    st.markdown("### Assign Scenarios")
    s1, s2, s3 = st.columns(3)
    with s1:
        low_pick = st.selectbox("Low", selected_ids, key="low_pick")
        low_id = int(low_pick) if low_pick != "(none)" else int(st.number_input("Low EventID", min_value=0, value=0, step=1, key="low_id_manual"))
    with s2:
        med_pick = st.selectbox("Med", selected_ids, key="med_pick")
        med_id = int(med_pick) if med_pick != "(none)" else int(st.number_input("Med EventID", min_value=0, value=0, step=1, key="med_id_manual"))
    with s3:
        high_pick = st.selectbox("High", selected_ids, key="high_pick")
        high_id = int(high_pick) if high_pick != "(none)" else int(st.number_input("High EventID", min_value=0, value=0, step=1, key="high_id_manual"))

    with st.expander("🔍 View generated output SQL"):
        st.code(_build_output_sql(DB, low_id, med_id, high_id), language="sql")

    if st.button("▶ Run & Populate Template", type="primary", use_container_width=True):
        SRV = st.session_state.sql_server
        try:
            df_out = run_sql(SRV, DB, _build_output_sql(DB, low_id, med_id, high_id))
            if df_out is not None and not df_out.empty:
                summary_df = (
                    df_out.groupby("Scenario", dropna=False)
                    .agg(
                        impacted_contracts=("Contract #", "nunique"),
                        industry_loss_b=("Industry Loss ($B)", "max"),
                        gross_loss_m=("Gross Loss $M", "sum"),
                    )
                    .reset_index()
                )
                # Market Share % = Everest Gross Loss / Industry Loss
                # Units: Gross is in $M, Industry is in $B => convert denominator by *1000
                summary_df["marketshare_pct"] = (
                    summary_df["gross_loss_m"]
                    / (summary_df["industry_loss_b"] * 1000.0)
                ) * 100.0
                summary_df["marketshare_pct"] = summary_df["marketshare_pct"].where(
                    summary_df["industry_loss_b"] > 0,
                    0.0,
                )
                summary_df = summary_df.rename(
                    columns={
                        "Scenario": "Scenario",
                        "impacted_contracts": "Impacted Contracts",
                        "industry_loss_b": "Industry Loss ($B)",
                        "gross_loss_m": "Gross Loss $M",
                        "marketshare_pct": "Market Share %",
                    }
                )
                _scenario_order = pd.CategoricalDtype(categories=["Low", "Med", "High"], ordered=True)
                summary_df["Scenario"] = summary_df["Scenario"].astype(_scenario_order)
                summary_df = summary_df.sort_values("Scenario").reset_index(drop=True)
                if "Market Share %" in summary_df.columns:
                    summary_df["Market Share %"] = _format_pct_series(summary_df["Market Share %"])
                st.markdown("#### Event Summary")
                _render_copy_button(summary_df, "Copy Event Summary (TSV)", "summary")
                st.dataframe(summary_df, use_container_width=True, hide_index=True)

                loss_by_contract = (
                    df_out.pivot_table(
                        index=[
                            "layerkey",
                            "Department",
                            "Company",
                            "SubType",
                            "Contract #",
                            "Terms",
                            "100% Limit ($)",
                            "ROL",
                            "Share",
                        ],
                        columns="Scenario",
                        values="Gross Loss $M",
                        aggfunc="sum",
                        fill_value=0.0,
                    )
                    .reset_index()
                )
                for sc in ["Low", "Med", "High"]:
                    if sc not in loss_by_contract.columns:
                        loss_by_contract[sc] = 0.0

                loss_by_contract = loss_by_contract.rename(
                    columns={
                        "layerkey": "Layerkey",
                        "SubType": "Subtype",
                        "Contract #": "Contract",
                        "100% Limit ($)": "Everest Limit",
                        "Low": "Low Gross Loss $M",
                        "Med": "Med Gross Loss $M",
                        "High": "High Gross Loss $M",
                    }
                )

                ordered_cols = [
                    "Layerkey",
                    "Department",
                    "Company",
                    "Subtype",
                    "Contract",
                    "Terms",
                    "Everest Limit",
                    "ROL",
                    "Share",
                    "Low Gross Loss $M",
                    "Med Gross Loss $M",
                    "High Gross Loss $M",
                ]
                loss_by_contract = loss_by_contract[[c for c in ordered_cols if c in loss_by_contract.columns]]
                if "Layerkey" in loss_by_contract.columns:
                    loss_by_contract["Layerkey"] = loss_by_contract["Layerkey"].map(_plain_int_str)
                if "Share" in loss_by_contract.columns:
                    loss_by_contract["Share"] = _format_pct_series(loss_by_contract["Share"])

                df_out_fmt = df_out.copy()
                if "layerkey" in df_out_fmt.columns:
                    df_out_fmt["layerkey"] = df_out_fmt["layerkey"].map(_plain_int_str)
                if "Share" in df_out_fmt.columns:
                    df_out_fmt["Share"] = _format_pct_series(df_out_fmt["Share"])

                st.markdown("#### Loss by Contract (Low / Med / High)")
                _render_copy_button(loss_by_contract, "Copy Loss by Contract (TSV)", "contract")
                st.dataframe(loss_by_contract, use_container_width=True, hide_index=True)
                _render_copy_button(df_out_fmt, "Copy Full Output (TSV)", "fullout")
                st.session_state["waterfall_df"] = df_out_fmt
            else:
                st.warning("Query returned no rows for these event IDs.")
        except Exception as exc:
            st.error(f"Waterfall query failed: {exc}")
else:
    st.info("Set filters and click **Find Candidate Events** to begin.")
