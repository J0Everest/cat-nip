import os
import json
import pyodbc
import pandas as pd
from pathlib import Path

SERVER = os.getenv("DB_SERVER_CURRENT") or os.getenv("DB_SERVER", "ERRSACTDBP1")
DATABASE = os.getenv("DB_CATACCUM_DATABASE", "CatAccum2604")
AIR_DB = os.getenv("AIR_EVENTS_DB", "AIREvents2025_TS13")
DRIVER = os.getenv("ODBC_DRIVER", "ODBC Driver 18 for SQL Server")

_HERE = Path(__file__).parent
OUT_CSV = str(_HERE / "air_event_descriptions_distinct.csv")
OUT_JSON = str(_HERE / "air_event_descriptions_summary.json")

DESC_ALIASES = {"eventdescription", "eventdesc", "description", "desc", "name"}

conn_str = (
    f"Driver={{{DRIVER}}};"
    f"Server={SERVER};Database={DATABASE};"
    "Trusted_Connection=Yes;Persist Security Info=False;Pooling=False;"
    "MultipleActiveResultSets=False;Encrypt=No;TrustServerCertificate=No;"
    "Packet Size=4096;Connection Timeout=30;"
)

q_cols = f"""
SELECT c.TABLE_SCHEMA, c.TABLE_NAME, c.COLUMN_NAME
FROM [{AIR_DB}].INFORMATION_SCHEMA.COLUMNS c
JOIN [{AIR_DB}].INFORMATION_SCHEMA.TABLES t
  ON t.TABLE_SCHEMA = c.TABLE_SCHEMA
 AND t.TABLE_NAME = c.TABLE_NAME
WHERE t.TABLE_TYPE = 'BASE TABLE'
ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION;
"""

all_desc = set()
summary = {
    "server": SERVER,
    "database": DATABASE,
    "air_db": AIR_DB,
    "tables_scanned": 0,
    "tables_with_description": 0,
    "table_details": [],
}

with pyodbc.connect(conn_str) as conn:
    cols_df = pd.read_sql(q_cols, conn)

    if cols_df.empty:
        pd.DataFrame(columns=["EventDescription"]).to_csv(OUT_CSV, index=False)
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print("No tables/columns found in AIREvents DB.")
        raise SystemExit(0)

    grouped = cols_df.groupby(["TABLE_SCHEMA", "TABLE_NAME"], dropna=False)
    summary["tables_scanned"] = int(len(grouped))

    cur = conn.cursor()
    for (schema, table), g in grouped:
        cols = [str(c) for c in g["COLUMN_NAME"].tolist()]
        lower_map = {c.lower(): c for c in cols}
        desc_col = None
        for alias in DESC_ALIASES:
            if alias in lower_map:
                desc_col = lower_map[alias]
                break

        tbl_info = {
            "schema": str(schema),
            "table": str(table),
            "description_column": desc_col,
            "rows_added": 0,
            "status": "skipped" if not desc_col else "ok",
        }

        if not desc_col:
            summary["table_details"].append(tbl_info)
            continue

        summary["tables_with_description"] += 1
        sql = f"""
SELECT DISTINCT CAST([{desc_col}] AS nvarchar(4000)) AS EventDescription
FROM [{AIR_DB}].[{schema}].[{table}]
WHERE [{desc_col}] IS NOT NULL
  AND LTRIM(RTRIM(CAST([{desc_col}] AS nvarchar(4000)))) <> '';
"""
        try:
            cur.execute(sql)
            rows = cur.fetchall()
            before = len(all_desc)
            for r in rows:
                val = str(r[0]).strip()
                if val:
                    all_desc.add(val)
            tbl_info["rows_added"] = len(all_desc) - before
        except Exception as exc:
            tbl_info["status"] = f"error: {exc}"

        summary["table_details"].append(tbl_info)

out_df = pd.DataFrame(sorted(all_desc), columns=["EventDescription"])
out_df.to_csv(OUT_CSV, index=False)
summary["distinct_descriptions"] = int(len(out_df))

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

print(f"Wrote {len(out_df):,} distinct descriptions to {OUT_CSV}")
print(f"Summary: {OUT_JSON}")
