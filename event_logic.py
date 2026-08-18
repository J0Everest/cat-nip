"""
Shared event-response business logic.
Contains query parsing, SQL generation, and data-fetching functions used by
both the new Scenario Builder and the legacy Event Response views.
"""
import re
import pandas as pd
import streamlit as st

from _db import run_sql
from config import AIR_EVENTS_DB

# ── Model Catalog ─────────────────────────────────────────────────────────────
# Definitive mapping of AIR model numbers to peril, region, and description.
# Built from Industry DB queries + AIR event description sampling (Aug 2026).
# Industry DB peril codes: EQ, FI, ST, ST+WD, TC, WS
# Models not present in Industry are marked with industry_peril=None.

MODEL_CATALOG = {
    5:  {"industry_peril": "FI",   "region": "US",              "label": "US Wildfire"},
    6:  {"industry_peril": None,   "region": "AusNZ",           "label": "Australia Bushfire"},
    8:  {"industry_peril": None,   "region": "US",              "label": "US Flood"},
    11: {"industry_peril": "EQ",   "region": "US/Canada",       "label": "US/Canada Earthquake"},
    13: {"industry_peril": "EQ",   "region": "US",              "label": "Hawaii Earthquake"},
    14: {"industry_peril": "EQ",   "region": "US",              "label": "Alaska Earthquake"},
    15: {"industry_peril": "EQ",   "region": "Caribbean",       "label": "Caribbean Earthquake"},
    18: {"industry_peril": None,   "region": "Asia",            "label": "Japan Flood"},
    19: {"industry_peril": None,   "region": "Canada",          "label": "Canada Flood"},
    20: {"industry_peril": "ST",   "region": "US",              "label": "US Severe Thunderstorm"},
    22: {"industry_peril": None,   "region": "US",              "label": "US Severe Thunderstorm (10K)"},
    23: {"industry_peril": "TC",   "region": "US",              "label": "Hawaii Hurricane"},
    26: {"industry_peril": None,   "region": "Canada",          "label": "Canada Windstorm"},
    27: {"industry_peril": "TC",   "region": "US/Caribbean",    "label": "North Atlantic Hurricane"},
    28: {"industry_peril": "WS",   "region": "US",              "label": "US Winter Storm"},
    30: {"industry_peril": None,   "region": "Canada",          "label": "Canada Hurricane"},
    31: {"industry_peril": "EQ",   "region": "Europe/MidEast",  "label": "Europe/Mid East Earthquake"},
    33: {"industry_peril": None,   "region": "US",              "label": "US SE Earthquake (Alabama)"},
    41: {"industry_peril": "WS",   "region": "Europe",          "label": "Europe Winter Storm"},
    42: {"industry_peril": None,   "region": "Canada",          "label": "Canada Winter Storm"},
    43: {"industry_peril": None,   "region": "Europe",          "label": "Europe Windstorm"},
    44: {"industry_peril": None,   "region": "AusNZ",           "label": "Australia Severe Thunderstorm"},
    50: {"industry_peril": None,   "region": "MidEast",         "label": "Iran Earthquake"},
    51: {"industry_peril": "EQ",   "region": "AusNZ",           "label": "Australia Earthquake"},
    52: {"industry_peril": "EQ",   "region": "Asia",            "label": "Japan Earthquake"},
    53: {"industry_peril": "EQ",   "region": "AusNZ",           "label": "New Zealand Earthquake"},
    54: {"industry_peril": "EQ",   "region": "Asia",            "label": "SE Asia Earthquake"},
    55: {"industry_peril": "EQ",   "region": "Asia",            "label": "China Earthquake"},
    58: {"industry_peril": None,   "region": "Asia",            "label": "Asia Earthquake"},
    60: {"industry_peril": "ST+WD","region": "Asia",            "label": "NW Pacific Typhoon"},
    61: {"industry_peril": "TC",   "region": "AusNZ",           "label": "Australia Tropical Cyclone"},
    68: {"industry_peril": None,   "region": "Asia",            "label": "India/Bay of Bengal Cyclone"},
    70: {"industry_peril": "EQ",   "region": "SouthAmerica",    "label": "South America Earthquake"},
    72: {"industry_peril": "EQ",   "region": "CentralAmerica",  "label": "Mexico Earthquake"},
    76: {"industry_peril": "EQ",   "region": "CentralAmerica",  "label": "Central America Earthquake"},
    86: {"industry_peril": None,   "region": "US/Canada",       "label": "US/Canada Crop/Agriculture"},
    90: {"industry_peril": None,   "region": "Europe",          "label": "Europe Flood"},
    92: {"industry_peril": None,   "region": "Europe",          "label": "UK/Ireland Flood"},
    94: {"industry_peril": None,   "region": "CentralAmerica",  "label": "Central America Flood"},
    96: {"industry_peril": None,   "region": "Europe",          "label": "Italy Flood"},
}

# User-facing peril → Industry DB peril code(s) that appear in
# Industry_Unadjusted_V21_ZonePercent.Peril
PERIL_DB_CODES = {
    "EQ":                ["EQ"],
    "TC":                ["TC", "ST+WD"],
    "Winter Storm":      ["WS"],
    "Severe Storm":      ["ST"],
    "Fire / Wildfire":   ["FI"],
}

# Peril grouping: maps a user-facing peril name to the set of MODEL_CATALOG
# models that cover that peril (including models not in Industry DB).
_PERIL_TO_MODELS = {
    "EQ":              [5, 11, 13, 14, 15, 31, 33, 50, 51, 52, 53, 54, 55, 58, 70, 72, 76],
    "TC":              [23, 27, 30, 60, 61, 68],
    "Winter Storm":    [28, 41, 42],
    "Severe Storm":    [20, 22, 26, 43, 44],
    "Fire / Wildfire": [5, 6],
    "Flood":           [8, 18, 19, 90, 92, 94, 96],
}

# Fix model 5: Industry marks it as FI but descriptions say "Wildfire"
# so it belongs in Fire/Wildfire, not in EQ. Remove from EQ list.
_PERIL_TO_MODELS["EQ"] = [m for m in _PERIL_TO_MODELS["EQ"] if m != 5]

PERIL_ALIASES = {
    "eq": "EQ", "earthquake": "EQ", "quake": "EQ", "seismic": "EQ",
    "hurricane": "TC", "typhoon": "TC", "cyclone": "TC",
    "tropical": "TC", "tc": "TC",
    "wind": "TC", "storm": "Severe Storm",
    "winterstorm": "Winter Storm", "winter storm": "Winter Storm",
    "winter": "Winter Storm", "ws": "Winter Storm",
    "severe thunderstorm": "Severe Storm", "thunderstorm": "Severe Storm",
    "tornado": "Severe Storm", "hail": "Severe Storm",
    "convective": "Severe Storm", "st": "Severe Storm",
    "flood": "Flood", "flooding": "Flood", "inland flood": "Flood",
    "wildfire": "Fire / Wildfire", "fire": "Fire / Wildfire",
    "bushfire": "Fire / Wildfire", "fi": "Fire / Wildfire",
}

ZONE_TOKEN_MAP = {
    # United States
    "us": "US", "usa": "US", "u.s.": "US",
    "unitedstates": "US", "united states": "US", "america": "US",
    "florida": "Zone 03 FL", "fl": "Zone 03 FL", "miami": "Zone 03 FL",
    "california": "Zone 09", "ca": "Zone 09",
    "texas": "Zone 03 Gulf", "tx": "Zone 03 Gulf",
    "gulf": "Zone 03 Gulf", "gulfcoast": "Zone 03 Gulf",
    "georgia": "Zone 03 GA SC", "ga": "Zone 03 GA SC",
    "south carolina": "Zone 03 GA SC", "sc": "Zone 03 GA SC",
    "north carolina": "Zone 03 NC", "nc": "Zone 03 NC",
    "northeast": "Zone 01", "new england": "Zone 01",
    "midatlantic": "Zone 02", "mid atlantic": "Zone 02",
    "southeast": "Zone 04", "se": "Zone 04",
    "midwest": "Zone 05 and 06", "central": "Zone 05 and 06",
    "northwest": "Zone 07", "pacific northwest": "Zone 07",
    "west": "Zone 08", "mountain": "Zone 08",
    "alaska": "Zone 09", "ak": "Zone 09",
    "hawaii": "Zone 10", "hi": "Zone 10",
    "ny": "Zone 01", "nj": "Zone 02", "pa": "Zone 02",
    "ct": "Zone 01", "ma": "Zone 01", "ri": "Zone 01",
    "nh": "Zone 01", "vt": "Zone 01", "me": "Zone 01",
    "md": "Zone 02", "va": "Zone 04", "de": "Zone 02",
    "la": "Zone 03 Gulf", "ms": "Zone 03 Gulf", "al": "Zone 04",
    "wa": "Zone 07", "or": "Zone 07",
    "az": "Zone 08", "nm": "Zone 08", "co": "Zone 08",
    "ut": "Zone 08", "nv": "Zone 08",
    "mn": "Zone 05 and 06", "wi": "Zone 05 and 06",
    "il": "Zone 05 and 06", "in": "Zone 05 and 06",
    "mi": "Zone 05 and 06", "oh": "Zone 05 and 06",
    "mo": "Zone 05 and 06", "ia": "Zone 05 and 06",
    "ks": "Zone 05 and 06", "ne": "Zone 05 and 06",
    "ok": "Zone 04", "ar": "Zone 04",
    "ky": "Zone 04", "tn": "Zone 04", "wv": "Zone 04",
    "nd": "Zone 05 and 06", "sd": "Zone 05 and 06",
    "mt": "Zone 07", "wy": "Zone 08", "id": "Zone 07",
    # Caribbean
    "caribbean": "Caribbean", "puerto rico": "Caribbean  Puerto Rico",
    "bahamas": "Caribbean  Bahamas", "bermuda": "Caribbean  Bermuda",
    "jamaica": "Caribbean  Jamaica", "cuba": "Caribbean  Cuba",
    "dominican republic": "Caribbean  Dominican Republic",
    "trinidad": "Caribbean  Trinidad and Tobago",
    "virgin islands": "Caribbean  Virgin Islands",
    "cayman": "Caribbean  Cayman Islands",
    # Canada
    "canada": "Canada", "canadian": "Canada",
    "ontario": "Canada  ON", "on": "Canada  ON",
    "quebec": "Canada  QC", "qc": "Canada  QC",
    "bc": "Canada  BC", "british columbia": "Canada  BC",
    "alberta": "Canada  AB", "ab": "Canada  AB",
    # Central America
    "mexico": "Central America  Mexico", "mexican": "Central America  Mexico",
    "costa rica": "Central America  Costa Rica",
    "guatemala": "Central America  Guatemala",
    "panama": "Central America  Panama",
    "honduras": "Central America  Honduras",
    "el salvador": "Central America  El Salvador",
    "nicaragua": "Central America  Nicaragua",
    "belize": "Central America  Belize",
    "central america": "Central America",
    # South America
    "venezuela": "South America  Venezuela", "venezuelan": "South America  Venezuela",
    "colombia": "South America  Colombia", "colombian": "South America  Colombia",
    "peru": "South America  Peru", "peruvian": "South America  Peru",
    "ecuador": "South America  Ecuador", "ecuadorian": "South America  Ecuador",
    "chile": "South America  Chile", "chilean": "South America  Chile",
    "south america": "South America",
    # Europe
    "europe": "Europe", "european": "Europe",
    "uk": "Europe  UK", "united kingdom": "Europe  UK",
    "britain": "Europe  UK", "england": "Europe  UK",
    "germany": "Europe  Germany", "german": "Europe  Germany",
    "france": "Europe  France", "french": "Europe  France",
    "italy": "Europe  Italy", "italian": "Europe  Italy",
    "spain": "Europe  Spain", "spanish": "Europe  Spain",
    "netherlands": "Europe  Netherlands", "dutch": "Europe  Netherlands",
    "switzerland": "Europe  Switzerland", "swiss": "Europe  Switzerland",
    "ireland": "Europe  Ireland", "irish": "Europe  Ireland",
    "poland": "Europe  Poland",
    "denmark": "Europe  Denmark",
    "norway": "Europe  Norway",
    "sweden": "Europe  Sweden",
    "finland": "Europe  Finland",
    "austria": "Europe  Austria",
    "belgium": "Europe  Belgium",
    "portugal": "Europe  Portugal",
    "greece": "Europe  Greece",
    "czech": "Europe  Czech Republic",
    "romania": "Europe  Romania",
    # Asia
    "asia": "Asia", "asian": "Asia",
    "japan": "Asia  Japan", "japanese": "Asia  Japan",
    "china": "Asia  China", "chinese": "Asia  China",
    "taiwan": "Asia  Taiwan",
    "philippines": "Asia  Philippines", "filipino": "Asia  Philippines",
    "indonesia": "Asia  Indonesia", "indonesian": "Asia  Indonesia",
    "vietnam": "Asia  Vietnam",
    "south korea": "Asia  South Korea", "korea": "Asia  South Korea",
    "singapore": "Asia  Singapore",
    "hong kong": "Asia  Hong Kong",
    # Mid East
    "turkey": "Mid East  Turkey", "turkish": "Mid East  Turkey",
    "turkiye": "Mid East  Turkey",
    "israel": "Mid East  Israel", "israeli": "Mid East  Israel",
    "iran": "Mid East", "iranian": "Mid East",
    "middle east": "Mid East", "mideast": "Mid East",
    # Australia / New Zealand
    "australia": "AusNZ  Australia", "australian": "AusNZ  Australia",
    "new zealand": "AusNZ  New Zealand", "nz": "AusNZ  New Zealand",
    "ausnz": "AusNZ",
    # India
    "india": "Asia", "indian": "Asia",
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

_AMBIGUOUS_SHORT_TOKENS = {"in", "or", "me", "de", "on", "hi", "id", "ok", "se"}

PERIL_OPTIONS = ["All", "EQ", "TC", "Winter Storm", "Severe Storm", "Fire / Wildfire", "Flood"]


# ── Parsing ────────────────────────────────────────────────────────────────────

def parse_scenario_query(text: str) -> dict:
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
        best_zone = None
        best_priority = -1
        for t in tokens:
            if t not in ZONE_TOKEN_MAP:
                continue
            if len(t) <= 2 and t in _AMBIGUOUS_SHORT_TOKENS:
                priority = 0
            elif len(t) <= 2:
                priority = 1
            else:
                priority = 2
            if priority > best_priority:
                best_priority = priority
                best_zone = ZONE_TOKEN_MAP[t]
        if best_zone:
            out["zone"] = best_zone

    m_rng = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:to|\-)\s*(\d+(?:\.\d+)?)(?:\s*(?:b|bn|billion))?\s*(?:industry\s*loss)?",
        q,
    )
    if m_rng:
        out["loss_lo"] = float(m_rng.group(1))
        out["loss_hi"] = float(m_rng.group(2))

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


# ── AIR table discovery and helpers ────────────────────────────────────────────

def _pick_col(col_map: dict, aliases: list[str]):
    for a in aliases:
        if a in col_map:
            return col_map[a]
    return None


def peril_table_tokens(peril: str) -> list[str]:
    """Return keyword tokens for matching AIR table names by peril.
    Used as fallback when MODEL_CATALOG doesn't cover a table.
    """
    p = (peril or "All").strip()
    if p == "EQ":
        return ["earthquake", "eq", "quake", "seismic"]
    if p == "TC":
        return ["hurricane", "typhoon", "cyclone", "tropical", "wind", "storm"]
    if p == "Winter Storm":
        return ["winterstorm", "winter"]
    if p == "Severe Storm":
        return ["thunderstorm", "severe", "convective", "hail", "tornado"]
    if p == "Fire / Wildfire":
        return ["wildfire", "bushfire", "fire"]
    if p == "Flood":
        return ["flood", "inland"]
    return []


def models_for_peril(peril: str) -> set[int]:
    """Return model numbers from MODEL_CATALOG that match a user-facing peril."""
    if not peril or peril == "All":
        return set(MODEL_CATALOG.keys())
    return set(_PERIL_TO_MODELS.get(peril, []))


def industry_peril_clause(peril: str) -> str:
    """Build a SQL WHERE clause fragment for Industry DB peril filtering.
    Maps user-facing peril names to actual Industry DB peril codes.
    Returns empty string for 'All' or peril types not in Industry DB (e.g. Flood).
    """
    if not peril or peril == "All":
        return ""
    db_codes = PERIL_DB_CODES.get(peril)
    if not db_codes:
        return ""
    if len(db_codes) == 1:
        return f"AND iu.Peril = '{db_codes[0]}'"
    codes_csv = ", ".join(f"'{c}'" for c in db_codes)
    return f"AND iu.Peril IN ({codes_csv})"


def prefilter_air_profiles_by_peril(profiles: list[dict], peril: str):
    """Filter/rank AIR table profiles by peril.
    Uses MODEL_CATALOG for deterministic matching, falls back to keyword scoring.
    """
    if not peril or peril == "All":
        return profiles, False

    target_models = models_for_peril(peril)

    catalog_matched = []
    keyword_candidates = []

    for p in profiles:
        m = re.search(r"(?:Tbl)?Model[_]?(\d+)", p["table"], re.IGNORECASE)
        if m:
            model_no = int(m.group(1))
            if model_no in target_models:
                catalog_matched.append(p)
                continue

        keyword_candidates.append(p)

    if catalog_matched:
        return catalog_matched, True

    tokens = peril_table_tokens(peril)
    if not tokens:
        return profiles, False
    scored = []
    for p in keyword_candidates:
        label = f"{p['schema']}.{p['table']}".lower()
        score = sum(1 for t in tokens if t in label)
        if score > 0:
            scored.append((score, p))
    if not scored:
        return profiles, False
    scored.sort(key=lambda x: (-x[0], f"{x[1]['schema']}.{x[1]['table']}"))
    return [p for _, p in scored], True


@st.cache_data(show_spinner=False, ttl=300)
def infer_model_from_industry(server: str, database: str, peril: str, zone_filter: str):
    peril_pred = industry_peril_clause(peril)
    zone_filter = (zone_filter or "").replace("'", "''").strip()
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
    return int(v) if pd.notna(v) else None


def match_table_by_model(labels: list[str], model_no: int | None):
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


def extract_query_keywords(text: str) -> list[str]:
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
    seen = set()
    uniq = []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq


def infer_table_by_keyword_match(server, database, profiles, peril, zone_filter, scenario_text):
    if not profiles:
        return None
    keywords = extract_query_keywords(scenario_text)
    if not keywords:
        return None

    keywords = keywords[:6]
    peril_pred = industry_peril_clause(peril)
    zone_sql = (zone_filter or "").replace("'", "''").strip()
    zone_pred = "" if not zone_sql else f"AND iu.[Zone] LIKE '%{zone_sql}%'"

    best_label = None
    best_score = -1

    for p in profiles:
        if not p.get("desc_col"):
            continue
        schema, table = p["schema"], p["table"]
        eid, dcol = p["event_id_col"], p["desc_col"]

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
def discover_air_event_tables(server: str, database: str):
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
        profiles.append({
            "schema": str(schema),
            "table": str(table),
            "event_id_col": event_id_col,
            "desc_col": _pick_col(col_map, ["eventdescription", "eventdesc", "description", "desc", "name"]),
            "mag_col": _pick_col(col_map, ["magnitude", "mag", "maxmagnitude", "intensity"]),
            "loc_col": _pick_col(col_map, ["location", "region", "zone", "country", "state", "city"]),
        })
    return profiles


def fetch_air_event_details(server, database, event_ids, profile):
    if not event_ids or not profile:
        return pd.DataFrame()

    schema, table = profile["schema"], profile["table"]
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
def fetch_air_descriptions_for_peril(server, database, profile, peril, zone_filter="", contains_text="", limit=500):
    if not profile or not profile.get("desc_col"):
        return []

    schema, table = profile["schema"], profile["table"]
    event_id_col, desc_col = profile["event_id_col"], profile["desc_col"]

    peril_pred = industry_peril_clause(peril)
    zone_filter = (zone_filter or "").replace("'", "''").strip()
    contains_text = (contains_text or "").replace("'", "''").strip()

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


# ── SQL generators ─────────────────────────────────────────────────────────────

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
