import re
import pandas as pd
from django.core.cache import cache

from apps.db.connection import run_sql
from apps.scenario.catalogs import (
    MODEL_CATALOG, PERIL_DB_CODES, PERIL_ALIASES, ZONE_TOKEN_MAP,
    QUERY_STOPWORDS, STATE_TOKENS, AMBIGUOUS_SHORT_TOKENS,
    _PERIL_TO_MODELS,
)
from django.conf import settings


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
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]} {tokens[i+1]}"
            if bigram in ZONE_TOKEN_MAP:
                best_zone = ZONE_TOKEN_MAP[bigram]
                best_priority = 3
                break
        for t in tokens:
            if t not in ZONE_TOKEN_MAP:
                continue
            if len(t) <= 2 and t in AMBIGUOUS_SHORT_TOKENS:
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

    m_mag = re.search(r"(?:magnitude|mag)\s*(\d+(?:\.\d+)?)\s*(?:to|\-)\s*(\d+(?:\.\d+)?)", q)
    if m_mag:
        out["mag_lo"] = float(m_mag.group(1))
        out["mag_hi"] = float(m_mag.group(2))

    m_rng = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:to|\-)\s*(\d+(?:\.\d+)?)\s*(?:b|bn|billion)",
        q,
    )
    if not m_rng:
        m_rng = re.search(
            r"(?:industry\s*loss|loss)\s*(?:of\s+)?(\d+(?:\.\d+)?)\s*(?:to|\-)\s*(\d+(?:\.\d+)?)",
            q,
        )
    if m_rng:
        out["loss_lo"] = float(m_rng.group(1))
        out["loss_hi"] = float(m_rng.group(2))

    m_model = re.search(r"(?:model|m)\s*#?\s*(\d{1,4})", q)
    if m_model:
        out["model_no"] = int(m_model.group(1))

    m_evt = re.search(r"(?:description|desc|keyword)\s*[:=]?\s*([a-z0-9\-\s]+)", q)
    if m_evt:
        out["event_keyword"] = m_evt.group(1).strip()

    return out


def compute_confidence(parsed: dict) -> tuple[str, int, int]:
    parts = 0
    total = 3
    if parsed.get("peril"):
        parts += 1
    if parsed.get("zone"):
        parts += 1
    if parsed.get("loss_lo") is not None and parsed.get("loss_hi") is not None:
        parts += 1
    if parts >= 2:
        level = "high"
    elif parts == 1:
        level = "partial"
    else:
        level = "needs_refinement"
    return level, parts, total


def models_for_peril(peril: str) -> set[int]:
    if not peril or peril == "All":
        return set(MODEL_CATALOG.keys())
    return set(_PERIL_TO_MODELS.get(peril, []))


def industry_peril_clause(peril: str) -> str:
    if not peril or peril == "All":
        return ""
    db_codes = PERIL_DB_CODES.get(peril)
    if not db_codes:
        return ""
    if len(db_codes) == 1:
        return f"AND iu.Peril = '{db_codes[0]}'"
    codes_csv = ", ".join(f"'{c}'" for c in db_codes)
    return f"AND iu.Peril IN ({codes_csv})"


def peril_table_tokens(peril: str) -> list[str]:
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


def prefilter_air_profiles_by_peril(profiles: list[dict], peril: str):
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


def _pick_col(col_map: dict, aliases: list[str]):
    for a in aliases:
        if a in col_map:
            return col_map[a]
    return None


def discover_air_event_tables(server: str, database: str):
    cache_key = f"air_tables:{server}:{database}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    q = f"""
SELECT c.TABLE_SCHEMA, c.TABLE_NAME, c.COLUMN_NAME
FROM [{settings.AIR_EVENTS_DB}].INFORMATION_SCHEMA.COLUMNS c
JOIN [{settings.AIR_EVENTS_DB}].INFORMATION_SCHEMA.TABLES t
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

    cache.set(cache_key, profiles, 600)
    return profiles


def infer_model_from_industry(server: str, database: str, peril: str, zone_filter: str):
    cache_key = f"model_infer:{server}:{database}:{peril}:{zone_filter}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

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
    result = int(v) if pd.notna(v) else None
    cache.set(cache_key, result, 300)
    return result


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


def best_fallback_table(profiles: list[dict], zone_filter: str) -> str | None:
    """Pick the best AIR table using catalog geography when DB inference fails."""
    if not profiles:
        return None

    geo_tokens: set[str] = set()
    zf_lower = (zone_filter or "").lower().strip()
    for token, zone_val in ZONE_TOKEN_MAP.items():
        if zone_val.lower() == zf_lower:
            geo_tokens.add(token)
    for word in zf_lower.split():
        if len(word) >= 2:
            geo_tokens.add(word)

    best_label = None
    best_score = -999

    for p in profiles:
        label = f"{p['schema']}.{p['table']}"
        m = re.search(r"(?:Tbl)?Model[_]?(\d+)", p["table"], re.IGNORECASE)
        if not m:
            if best_score < 0:
                best_label = label
                best_score = 0
            continue
        model_no = int(m.group(1))
        entry = MODEL_CATALOG.get(model_no)
        if not entry:
            continue

        score = 0
        model_label = entry["label"].lower()
        model_region = entry["region"].lower()

        for gt in geo_tokens:
            if gt in model_region:
                score += 3
            if gt in model_label:
                score += 3

        if "/" in entry["region"]:
            score += 1

        for place in ["hawaii", "alaska", "guam", "india", "japan", "china",
                       "australia", "korea"]:
            if place in model_label and place not in geo_tokens:
                score -= 5

        if score > best_score:
            best_score = score
            best_label = label

    return best_label


def get_distinct_zones(server: str, database: str, peril: str) -> list[str]:
    cache_key = f"zones:{server}:{database}:{peril}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    peril_pred = industry_peril_clause(peril)
    where = f"WHERE 1=1 {peril_pred}" if peril_pred else ""
    q = f"""
SELECT DISTINCT [Zone]
FROM [Industry].[dbo].[Industry_Unadjusted_V21_ZonePercent]
{where}
ORDER BY [Zone];
"""
    try:
        df = run_sql(server, database, q)
    except Exception:
        return []
    if df is None or df.empty:
        return []
    result = [str(v) for v in df["Zone"].dropna().tolist()]
    cache.set(cache_key, result, 600)
    return result


def extract_query_keywords(text: str) -> list[str]:
    q = (text or "").lower()
    toks = re.findall(r"[a-z0-9]+", q)
    out = []
    for t in toks:
        if t in QUERY_STOPWORDS:
            continue
        if t.isdigit():
            continue
        if len(t) >= 3 or t in STATE_TOKENS or t == "us":
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
FROM [{settings.AIR_EVENTS_DB}].[{schema}].[{table}] a
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
FROM [{settings.AIR_EVENTS_DB}].[{schema}].[{table}]
WHERE TRY_CONVERT(bigint, [{event_id_col}]) IN ({ids_csv});
"""
    try:
        df = run_sql(server, database, q)
    except Exception:
        return pd.DataFrame()
    return df if df is not None else pd.DataFrame()


def fetch_air_descriptions_for_peril(server, database, profile, peril, zone_filter="", contains_text="", limit=500):
    if not profile or not profile.get("desc_col"):
        return []

    cache_key = f"air_descs:{server}:{database}:{profile['schema']}.{profile['table']}:{peril}:{zone_filter}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

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
FROM [{settings.AIR_EVENTS_DB}].[{schema}].[{table}] a
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
    result = [str(v) for v in df["EventDescription"].dropna().tolist()]
    cache.set(cache_key, result, 300)
    return result
