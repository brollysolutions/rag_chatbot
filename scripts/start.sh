#!/bin/bash
set -e

echo "🚀 Starting Digital Brolly Assistant setup..."

echo "🔍 Checking Cache Collection..."
python init_cache.py

echo "📄 Running Document Ingestion..."
python ingestion.py

echo "✅ Setup complete. Launching FastAPI..."

exec uvicorn app.main:app \
     --host 0.0.0.0 \
     --port 8080 \
     --workers 2 \
     --proxy-headers \
     --forwarded-allow-ips "*" \
     --timeout-keep-alive 30 \
     --log-level warning \
     --no-access-log