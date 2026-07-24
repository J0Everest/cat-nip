import os
import pyodbc
import pandas as pd

SERVER = os.getenv("DB_SERVER_CURRENT") or os.getenv("DB_SERVER", "ERRSACTDBP1")
DATABASE = os.getenv("DB_CATACCUM_DATABASE", "CatAccum2604")
DRIVER = os.getenv("ODBC_DRIVER", "ODBC Driver 18 for SQL Server")

TABLES = [
    "Catapult_Loss_All_NonCorrelating",
    "Catapult_Loss_All",
    "Catapult_Tbl_Program_Scenario",
    "Catapult_Tbl_Program",
    "Catapult_Tbl_Layer",
]

conn = pyodbc.connect(
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    "Trusted_Connection=Yes;"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
    "Connection Timeout=8;"
)

for tbl in TABLES:
    print("\n" + "=" * 80)
    print(tbl)
    q = f"""
    SELECT COLUMN_NAME, DATA_TYPE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='{tbl}'
    ORDER BY ORDINAL_POSITION;
    """
    df = pd.read_sql(q, conn)
    print(df.to_string(index=False))

conn.close()
