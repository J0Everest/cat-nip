"""
Pre-flight configuration validator.
Run before deploying: python validate_config.py
Exits 0 on success, 1 on failure.
"""
import sys
import os

errors = []
warnings = []

# ── Load .env if present (dev convenience) ─────────────────────────────────────
try:
    from pathlib import Path
    _env = Path(__file__).parent / ".env"
    if _env.exists():
        for line in _env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
except Exception as e:
    warnings.append(f".env load skipped: {e}")

import config  # noqa: E402 — must come after .env load

# ── 1. Required env vars ────────────────────────────────────────────────────────
REQUIRED = {
    "DB_SERVER_CURRENT": config.DB_SERVER,
    "DB_CATACCUM_DATABASE": config.DB_CATACCUM_DATABASE,
}
for name, val in REQUIRED.items():
    if not val:
        errors.append(f"MISSING: {name} is empty")

# ── 2. Auth-mode-specific checks ───────────────────────────────────────────────
if config.DB_AUTH_MODE == "sql":
    if not config.DB_USER:
        errors.append("DB_AUTH_MODE=sql but DB_USER is empty")
    if not config.DB_PASSWORD:
        errors.append("DB_AUTH_MODE=sql but DB_PASSWORD is empty")
elif config.DB_AUTH_MODE == "windows":
    warnings.append(
        "DB_AUTH_MODE=windows — Kerberos/NTLM auth will fail on Linux/Databricks. "
        "Set DB_AUTH_MODE=sql for non-domain environments."
    )
else:
    errors.append(f"DB_AUTH_MODE='{config.DB_AUTH_MODE}' is invalid; must be 'windows' or 'sql'")

# ── 3. Quarterly DB naming convention ──────────────────────────────────────────
import re
if not re.match(r"^.*\d{4}$", config.DB_CATACCUM_DATABASE):
    warnings.append(
        f"DB_CATACCUM_DATABASE='{config.DB_CATACCUM_DATABASE}' does not end in YYMM "
        f"(expected e.g. CatAccum2604). The Next Quarter button depends on this pattern."
    )

# ── 4. Cross-DB references populated ──────────────────────────────────────────
for name, val in [("AIR_EVENTS_DB", config.AIR_EVENTS_DB), ("INDUSTRY_DB", config.INDUSTRY_DB)]:
    if not val:
        errors.append(f"MISSING: {name} is empty")

# ── 5. Workbook path exists (dev only) ─────────────────────────────────────────
if not config.WORKBOOK_PATH.exists():
    warnings.append(
        f"WORKBOOK_PATH not found: {config.WORKBOOK_PATH} "
        f"(required only for _dump_sql_sheet.py and _inspect_workbook.py)"
    )

# ── 6. Optional connectivity probe ─────────────────────────────────────────────
SKIP_PROBE = os.getenv("SKIP_DB_PROBE", "").lower() in ("1", "true", "yes")
if not SKIP_PROBE:
    try:
        import pyodbc
        cs = config.DB_AUTH_MODE
        test_str = (
            f"Driver={{{config.ODBC_DRIVER}}};"
            f"Server={config.DB_SERVER},1433;"
            f"Database={config.DB_CATACCUM_DATABASE};"
            + ("Trusted_Connection=Yes;" if cs == "windows"
               else f"UID={config.DB_USER};PWD={config.DB_PASSWORD};")
            + "Connection Timeout=5;"
        )
        with pyodbc.connect(test_str, timeout=5) as conn:
            conn.cursor().execute("SELECT 1")
        print(f"  [OK] DB connection: {config.DB_SERVER}/{config.DB_CATACCUM_DATABASE}")
    except Exception as e:
        warnings.append(f"DB probe failed (set SKIP_DB_PROBE=1 to suppress): {e}")

# ── Report ──────────────────────────────────────────────────────────────────────
print("\n=== validate_config ===")
print(f"  DB_SERVER          : {config.DB_SERVER}")
print(f"  DB_CATACCUM_DATABASE: {config.DB_CATACCUM_DATABASE}")
print(f"  DB_AUTH_MODE       : {config.DB_AUTH_MODE}")
print(f"  AIR_EVENTS_DB      : {config.AIR_EVENTS_DB}")
print(f"  INDUSTRY_DB        : {config.INDUSTRY_DB}")
print(f"  ODBC_DRIVER        : {config.ODBC_DRIVER}")

if warnings:
    print("\nWARNINGS:")
    for w in warnings:
        print(f"  ! {w}")

if errors:
    print("\nERRORS:")
    for e in errors:
        print(f"  x {e}")
    print("\nFAILED — fix errors above before deploying.")
    sys.exit(1)

print("\nOK — configuration is valid.")
sys.exit(0)
