# CAT-NIP — Catastrophe Scenario Explorer

Django REST API + Angular SPA backed by SQL Server.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | [python.org](https://www.python.org/downloads/) — check "Add to PATH" during install |
| ODBC Driver 18 | [Microsoft download](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) — required for SQL Server connectivity |
| Network access | Must be on the Everest network or VPN to reach `ERRSACTDBP1` |

Node.js is **not required** — the Angular frontend is pre-built and committed to `static/angular/`.

---

## Setup

### 1. Clone and create virtual environment

```powershell
git clone https://github.com/J0Everest/cat-nip.git
cd cat-nip
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```powershell
copy .env.example .env
```

The defaults in `.env.example` work out of the box on the Everest domain (Windows Integrated Security, `ERRSACTDBP1`). Edit `.env` only if your setup differs:

| Variable | Default | Change if… |
|---|---|---|
| `DB_SERVER_CURRENT` | `ERRSACTDBP1` | Using a different SQL Server |
| `DB_CATACCUM_DATABASE` | `CatAccum2604` | New quarter — update to e.g. `CatAccum2607` |
| `AIR_EVENTS_DB` | `AIREvents2025_TS13` | AIR model year refreshed |
| `DB_AUTH_MODE` | `windows` | Running outside domain — set `sql` and fill `DB_USER`/`DB_PASSWORD` |

### 3. Initialize the database

```powershell
python manage.py migrate
```

This creates the local SQLite database used for saved scenarios.

### 4. Run

```powershell
python manage.py runserver
```

Open **http://localhost:8000**

---

## Quick start (PowerShell one-liner)

```powershell
.\run-app.ps1
```

---

## Quarterly database roll-forward

Update one line in `.env`:

```
DB_CATACCUM_DATABASE=CatAccum2607   # change YYMM to the new quarter
```

Or use the **Next Qtr** button in the sidebar — it auto-increments the database name and updates the active connection.

---

## Project structure

```
apps/
  core/          Django settings, health/config endpoints
  db/            SQL Server connection helpers (pyodbc + pymssql fallback)
  scenario/      Main app — parse, search, analyze, saved scenarios
client/          Angular source (TypeScript + Angular Material)
static/angular/  Pre-built Angular SPA (committed — no rebuild needed to run)
```

## Rebuilding the frontend (optional)

Only needed if you modify Angular source files under `client/src/`:

```powershell
cd client
npm install       # one-time
npx ng build
cd ..
```
