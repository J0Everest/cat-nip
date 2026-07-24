import pandas as pd
import plotly.express as px
import streamlit as st
import os
import re
from _db import init_db_state, run_sql
# ── Official Everest brand colours (Brand Guide Oct 2024, p.16) ──────
EVEREST_BLUE   = "#235CF4"   # Everest Blue  – primary brand colour
MID_BLUE       = "#0A3699"   # Mid Blue
DARK_BLUE      = "#061C49"   # Dark Blue
MID_GRAY       = "#A4ABC8"   # Mid Gray
LIGHT_GRAY     = "#F5F5F5"   # Light Gray
# Secondary – data viz only
DARK_PURPLE    = "#6929C4"
LIGHT_PURPLE   = "#A56EFF"
DARK_TEAL      = "#075D5D"
LIGHT_TEAL     = "#119D9A"
# Aliases kept for CSS blocks below
EVEREST_BLUE2  = MID_BLUE
EVEREST_ICE    = LIGHT_GRAY

# ── Shared DB state (set from app sidebar) ────────────────────────────────────
init_db_state()
sql_server = st.session_state.sql_server
sql_database = st.session_state.sql_database


def _run_sql(server: str, database: str, query: str, params=()):
    return run_sql(server, database, query, params)


def _parse_question_filters(question: str):
    """Return (peril_db_value, region_partial) matching the real DB values."""
    q = str(question or "").strip().lower()
    if not q:
        return None, None

    tokens = re.split(r"[^a-z0-9]+", q)

    # Peril: match against known aliases
    peril = None
    for token in tokens:
        if token in PERIL_ALIASES:
            peril = PERIL_ALIASES[token]
            break

    # Region: try multi-word phrases first, then single tokens
    region = None
    q_stripped = q.strip()
    for phrase, mapped in REGION_TOKENS.items():
        if phrase in q_stripped:
            region = mapped
            break
    if not region:
        for token in tokens:
            if token in REGION_TOKENS:
                region = REGION_TOKENS[token]
                break
    if not region and len(q_stripped) >= 3:
        # Raw fallback — let SQL do a LIKE search on whatever was typed
        region = q_stripped

    return peril, region


# Actual peril codes from dbo.All_Loss: EQ, Wind, Flood, Wildfire, MPCI, CROP
PERIL_ALIASES = {
    # Earthquake
    "eq":            "EQ",
    "earthquake":    "EQ",
    "quake":         "EQ",
    "seismic":       "EQ",
    # Wind / Hurricane / Typhoon
    "wind":          "Wind",
    "windstorm":     "Wind",
    "hurricane":     "Wind",
    "typhoon":       "Wind",
    "tropical":      "Wind",
    "cyclone":       "Wind",
    "ht":            "Wind",
    "hu":            "Wind",
    "wt":            "Wind",
    "ty":            "Wind",
    # Flood
    "flood":         "Flood",
    "flooding":      "Flood",
    "surge":         "Flood",
    # Wildfire
    "wildfire":      "Wildfire",
    "fire":          "Wildfire",
    "wf":            "Wildfire",
    # Crop / MPCI
    "crop":          "CROP",
    "mpci":          "MPCI",
    "agriculture":   "CROP",
}

# All actual zones from dbo.All_Loss mapped to (lat, lon)
ZONE_GEO = {
    # US Zones
    "US  Zone 01":                              (35.0,  -97.0),
    "US  Zone 02":                              (36.5,  -94.0),
    "US  Zone 03 FL":                           (28.0,  -81.8),
    "US  Zone 03 GA SC":                        (33.0,  -82.0),
    "US  Zone 03 NC":                           (35.5,  -79.0),
    "US  Zone 03 Gulf":                         (29.5,  -89.5),
    "US  Zone 04":                              (37.5,  -99.0),
    "US  Zone 05 and 06":                       (41.0,  -88.0),
    "US  Zone 07":                              (34.0, -118.0),
    "US  Zone 08":                              (40.0, -105.0),
    "US  Zone 09":                              (38.5, -120.5),
    "US  Zone 10":                              (47.5, -122.0),
    "US  SCS":                                  (38.0,  -97.0),
    "US  WF":                                   (39.0, -120.0),
    "US  WT":                                   (38.0,  -97.0),
    "US":                                       (38.0,  -97.0),
    "US & Canada  EQ":                          (45.0, -100.0),
    "North America  HU":                        (25.0,  -80.0),
    # Canada
    "Canada  AB":                               (53.9, -116.6),
    "Canada  BC":                               (53.7, -127.6),
    "Canada  MB":                               (53.8,  -98.8),
    "Canada  NB":                               (46.5,  -66.5),
    "Canada  NF":                               (53.0,  -56.0),
    "Canada  NL":                               (53.0,  -60.0),
    "Canada  NS":                               (45.0,  -63.0),
    "Canada  NT":                               (64.3, -119.2),
    "Canada  NU":                               (70.3,  -84.0),
    "Canada  ON":                               (51.3,  -85.3),
    "Canada  PE":                               (46.3,  -63.1),
    "Canada  QC":                               (53.0,  -70.0),
    "Canada  SK":                               (54.0, -106.0),
    "Canada  YT":                               (64.0, -135.0),
    "Canada  SCS":                              (50.0, -104.0),
    "Canada  HU":                               (45.0,  -63.0),
    "Canada  WT":                               (51.0, -100.0),
    "Canada":                                   (56.0, -106.0),
    # Caribbean
    "Caribbean  Anguilla":                      (18.2,  -63.1),
    "Caribbean  Antigua and Barbuda":           (17.1,  -61.8),
    "Caribbean  Aruba":                         (12.5,  -70.0),
    "Caribbean  Bahamas":                       (25.0,  -78.0),
    "Caribbean  Barbados":                      (13.2,  -59.5),
    "Caribbean  Bermuda":                       (32.3,  -64.8),
    "Caribbean  Bonaire and Sint Eustatius and Saba": (12.2, -68.3),
    "Caribbean  British Virgin Islands":        (18.4,  -64.6),
    "Caribbean  Cayman Islands":                (19.3,  -81.4),
    "Caribbean  Cuba":                          (22.0,  -80.0),
    "Caribbean  Curacao":                       (12.2,  -69.0),
    "Caribbean  Dominica":                      (15.4,  -61.4),
    "Caribbean  Dominican Republic":            (19.0,  -70.7),
    "Caribbean  Grenada":                       (12.1,  -61.7),
    "Caribbean  Guadeloupe":                    (16.3,  -61.6),
    "Caribbean  Haiti":                         (19.0,  -72.3),
    "Caribbean  Jamaica":                       (18.2,  -77.3),
    "Caribbean  Martinique":                    (14.6,  -61.0),
    "Caribbean  Montserrat":                    (16.7,  -62.2),
    "Caribbean  Puerto Rico":                   (18.2,  -66.6),
    "Caribbean  St. Barts":                     (17.9,  -62.8),
    "Caribbean  St. Kitts and Nevis":           (17.3,  -62.7),
    "Caribbean  St. Lucia":                     (13.9,  -60.9),
    "Caribbean  St. Maarten":                   (18.1,  -63.1),
    "Caribbean  St. Martin":                    (18.1,  -63.1),
    "Caribbean  St. Vincent and the Grenadines": (13.3, -61.2),
    "Caribbean  Trinidad and Tobago":           (10.7,  -61.2),
    "Caribbean  Turks and Caicos Islands":      (21.7,  -71.8),
    "Caribbean  Virgin Islands":                (18.3,  -64.9),
    "Caribbean  EQ":                            (18.0,  -67.0),
    # Central America
    "Central America  Belize":                  (17.2,  -88.5),
    "Central America  Costa Rica":              ( 9.7,  -83.8),
    "Central America  El Salvador":             (13.8,  -88.9),
    "Central America  Guatemala":               (15.8,  -90.2),
    "Central America  Honduras":                (15.2,  -86.2),
    "Central America  Mexico":                  (23.6,  -102.5),
    "Central America  Nicaragua":               (12.9,  -85.2),
    "Central America  Panama":                  ( 8.5,  -80.8),
    # South America
    "South America  Chile":                     (-33.5, -70.7),
    "South America  Colombia":                  (  4.6, -74.1),
    "South America  Ecuador":                   ( -1.8, -78.2),
    "South America  Peru":                      (-12.0, -77.0),
    "South America  Venezuela":                 (  8.0, -66.0),
    "South America  EQ":                        (-20.0, -65.0),
    # Europe
    "Europe  Albania":                          (41.3,  20.2),
    "Europe  Austria":                          (47.8,  13.0),
    "Europe  Belgium":                          (50.9,   4.5),
    "Europe  Bulgaria":                         (42.7,  25.5),
    "Europe  Cyprus":                           (35.1,  33.4),
    "Europe  Czech Republic":                   (49.8,  15.5),
    "Europe  Denmark":                          (56.3,   9.5),
    "Europe  EQ":                               (46.0,  14.0),
    "Europe  Estonia":                          (58.6,  25.0),
    "Europe  Finland":                          (64.0,  26.0),
    "Europe  France":                           (46.6,   2.4),
    "Europe  Germany":                          (51.2,  10.5),
    "Europe  Greece":                           (39.1,  22.0),
    "Europe  Hungary":                          (47.2,  19.4),
    "Europe  Ireland":                          (53.4,  -8.2),
    "Europe  Italy":                            (41.9,  12.6),
    "Europe  Latvia":                           (57.0,  25.0),
    "Europe  Liechtenstein":                    (47.2,   9.5),
    "Europe  Lithuania":                        (55.7,  23.9),
    "Europe  Luxembourg":                       (49.8,   6.1),
    "Europe  Macedonia":                        (41.6,  21.7),
    "Europe  Netherlands":                      (52.1,   5.3),
    "Europe  Norway":                           (60.5,   8.5),
    "Europe  Poland":                           (52.1,  19.1),
    "Europe  Portugal":                         (39.4,  -8.2),
    "Europe  Romania":                          (45.9,  24.9),
    "Europe  SCS":                              (50.0,  10.0),
    "Europe  Serbia":                           (44.0,  21.0),
    "Europe  Slovakia":                         (48.7,  19.7),
    "Europe  Slovenia":                         (46.2,  14.8),
    "Europe  Sweden":                           (60.1,  18.6),
    "Europe  Switzerland":                      (46.8,   8.2),
    "Europe  UK":                               (54.0,  -2.0),
    "Europe":                                   (50.0,  10.0),
    "Europe (Central)  FL":                     (49.0,  13.0),
    # Asia
    "Asia  Brunei":                             ( 4.5,  114.7),
    "Asia  China":                              (35.9,  104.2),
    "Asia  Fiji":                               (-17.7, 178.1),
    "Asia  Guam":                               (13.4,  144.8),
    "Asia  Hong Kong":                          (22.3,  114.2),
    "Asia  India":                              (20.6,   78.9),
    "Asia  Indonesia":                          (-2.5,  118.0),
    "Asia  Japan":                              (36.2,  138.3),
    "Asia  Macau":                              (22.2,  113.5),
    "Asia  Malaysia":                           ( 3.8,  108.7),
    "Asia  Philippines":                        (13.0,  122.0),
    "Asia  Saipan":                             (15.2,  145.7),
    "Asia  Singapore":                          ( 1.4,  103.8),
    "Asia  South Korea":                        (36.0,  128.0),
    "Asia  Southeast Asia":                     (10.0,  106.0),
    "Asia  Taiwan":                             (23.7,  121.0),
    "Asia  Thailand":                           (15.9,  100.9),
    "Asia  TY":                                 (25.0,  135.0),
    "Asia  Vietnam":                            (14.0,  108.3),
    # Japan
    "Japan  EQ":                                (36.2,  138.3),
    # AusNZ
    "AusNZ  Australia":                         (-25.3, 133.8),
    "AusNZ  New Zealand":                       (-41.3,  174.8),
    # Mid East
    "Mid East  Bahrain":                        (26.0,   50.6),
    "Mid East  Israel":                         (31.5,   34.9),
    "Mid East  Jordan":                         (30.6,   36.0),
    "Mid East  Kuwait":                         (29.5,   47.9),
    "Mid East  Lebanon":                        (33.9,   35.9),
    "Mid East  Oman":                           (21.5,   57.0),
    "Mid East  Qatar":                          (25.4,   51.2),
    "Mid East  Saudi Arabia":                   (24.7,   46.7),
    "Mid East  Turkey":                         (39.0,   35.0),
    "Mid East  UAE":                            (24.5,   54.4),
    "Mid East  United Arab Emirates":           (24.5,   54.4),
    # Africa
    "Africa  South Africa":                     (-29.0,  25.0),
    # SE Asia
    "SE Asia  EQ":                              ( 5.0,  110.0),
    # Water
    "Water  Gulf of Mexico":                    (25.0,  -90.0),
    # Global / Unmapped
    "Global":                                   (20.0,    0.0),
    "Unmapped Zone":                            ( 0.0,    0.0),
}


def _zone_to_geo(zone: str):
    if not zone:
        return None
    z = str(zone).strip()
    if z in ZONE_GEO:
        return ZONE_GEO[z]
    # Fallback: try trimmed variants
    for key in ZONE_GEO:
        if key.lower().strip() == z.lower():
            return ZONE_GEO[key]
    return None


REGION_TOKENS = {
    # Countries / subregions → words that appear in zone strings
    "venezuela":       "Venezuela",
    "venezuelan":      "Venezuela",
    "florida":         "FL",
    "fl":              "FL",
    "gulf":            "Gulf",
    "puerto rico":     "Puerto Rico",
    "california":      "Zone 09",
    "texas":           "Zone 03 Gulf",
    "japan":           "Japan",
    "australia":       "Australia",
    "new zealand":     "New Zealand",
    "uk":              "UK",
    "turkey":          "Turkey",
    "chile":           "Chile",
    "colombia":        "Colombia",
    "peru":            "Peru",
    "ecuador":         "Ecuador",
    "china":           "China",
    "india":           "India",
    "indonesia":       "Indonesia",
    "philippines":     "Philippines",
    "taiwan":          "Taiwan",
    "italy":           "Italy",
    "france":          "France",
    "germany":         "Germany",
    "greece":          "Greece",
    "mexico":          "Mexico",
    "canada":          "Canada",
}


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_kpis(server: str, database: str):
    q = """
      SELECT
        SUM(GrossAAL) / 1e6                          AS total_gross_aal_m,
        SUM(NetofRIPAAL) / 1e6                       AS total_net_aal_m,
        SUM(GrossAAL - ISNULL(NetofRIPAAL, 0)) / 1e6 AS total_ceded_m,
        COUNT(DISTINCT layerkey)                     AS contract_count
      FROM dbo.All_Contract_AAL WITH (NOLOCK)
    """
    try:
        df = _run_sql(server, database, q)
        return (df.iloc[0].to_dict() if len(df) else {}), True
    except Exception as e:
        return {"error": str(e)}, False


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_exposure_map(server: str, database: str,
                        peril_filter: str = None, region_filter: str = None):
    where_extra = ""
    params = []
    if peril_filter:
        where_extra += " AND peril = ?"
        params.append(peril_filter)
    if region_filter:
        where_extra += " AND zone LIKE '%' + ? + '%'"
        params.append(region_filter)

    filtered = bool(peril_filter or region_filter)

    # Unfiltered global view: TABLESAMPLE for near-instant results (~1-2s)
    # Filtered view: full precise query on the smaller table, fallback to All_Loss
    if not filtered:
        q = """
          SELECT TOP 200
            peril,
            zone,
            COUNT(DISTINCT layerkey)                                AS contract_count,
            SUM(grloss) / NULLIF(COUNT(DISTINCT [year]), 0) / 1e6  AS avg_annual_loss_m
          FROM dbo.Catapult_Loss_All_NonCorrelating TABLESAMPLE (10 PERCENT) WITH (NOLOCK)
          WHERE grloss > 0
          GROUP BY peril, zone
          ORDER BY SUM(grloss) / NULLIF(COUNT(DISTINCT [year]), 0) DESC
        """
        source = "dbo.Catapult_Loss_All_NonCorrelating (10% sample)"
        tables = [(q, None, source)]
    else:
        q_filtered = f"""
          SELECT TOP 500
            peril,
            zone,
            COUNT(DISTINCT layerkey)                                AS contract_count,
            SUM(grloss) / NULLIF(COUNT(DISTINCT [year]), 0) / 1e6  AS avg_annual_loss_m
          FROM {{table_name}} WITH (NOLOCK)
          WHERE grloss > 0{where_extra}
          GROUP BY peril, zone
          ORDER BY SUM(grloss) / NULLIF(COUNT(DISTINCT [year]), 0) DESC
          OPTION (RECOMPILE)
        """
        tables = [
            (q_filtered.format(table_name="dbo.Catapult_Loss_All_NonCorrelating"),
             params, "dbo.Catapult_Loss_All_NonCorrelating"),
            (q_filtered.format(table_name="dbo.All_Loss"),
             params, "dbo.All_Loss"),
        ]

    def _enrich(df):
        df["geo"] = df["zone"].apply(_zone_to_geo)
        df = df[df["geo"].notna()].copy()
        df["lat"] = df["geo"].apply(lambda x: x[0])
        df["lon"] = df["geo"].apply(lambda x: x[1])
        df.drop(columns=["geo"], inplace=True)
        return df

    try:
        for (q, p, src) in tables:
            df = _run_sql(server, database, q, params=p or None)
            df = _enrich(df)
            if len(df) > 0:
                return {"records": df.to_dict(orient="records"), "source": src}, True
        return {"records": [], "source": "none"}, True
    except Exception as e:
        return {"error": str(e)}, False


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_top_program_scenarios(server: str, database: str,
                                                                 peril_filter: str = None, region_filter: str = None):
        q = """
            WITH filtered AS (
                SELECT
                    COALESCE(ac.Company, ps.Ceding_Company_Name, '(Unknown Company)') AS company_name,
                    COALESCE(
                        ps.Program_Scenario_Name,
                        CONCAT('ProgramScenarioKey ', CAST(l.ProgramScenarioKey AS varchar(20)))
                    ) AS program_scenario,
                    ac.UWS_Contract_Nbr AS uws_contract_nbr,
                    x.[year],
                    x.grloss
                FROM dbo.All_Loss x WITH (NOLOCK)
                JOIN dbo.All_Contract ac WITH (NOLOCK)
                    ON x.layerkey = ac.layerkey
                   AND ac.status_ind = 'B'
                LEFT JOIN dbo.Catapult_Tbl_Layer l WITH (NOLOCK)
                    ON x.layerkey = l.LayerKey
                LEFT JOIN dbo.Catapult_Tbl_Program_Scenario ps WITH (NOLOCK)
                    ON l.ProgramScenarioKey = ps.ProgramScenarioKey
                WHERE x.grloss > 0
                  AND (? IS NULL OR x.peril = ?)
                  AND (? IS NULL OR x.zone LIKE '%' + ? + '%')
            ), agg AS (
                SELECT
                    company_name,
                    program_scenario,
                    SUM(grloss) / NULLIF(COUNT(DISTINCT [year]), 0) / 1e6 AS avg_annual_gross_loss_m
                FROM filtered
                GROUP BY company_name, program_scenario
            )
            SELECT TOP 10
                a.company_name,
                a.program_scenario,
                c.uws_contract_nbrs,
                a.avg_annual_gross_loss_m
            FROM agg a
            OUTER APPLY (
                SELECT STUFF((
                    SELECT DISTINCT ', ' + CAST(f2.uws_contract_nbr AS varchar(64))
                    FROM filtered f2
                    WHERE f2.company_name = a.company_name
                      AND f2.program_scenario = a.program_scenario
                      AND f2.uws_contract_nbr IS NOT NULL
                    FOR XML PATH(''), TYPE
                ).value('.', 'nvarchar(max)'), 1, 2, '') AS uws_contract_nbrs
            ) c
            ORDER BY a.avg_annual_gross_loss_m DESC
            OPTION (RECOMPILE)
        """
        params = [peril_filter, peril_filter, region_filter, region_filter]
        try:
                df = _run_sql(server, database, q, params=params)
                return {
                        "source": "dbo.All_Loss + dbo.All_Contract(status_ind='B')",
                        "rows": df.to_dict(orient="records"),
                }, True
        except Exception as e:
                return {"error": str(e)}, False


@st.cache_data(ttl=180, show_spinner=False)
def _ask_query_sql(server: str, database: str, question: str):
    peril_filter, region_filter = _parse_question_filters(question)

    # peril is an exact DB code (EQ, Wind, Flood, Wildfire, MPCI, CROP)
    # zone is a free-form string so we use LIKE for partial match
    q = """
        SELECT TOP 10
            peril,
            zone,
            COUNT(DISTINCT layerkey)                                AS exposure_count,
            SUM(grloss) / NULLIF(COUNT(DISTINCT [year]), 0) / 1e6  AS avg_annual_loss_m
        FROM {table_name} WITH (NOLOCK)
        WHERE grloss > 0
            AND (? IS NULL OR peril = ?)
            AND (? IS NULL OR zone LIKE '%' + ? + '%')
        GROUP BY peril, zone
        ORDER BY SUM(grloss) / NULLIF(COUNT(DISTINCT [year]), 0) DESC
        OPTION (RECOMPILE)
    """
    try:
        # Fast path first: much smaller table (~89M rows vs multi-billion)
        fast_table = "dbo.Catapult_Loss_All_NonCorrelating"
        fast_df = _run_sql(
            server,
            database,
            q.format(table_name=fast_table),
            params=[peril_filter, peril_filter, region_filter, region_filter],
        )

        if len(fast_df) > 0:
            return {
                "source": fast_table,
                "peril_filter": peril_filter,
                "region_filter": region_filter,
                "rows": fast_df.to_dict(orient="records"),
            }, True

        # Fallback: full loss table
        full_table = "dbo.All_Loss"
        full_df = _run_sql(
            server,
            database,
            q.format(table_name=full_table),
            params=[peril_filter, peril_filter, region_filter, region_filter],
        )

        return {
            "source": full_table,
            "peril_filter": peril_filter,
            "region_filter": region_filter,
            "rows": full_df.to_dict(orient="records"),
        }, True
    except Exception as e:
        return {"error": str(e)}, False

# ── Global CSS: bespoke branded elements only ─────────────────────
# Base theme (light, Everest colours) is enforced via .streamlit/config.toml
st.markdown(
    f"""
    <style>
        /* Font stack: Avenir Next LT Pro is the brand typeface */
        html, body, [class*="css"] {{
            font-family: 'Avenir Next LT Pro', 'Avenir Next', 'Segoe UI', Arial, sans-serif !important;
        }}

        /* Metric cards – Everest blue left accent */
        [data-testid="metric-container"] {{
            border-left: 5px solid {EVEREST_BLUE} !important;
            border-radius: 10px;
        }}

        /* Query response box */
        .query-box {{
            background: #ffffff;
            border: 1px solid #d4dae8;
            border-left: 5px solid {EVEREST_BLUE};
            border-radius: 10px;
            padding: 14px 18px;
            font-size: 0.93rem;
            color: {DARK_BLUE};
            white-space: pre-wrap;
            margin-top: 8px;
            line-height: 1.65;
        }}

        /* Section h2 underline */
        h2 {{
            border-bottom: 3px solid {EVEREST_BLUE};
            padding-bottom: 6px;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ─────────────────────────────────────────────────────────
st.markdown(
    f"<h1 style='margin:0;padding-top:6px;color:{DARK_BLUE};font-weight:700;'>Cat Scenario Explorer</h1>"
    f"<p style='margin:0;color:{MID_GRAY};font-size:0.85rem;'>CatAccum-backed portfolio impact analysis</p>",
    unsafe_allow_html=True,
)

st.divider()

# ── KPI metrics (live from All_Contract_AAL) ─────────────────────────────────
with st.spinner("Loading portfolio KPIs…"):
    _kpi_data, _kpi_live = _fetch_kpis(sql_server, sql_database)

if _kpi_live and _kpi_data and not _kpi_data.get("error"):
    k = _kpi_data
    gross_total = k.get("total_gross_aal_m") or 0
    net_total   = k.get("total_net_aal_m")   or 0
    ceded_total = k.get("total_ceded_m")     or 0
    contracts   = k.get("contract_count")    or 0
    _src_badge  = f"🟢 Live – `dbo.All_Contract_AAL`"
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Gross AAL",    f"${gross_total:,.0f}M")
    k2.metric("Total Net AAL",      f"${net_total:,.0f}M")
    k3.metric("Total Ceded AAL",    f"${ceded_total:,.0f}M")
    k4.metric("Active Contracts",   f"{contracts:,}")
else:
    _src_badge = "🟡 Sample data – SQL connection not available"
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Gross Loss Range",  "$420M – $680M")
    k2.metric("Net Loss Range",    "$180M – $290M")
    k3.metric("Ceded Recovery",    "$190M – $310M")
    k4.metric("Impacted Contracts","143")
st.caption(_src_badge)

st.divider()

# ── Scenario Query panel ──────────────────────────────────────────
st.markdown("## Scenario Query")
st.markdown(
    "Ask how a **peril** in a **region** could impact the portfolio in CatAccum. "
    "This uses local question parsing and SQL filters (not Microsoft Copilot). "
    "_Example: What is the impact of hurricane in Florida?_"
)

with st.form("query_form", clear_on_submit=False):
    question = st.text_input(
        label="Question",
        placeholder="What is the impact of earthquake in California?",
        label_visibility="collapsed",
    )
    submitted = st.form_submit_button("Ask", use_container_width=False)

# Persist active filters across reruns
if "active_peril" not in st.session_state:
    st.session_state.active_peril = None
if "active_region" not in st.session_state:
    st.session_state.active_region = None
if "query_answer" not in st.session_state:
    st.session_state.query_answer = None

if submitted and question.strip():
    data, ok = _ask_query_sql(sql_server, sql_database, question.strip())
    if not ok:
        answer = f"Could not query CatAccum: {data.get('error', 'Unknown SQL error')}"
        st.session_state.active_peril = None
        st.session_state.active_region = None
    else:
        rows = data.get("rows", []) if isinstance(data, dict) else []
        source = data.get("source", "dbo.All_Loss") if isinstance(data, dict) else "dbo.All_Loss"
        pf = data.get("peril_filter") if isinstance(data, dict) else None
        rf = data.get("region_filter") if isinstance(data, dict) else None
        # Store for map + EP curve
        st.session_state.active_peril = pf
        st.session_state.active_region = rf

        lines = [f"Top CatAccum matches for: {question.strip()}"]
        lines.append(f"Source: {source}")
        if pf or rf:
            lines.append(f"Parsed filters → peril: {pf or 'none'}, region: {rf or 'none'}")
        if not rows:
            lines.append("No results found.")
        else:
            for i, item in enumerate(rows, 1):
                lines.append(
                    f"{i}. {item.get('peril', 'N/A')} in {item.get('zone', 'N/A')} | "
                    f"exposures: {int(item.get('exposure_count', 0)):,} | "
                    f"avg annual gross loss: ${float(item.get('avg_annual_loss_m', 0)):.1f}M"
                )
        answer = "\n".join(lines)
    st.session_state.query_answer = answer

if st.session_state.query_answer:
    st.markdown(f'<div class="query-box">{st.session_state.query_answer}</div>', unsafe_allow_html=True)
    if st.session_state.active_peril or st.session_state.active_region:
        if st.button("✕ Clear filter — show full portfolio"):
            st.session_state.active_peril = None
            st.session_state.active_region = None
            st.session_state.query_answer = None
            st.rerun()

st.divider()

# ── Exposure Map (live, filtered by active question) ────────────────────────────
_active_peril  = st.session_state.get("active_peril")
_active_region = st.session_state.get("active_region")

_map_spinner_msg = (
    f"Loading map for {_active_peril or ''} {_active_region or ''}…".strip()
    if (_active_peril or _active_region)
    else "Loading exposure map (sampled)…"
)
with st.spinner(_map_spinner_msg):
    _exp_data, _exp_live = _fetch_exposure_map(sql_server, sql_database,
                                               peril_filter=_active_peril,
                                               region_filter=_active_region)

if _exp_live and _exp_data and not _exp_data.get("error"):
    _exp_records = _exp_data.get("records", [])
    _exp_source  = _exp_data.get("source", "dbo.Catapult_Loss_All_NonCorrelating")
    exposures = pd.DataFrame(_exp_records)
    exposures.rename(columns={"avg_annual_loss_m": "impact_m", "zone": "state",
                               "contract_count": "contracts"}, inplace=True)
    _exp_badge = f"🟢 Live – `{_exp_source}` ({len(exposures)} peril-zone rows)"
else:
    _exp_badge = "🟡 Sample data – SQL connection not available"
    exposures = pd.DataFrame([
        {"peril": "Hurricane",  "state": "FL", "lat": 25.77,  "lon": -80.19,  "impact_m": 210, "contracts": 28},
        {"peril": "Hurricane",  "state": "FL", "lat": 30.33,  "lon": -81.65,  "impact_m": 155, "contracts": 19},
        {"peril": "Hurricane",  "state": "LA", "lat": 29.95,  "lon": -90.07,  "impact_m": 130, "contracts": 15},
        {"peril": "Hurricane",  "state": "TX", "lat": 29.76,  "lon": -95.36,  "impact_m":  95, "contracts": 12},
        {"peril": "Earthquake", "state": "CA", "lat": 34.05,  "lon": -118.24, "impact_m": 185, "contracts": 22},
        {"peril": "Earthquake", "state": "CA", "lat": 37.77,  "lon": -122.41, "impact_m": 140, "contracts": 17},
        {"peril": "Earthquake", "state": "OR", "lat": 45.52,  "lon": -122.68, "impact_m":  60, "contracts":  8},
        {"peril": "Wildfire",   "state": "CA", "lat": 38.58,  "lon": -121.49, "impact_m":  90, "contracts": 11},
        {"peril": "Wildfire",   "state": "CO", "lat": 39.73,  "lon": -104.98, "impact_m":  45, "contracts":  6},
        {"peril": "Hail",       "state": "TX", "lat": 32.77,  "lon":  -96.79, "impact_m":  70, "contracts":  9},
        {"peril": "Hail",       "state": "OK", "lat": 35.47,  "lon":  -97.51, "impact_m":  55, "contracts":  7},
        {"peril": "Hail",       "state": "KS", "lat": 39.05,  "lon":  -95.68, "impact_m":  40, "contracts":  5},
    ])


_map_title = "Exposure Map"
if _active_peril or _active_region:
    _map_title += f" — {_active_peril or ''} {_active_region or ''}".strip()
st.subheader(_map_title)
st.caption(_exp_badge)

PERIL_COLORS = {
    "Wind":     EVEREST_BLUE,
    "EQ":       DARK_PURPLE,
    "Flood":    DARK_TEAL,
    "Wildfire": MID_BLUE,
    "MPCI":     LIGHT_PURPLE,
    "CROP":     LIGHT_TEAL,
}

if "lat" in exposures.columns and "lon" in exposures.columns and len(exposures) > 0:
    exposures = exposures.copy()
    exposures["lat"] = pd.to_numeric(exposures["lat"], errors="coerce")
    exposures["lon"] = pd.to_numeric(exposures["lon"], errors="coerce")
    exposures["impact_m"] = pd.to_numeric(exposures["impact_m"], errors="coerce").fillna(0)
    exposures = exposures.dropna(subset=["lat", "lon"])
    exposures["bubble_size"] = exposures["impact_m"].clip(lower=5)

    fig_map = px.scatter_mapbox(
        exposures,
        lat="lat",
        lon="lon",
        size="bubble_size",
        size_max=50,
        color="peril",
        color_discrete_map=PERIL_COLORS,
        hover_name="state" if "state" in exposures.columns else None,
        hover_data={c: True for c in ["impact_m", "contracts"] if c in exposures.columns},
        labels={"impact_m": "Avg Annual Loss ($M)", "contracts": "Contracts", "peril": "Peril"},
        zoom=4 if (_active_peril or _active_region) else 3,
        center=(
            {"lat": exposures["lat"].mean(), "lon": exposures["lon"].mean()}
            if (_active_peril or _active_region) and len(exposures) > 0
            else {"lat": 37.0, "lon": -96.0}
        ),
        mapbox_style="carto-positron",
        height=500,
    )
    fig_map.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        legend=dict(
            title="Peril", orientation="h",
            yanchor="bottom", y=1.01, xanchor="left", x=0,
            bgcolor="rgba(255,255,255,0.85)",
            font=dict(size=12, color=DARK_BLUE),
        ),
    )
    st.plotly_chart(fig_map, use_container_width=True)
else:
    st.info("No mappable exposure data returned from SQL. Check server/database and permissions.")

# ── Top Catapult Program Scenarios impacted by active question ───────────────
with st.spinner("Loading impacted program scenarios…"):
    _scn_data, _scn_live = _fetch_top_program_scenarios(
        sql_server,
        sql_database,
        peril_filter=_active_peril,
        region_filter=_active_region,
    )

_scn_title = "Top 10 Impacted Catapult Program Scenarios"
if _active_peril or _active_region:
    _scn_title += f" — {_active_peril or ''} {_active_region or ''}".strip()
st.subheader(_scn_title)

if _scn_live and _scn_data and not _scn_data.get("error"):
    _source = _scn_data.get("source", "dbo.Catapult_Loss_All_NonCorrelating")
    _rows = _scn_data.get("rows", [])
    _filter_txt = (
        f" · filtered: {_active_peril or 'all perils'} / {_active_region or 'all regions'}"
        if (_active_peril or _active_region)
        else " · unfiltered"
    )
    st.caption(f"🟢 Live – `{_source}` ({len(_rows)} rows){_filter_txt}")

    if len(_rows) == 0:
        st.info("No impacted Catapult program scenarios found for the current filter.")
    else:
        scn_df = pd.DataFrame(_rows)
        scn_df.rename(
            columns={
                "company_name": "Company_Name",
                "program_scenario": "Program Scenario",
                "uws_contract_nbrs": "UWS_Contract_Nbr/s",
                "avg_annual_gross_loss_m": "Avg Annual Gross Loss ($M)",
            },
            inplace=True,
        )

        for c in ["Avg Annual Gross Loss ($M)"]:
            if c in scn_df.columns:
                scn_df[c] = pd.to_numeric(scn_df[c], errors="coerce").fillna(0.0).round(2)

        scn_df = scn_df[[
            "Company_Name",
            "Program Scenario",
            "UWS_Contract_Nbr/s",
            "Avg Annual Gross Loss ($M)",
        ]]

        st.dataframe(scn_df, use_container_width=True, hide_index=True)
else:
    st.caption("🟡 Sample data – SQL connection not available")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Company_Name": "EVEREST REINSURANCE COMPANY",
                    "Program Scenario": "Venezuela EQ Base",
                    "UWS_Contract_Nbr/s": "UWS-10231, UWS-11984",
                    "Avg Annual Gross Loss ($M)": 0.12,
                },
                {
                    "Company_Name": "EVEREST REINSURANCE COMPANY",
                    "Program Scenario": "Andean EQ Stress",
                    "UWS_Contract_Nbr/s": "UWS-13045",
                    "Avg Annual Gross Loss ($M)": 0.08,
                },
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )
