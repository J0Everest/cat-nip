import os
import pyodbc
import pandas as pd

SERVER = os.getenv("DB_SERVER_CURRENT") or os.getenv("DB_SERVER", "ERRSACTDBP1")
DATABASE = os.getenv("DB_CATACCUM_DATABASE", "CatAccum2604")
DRIVER = os.getenv("ODBC_DRIVER", "ODBC Driver 18 for SQL Server")

conn = pyodbc.connect(
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=Yes;"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
    "Connection Timeout=8;"
)

q = """
SELECT TABLE_SCHEMA, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_TYPE='BASE TABLE'
  AND (
        TABLE_NAME LIKE '%Catapult%'
     OR TABLE_NAME LIKE '%Scenario%'
     OR TABLE_NAME LIKE '%Program%'
  )
ORDER BY TABLE_SCHEMA, TABLE_NAME;
"""

print(pd.read_sql(q, conn).to_string(index=False))
conn.close()
