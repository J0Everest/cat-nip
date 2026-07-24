"""
Shared database connection helpers — imported by all pages.
Settings are stored in st.session_state so they persist across page switches.
"""
import re
import pandas as pd
import pyodbc
import streamlit as st

from config import (
    DB_SERVER,
    DB_CATACCUM_DATABASE,
    DB_AUTH_MODE,
    DB_USER,
    DB_PASSWORD,
    DB_PORT,
    DB_ENCRYPT,
    DB_TRUST_SERVER_CERT,
    DB_CONNECT_TIMEOUT,
    ODBC_DRIVER,
)

DEFAULT_SERVER = DB_SERVER
DEFAULT_DATABASE = DB_CATACCUM_DATABASE


def init_db_state():
    """Call once per page to ensure session_state keys exist."""
    if "sql_server" not in st.session_state:
        st.session_state.sql_server = DEFAULT_SERVER
    if "sql_database" not in st.session_state:
        st.session_state.sql_database = DEFAULT_DATABASE


def next_quarter(db_name: str) -> str:
    m = re.match(r"^(.*?)(\d{2})(\d{2})$", str(db_name).strip())
    if not m:
        return db_name
    prefix, yy_raw, mm_raw = m.groups()
    yy, mm = int(yy_raw), int(mm_raw)
    mm += 3
    if mm > 12:
        mm -= 12
        yy = (yy + 1) % 100
    return f"{prefix}{yy:02d}{mm:02d}"


def conn_str(server: str, database: str) -> str:
    """Build an ODBC connection string for the configured auth mode.

    DB_AUTH_MODE=windows  — Kerberos/NTLM (local/domain Windows only)
    DB_AUTH_MODE=sql      — SQL login via DB_USER / DB_PASSWORD
    """
    encrypt = "Yes" if DB_ENCRYPT else "No"
    trust = "Yes" if DB_TRUST_SERVER_CERT else "No"
    base = (
        f"Driver={{{ODBC_DRIVER}}};"
        f"Server={server},{DB_PORT};Database={database};"
        f"Encrypt={encrypt};TrustServerCertificate={trust};"
        "Persist Security Info=False;Pooling=False;"
        "MultipleActiveResultSets=False;"
        f"Packet Size=4096;Connection Timeout={DB_CONNECT_TIMEOUT};"
    )
    if DB_AUTH_MODE == "sql":
        return base + f"UID={DB_USER};PWD={DB_PASSWORD};"
    # Default: Windows Integrated Security (Kerberos/NTLM)
    # TODO(databricks): Windows auth is unavailable on Linux clusters.
    #   Switch to DB_AUTH_MODE=sql before Databricks deployment.
    return base + "Trusted_Connection=Yes;"


def run_sql(server: str, database: str, query: str, params=()):
    with pyodbc.connect(conn_str(server, database)) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)

        # Some pages send multi-statement batches (temp tables + final SELECT).
        # Move through non-query statements until we reach a result set.
        while cursor.description is None:
            if not cursor.nextset():
                return pd.DataFrame()

        rows = cursor.fetchall()
        cols = [c[0] for c in cursor.description]
        return pd.DataFrame.from_records(rows, columns=cols)
