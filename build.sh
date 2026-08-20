#!/usr/bin/env bash
set -euo pipefail

echo "=== Building Angular client ==="
cd client
npm ci
npx ng build --configuration=production
cd ..

echo "=== Collecting Django static files ==="
python manage.py collectstatic --noinput

echo "=== Build complete ==="
echo "Run:  python manage.py runserver"
