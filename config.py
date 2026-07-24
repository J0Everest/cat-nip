"""
Centralized application configuration — all os.getenv calls live here.
Other modules should import from this module, not call os.getenv directly.
"""
import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).parent
ASSETS_DIR = APP_DIR / "assets"
WORKBOOK_PATH = ASSETS_DIR / "Winter Storm Fern - Waterfall v2.xlsm"

# ── Database — primary server ──────────────────────────────────────────────────
DB_SERVER = os.getenv("DB_SERVER_CURRENT") or os.getenv("DB_SERVER", "ERRSACTDBP1")
DB_CATACCUM_DATABASE = os.getenv("DB_CATACCUM_DATABASE", "CatAccum2604")
DB_CATAPULT_DATABASE = os.getenv("DB_DATABASE", "Catapult")

# ── Database — cross-database references ───────────────────────────────────────
# TODO(databricks): Cross-DB SQL references ([AIREvents2025_TS13].[dbo].[Table])
#   are SQL Server-specific. On Databricks, replace with Unity Catalog three-part
#   names (catalog.schema.table) and separate connections per database.
AIR_EVENTS_DB = os.getenv("AIR_EVENTS_DB", "AIREvents2025_TS13")
INDUSTRY_DB = os.getenv("INDUSTRY_DB", "Industry")

# ── Authentication ─────────────────────────────────────────────────────────────
# DB_AUTH_MODE: "windows" (Kerberos/NTLM) | "sql" (username + password)
# TODO(databricks): "windows" auth is unavailable on Databricks Linux clusters.
#   Set DB_AUTH_MODE=sql and provision a SQL login (or use managed identity +
#   token-based auth via the JDBC connector) before cluster deployment.
DB_AUTH_MODE = os.getenv("DB_AUTH_MODE", "windows").lower()
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_PORT = int(os.getenv("DB_PORT", "1433"))

# ── Connection options ─────────────────────────────────────────────────────────
# TODO(databricks): Enable TLS — set DB_ENCRYPT=true for external SQL Server
#   connections from Databricks (VPN/private endpoint may also be required).
DB_ENCRYPT = os.getenv("DB_ENCRYPT", "false").lower() == "true"
DB_TRUST_SERVER_CERT = os.getenv("DB_TRUST_SERVER_CERT", "false").lower() == "true"
DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "30"))

# ── ODBC driver ────────────────────────────────────────────────────────────────
# TODO(databricks): Install MS ODBC driver 18 on Databricks via cluster init
#   script, or override ODBC_DRIVER to use driver 17 if already present.
#   Alternative: switch to pymssql (pure-Python, no ODBC layer needed).
ODBC_DRIVER = os.getenv("ODBC_DRIVER", "ODBC Driver 18 for SQL Server")

# ── Application ────────────────────────────────────────────────────────────────
APP_PORT = int(os.getenv("PORT", "8501"))
