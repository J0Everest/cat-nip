# Databricks Migration Plan — Cat Scenario Explorer

**App:** Everest Cat Tools (Streamlit)  
**Current environment:** Windows developer workstation, ODBC to on-prem SQL Server  
**Target environment:** Databricks Apps (Serverless) with network access to ERRSACTDBP1

---

## 1. Architecture Mapping: Current → Databricks

| Layer | Current (local) | Target (Databricks) |
|---|---|---|
| **UI framework** | Streamlit (local `streamlit run`) | Streamlit (Databricks Apps runtime) |
| **Python runtime** | Local `.venv`, Python 3.x | Databricks Apps managed runtime |
| **Data access** | pyodbc → ODBC Driver 18 → SQL Server | pyodbc → ODBC Driver 18 (init script) → SQL Server, OR Databricks SQL connector |
| **Authentication** | Windows Integrated Security (Kerberos) | SQL login (`DB_AUTH_MODE=sql`) or managed identity |
| **Configuration** | `.env` file on disk | Databricks App environment variables (secrets via Databricks Secrets) |
| **Cross-DB queries** | `[AIREvents2025_TS13].[dbo].[Table]` syntax | Same syntax if SQL Server allows; OR Unity Catalog if data is mirrored |
| **Secrets** | `.env` (no passwords — Windows auth) | Databricks Secrets API (`dbutils.secrets.get`) |
| **File assets** | Local `assets/` directory | Bundle in app package; use DBFS for large outputs |
| **Deployment** | Manual `streamlit run app.py` | `databricks apps deploy` via CI pipeline |

---

## 2. Runtime / Dependency Substitutions

| Dependency | Local version | Databricks action |
|---|---|---|
| `pyodbc==5.1.0` | Works on Windows with system ODBC driver | Install ODBC Driver 18 via cluster/app init script (see Phase 1 below) |
| `ODBC Driver 18 for SQL Server` | Pre-installed on dev machine | Install in init script; OR switch to `pymssql` (no ODBC needed) |
| `streamlit==1.39.0` | Local package | Pin same version in `requirements.txt` (already done) |
| Windows Integrated Security | Kerberos/NTLM — domain-joined machine | Replace with SQL login (`DB_AUTH_MODE=sql`) or managed identity |
| `.env` file | Committed template, live file excluded | Databricks App environment variables; secrets via Databricks Secrets |
| Local `assets/` directory | Read directly from filesystem | Bundle with app deployment artifact |
| `analysis/air_event_descriptions_distinct.csv` (130 MB) | Checked-in output | Move to DBFS or Delta table; exclude from app package |

---

## 3. Phased Migration Runbook

### Phase 1 — Environment prep (dev, ~1 day)

**Goal:** Prove the app boots on a Linux Python environment.

1. Provision a Databricks workspace with Apps feature enabled.
2. Create a cluster init script to install ODBC Driver 18:
   ```bash
   #!/bin/bash
   curl -sSL https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
   curl -sSL https://packages.microsoft.com/config/ubuntu/22.04/prod.list \
     > /etc/apt/sources.list.d/mssql-release.list
   ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev
   ```
3. Set the following App environment variables (not secrets, no passwords yet):
   ```
   DB_SERVER_CURRENT=ERRSACTDBP1
   DB_CATACCUM_DATABASE=CatAccum2604
   AIR_EVENTS_DB=AIREvents2025_TS13
   INDUSTRY_DB=Industry
   DB_AUTH_MODE=sql
   ODBC_DRIVER=ODBC Driver 18 for SQL Server
   DB_ENCRYPT=true
   DB_TRUST_SERVER_CERT=true
   ```
4. Create a Databricks Secret scope `cat-tools` and add `DB_USER` and `DB_PASSWORD`.
5. Wire secrets into the App via the `env` section of `app.yaml`:
   ```yaml
   command: ["streamlit", "run", "app.py", "--server.port", "8080", "--server.headless", "true"]
   env:
     - name: DB_USER
       valueFrom:
         secretRef:
           name: cat-tools/db-user
     - name: DB_PASSWORD
       valueFrom:
         secretRef:
           name: cat-tools/db-password
   ```
6. Run `python validate_config.py` locally with `DB_AUTH_MODE=sql` to verify config.
7. Deploy: `databricks apps deploy --app cat-scenario-explorer`.

**Success criteria:** App loads, sidebar shows correct server/database, no Python import errors.

---

### Phase 2 — Network and SQL auth validation (dev, ~1 day)

**Goal:** Prove SQL Server connectivity from Databricks.

1. Confirm network path: Databricks cluster VPC → corporate network (VPN, private link, or peering).
2. Provision a SQL login on `ERRSACTDBP1` with SELECT on `CatAccum*`, `Industry`, `AIREvents*` databases.
3. Test connectivity from a Databricks notebook:
   ```python
   import pyodbc, os
   cs = (
       f"Driver={{ODBC Driver 18 for SQL Server}};"
       f"Server={os.environ['DB_SERVER_CURRENT']},1433;"
       f"Database={os.environ['DB_CATACCUM_DATABASE']};"
       f"UID={os.environ['DB_USER']};PWD={os.environ['DB_PASSWORD']};"
       "Encrypt=Yes;TrustServerCertificate=Yes;Connection Timeout=10;"
   )
   conn = pyodbc.connect(cs)
   print(conn.cursor().execute("SELECT 1").fetchone())
   ```
4. Once notebook test passes, redeploy the App and exercise Event Response with a real query.
5. Validate cross-database SQL queries: `[Industry].[dbo].[Industry_Unadjusted_V21_ZonePercent]` and `[AIREvents2025_TS13].[dbo].[...]`.

   > **Assumption:** SQL Server on `ERRSACTDBP1` allows cross-database access from the SQL login. If not, restructure queries to use separate connections per database (create a `run_sql_db(db, query, params)` wrapper in `_db.py`).

**Success criteria:** Event Response waterfall completes with live data, no connection errors.

---

### Phase 3 — Secrets hardening and CI (test, ~1 day)

**Goal:** Remove all plaintext config from the codebase; automate deployment.

1. Remove `.env` from the repository entirely (already in `.gitignore`).
2. Move `DB_SERVER_CURRENT` and `DB_CATACCUM_DATABASE` into Databricks Secrets (these are not passwords but they are environment-specific).
3. Add a GitHub Actions (or Azure DevOps) pipeline:
   ```yaml
   # .github/workflows/deploy.yml
   - name: Deploy to Databricks
     run: |
       pip install databricks-cli
       databricks apps deploy --app cat-scenario-explorer
     env:
       DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
       DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
   ```
4. Add pre-deploy step: `python validate_config.py` with `SKIP_DB_PROBE=1` (CI can't reach SQL Server).
5. Pin `requirements.txt` versions (already done for all Python deps).

**Success criteria:** Successful deploy from CI pipeline with no manual steps.

---

### Phase 4 — Production cutover (prod, ~0.5 day)

**Goal:** Route internal users to the Databricks-hosted app.

1. Update prod Databricks App env vars to point at production SQL Server and `CatAccum` database for current quarter.
2. Smoke test with production data:
   - [ ] App loads without errors
   - [ ] Sidebar shows correct server/database
   - [ ] Event Response: search returns results
   - [ ] Waterfall renders gross/net/ceded breakdown
   - [ ] "Next Quarter" button increments database name correctly
3. Communicate URL to the Cat actuarial team.
4. Keep local `streamlit run` working as fallback (local dev) — it still works with `.env`.

---

## 4. Pre-Migration Checklist

- [ ] `python validate_config.py` passes locally with `DB_AUTH_MODE=sql`
- [ ] SQL login created on ERRSACTDBP1 with required permissions
- [ ] Network path from Databricks VPC to ERRSACTDBP1 confirmed (ping / sqlcmd test)
- [ ] ODBC Driver 18 installs successfully on Databricks via init script
- [ ] Databricks Secret scope `cat-tools` exists with `db-user` and `db-password`
- [ ] `requirements.txt` pinned and tested (`pip install -r requirements.txt` on Linux)
- [ ] `analysis/air_event_descriptions_distinct.csv` excluded from app deploy artifact (130 MB)
- [ ] `.env` excluded from git (`.gitignore` in place)

---

## 5. Post-Migration Checklist

- [ ] App URL is accessible to intended users (SSO / Databricks workspace auth)
- [ ] Event Response completes a full waterfall query in under 30 seconds
- [ ] Cross-database queries (`[Industry]`, `[AIREvents2025_TS13]`) return results
- [ ] "Next Quarter" button advances `DB_CATACCUM_DATABASE` in session state
- [ ] No hardcoded `ERRSACTDBP1` references remain in active code paths
- [ ] CI pipeline deploys successfully on push to `main`
- [ ] Runbook shared with Cat actuarial team and IT operations

---

## 6. Known Risks and Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Windows Integrated Security unavailable on Linux | Critical | Switch to SQL login (`DB_AUTH_MODE=sql`); provision dedicated SQL account |
| ODBC Driver 18 not available on Databricks image | High | Install via cluster init script; fallback: switch to `pymssql` (pure Python) |
| Cross-DB SQL syntax fails with SQL login (permissions) | High | Grant SQL login cross-database SELECT; or refactor to separate pyodbc connections per DB |
| Network path from Databricks to ERRSACTDBP1 blocked | High | Work with IT to establish VPN tunnel or private endpoint before Phase 2 |
| Quarterly DB name change (`CatAccum2604 → 2607`) requires env update | Medium | Update Databricks App env var each quarter; automate with a CI job or Databricks job |
| `analysis/air_event_descriptions_distinct.csv` (130 MB) in git | Medium | Added to `.gitignore`; move artifact to DBFS or regenerate on demand |
| `pages_legacy/` and `views/1_Scenario_Explorer.py` orphaned | Low | Dead code; safe to delete after confirming not needed |
| `event_response_mockup.py` not wired to any page | Low | Safe to delete or wire as a stub page |

---

## 7. Remaining Gaps and Next Actions

| Gap | Priority | Owner | Action |
|---|---|---|---|
| SQL login provisioned on ERRSACTDBP1 | Critical | IT / DBA | Create login with SELECT on `CatAccum*`, `Industry`, `AIREvents*`; test with `validate_config.py` |
| Network path Databricks → ERRSACTDBP1 | Critical | IT / Network | Confirm VPN or private link; document latency |
| ODBC init script tested on Databricks | High | Engineering | Run Phase 1 step 2; confirm `odbcinst -q -d` shows driver |
| `app.yaml` for Databricks Apps | High | Engineering | Write and commit `app.yaml` with secrets wiring (template in Phase 1) |
| CI pipeline for `databricks apps deploy` | High | Engineering | Add `.github/workflows/deploy.yml`; add `DATABRICKS_HOST`/`TOKEN` secrets to repo |
| Cross-DB query validation under SQL login | High | Engineering/DBA | Run Phase 2 notebook test; fix permissions if queries fail |
| Quarterly DB rotation — operational procedure | Medium | Cat Actuarial/IT | Document who updates `DB_CATACCUM_DATABASE` env var each quarter and how |
| Large CSV removal from git history | Medium | Engineering | `git filter-repo --path analysis/air_event_descriptions_distinct.csv --invert-paths` |
| Remove `pages_legacy/` dead code | Low | Engineering | Delete after confirming no references in active pages |
| `event_response_mockup.py` disposition | Low | Product | Decide: delete, wire as page, or keep as design reference |
