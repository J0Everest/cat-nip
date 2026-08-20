import re
import pandas as pd

try:
    import pyodbc
except Exception:
    pyodbc = None

try:
    import pymssql
except Exception:
    pymssql = None

from django.conf import settings


def get_connection_string(server: str, database: str) -> str:
    encrypt = "Yes" if settings.DB_ENCRYPT else "No"
    trust = "Yes" if settings.DB_TRUST_SERVER_CERT else "No"
    base = (
        f"Driver={{{settings.ODBC_DRIVER}}};"
        f"Server={server},{settings.DB_PORT};Database={database};"
        f"Encrypt={encrypt};TrustServerCertificate={trust};"
        "Persist Security Info=False;Pooling=False;"
        "MultipleActiveResultSets=False;"
        f"Packet Size=4096;Connection Timeout={settings.DB_CONNECT_TIMEOUT};"
    )
    if settings.DB_AUTH_MODE == "sql":
        return base + f"UID={settings.DB_USER};PWD={settings.DB_PASSWORD};"
    return base + "Trusted_Connection=Yes;"


def run_sql(server: str, database: str, query: str, params=()) -> pd.DataFrame:
    if pyodbc is not None:
        with pyodbc.connect(get_connection_string(server, database)) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            while cursor.description is None:
                if not cursor.nextset():
                    return pd.DataFrame()
            rows = cursor.fetchall()
            cols = [c[0] for c in cursor.description]
            return pd.DataFrame.from_records(rows, columns=cols)

    if pymssql is not None:
        if settings.DB_AUTH_MODE != "sql":
            raise RuntimeError(
                "pyodbc is unavailable and DB_AUTH_MODE is not 'sql'. "
                "Use DB_AUTH_MODE=sql when running without ODBC libraries."
            )
        with pymssql.connect(
            server=server,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=database,
            port=settings.DB_PORT,
            login_timeout=settings.DB_CONNECT_TIMEOUT,
            timeout=settings.DB_CONNECT_TIMEOUT,
        ) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            while cursor.description is None:
                if not cursor.nextset():
                    return pd.DataFrame()
            rows = cursor.fetchall()
            cols = [c[0] for c in cursor.description]
            return pd.DataFrame.from_records(rows, columns=cols)

    raise RuntimeError(
        "No SQL driver available: pyodbc failed to load and pymssql is not installed."
    )
