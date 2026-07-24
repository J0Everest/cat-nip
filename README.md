# Everest Cat Scenario Explorer (SQL-backed)

This turns your static dashboard into a real web app backed by SQL Server.

## 1) Create DB/table/sample data
Run [sql/schema.sql](sql/schema.sql) in SQL Server Management Studio.

## 2) Configure environment
Copy `.env.example` to `.env` and set credentials.

### Windows Integrated Security (your setup)
Use these values in `.env`:
- `DB_AUTH_MODE=windows`
- `DB_INTEGRATED_SECURITY=true`
- `DB_SERVER_CURRENT=ERRSACTDBP1`
- `DB_CATACCUM_DATABASE=CatAccum2604`
- `DB_ENCRYPT=false`
- `DB_TRUST_SERVER_CERT=false`

Quarterly CatAccum roll-forward: update **one** value only:
- `DB_CATACCUM_DATABASE=CatAccumYYMM` (example: `CatAccum2604` → `CatAccum2607`)

## 3) Install and run
```bash
npm install
npm run dev
```

Open: http://localhost:3000

## API
- `GET /api/health`
- `GET /api/placements`
- `POST /api/copilot/ask`

## Notes
- Frontend is in [public/index.html](public/index.html) and [public/app.js](public/app.js).
- Data is loaded from SQL on page load.
- Set `DB_CATACCUM_DATABASE=CatAccum` (or your CatAccum DB name) in `.env` for Copilot peril/region impact questions.
- For Windows Integrated Security, ensure the app runs under a Windows account with read access to CatAccum tables.
