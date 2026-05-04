#!/bin/bash
set -e

echo "🚀 Starting Digital Brolly Assistant setup..."

# 1. Initialize Cache Collection
echo "🔍 Checking Cache Collection..."
python app/init_cache.py

# 2. Run Ingestion (Processes PDFs if they haven't been indexed)
# Note: Ensure your ingestion.py is idempotent (checks if data exists before uploading)
echo "📄 Running Document Ingestion..."
python app/ingestion.py

echo "✅ Setup complete. Launching FastAPI..."

# 3. Start the API
exec uvicorn app.main:app \
     --host 0.0.0.0 \
     --port 8080 \
     --workers 2 \
     --proxy-headers \
     --forwarded-allow-ips "*" \
     --timeout-keep-alive 30 \
     --log-level warning \
     --no-access-log