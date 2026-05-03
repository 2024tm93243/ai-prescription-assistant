#!/bin/bash
# Startup script for Render deployment
# Launches all microservices in a single web service

set -e  # Exit on error

echo "🚀 Starting Prescription Reader Backend Services..."

# Get port from Render (or default to 8000)
PORT="${PORT:-8000}"

echo "📝 Configuration:"
echo "   Port: $PORT"
echo "   LLM Provider: ${LLM_PROVIDER:-not set}"
echo "   Environment: ${APP_ENV:-dev}"

# Create upload directory
mkdir -p /tmp/uploads
echo "✅ Created /tmp/uploads directory"

# Start microservices in background
echo "🔧 Starting OCR Service (port 8001)..."
PYTHONPATH=$PWD python3 -m uvicorn ocr_service.main:app \
  --host 0.0.0.0 --port 8001 --log-level warning &

echo "🔧 Starting Drug Extractor Service (port 8002)..."
PYTHONPATH=$PWD python3 -m uvicorn drug_extractor.main:app \
  --host 0.0.0.0 --port 8002 --log-level warning &

echo "🔧 Starting Drug Info Service (port 8003)..."
PYTHONPATH=$PWD python3 -m uvicorn drug_info_service.main:app \
  --host 0.0.0.0 --port 8003 --log-level warning &

echo "🔧 Starting Audit Service (port 8004)..."
PYTHONPATH=$PWD python3 -m uvicorn audit_service.main:app \
  --host 0.0.0.0 --port 8004 --log-level warning &

# Wait for services to initialize
echo "⏳ Waiting for services to initialize (5 seconds)..."
sleep 5

# Start API Gateway in foreground (this keeps the container running)
echo "🚀 Starting API Gateway on port $PORT..."
PYTHONPATH=$PWD exec python3 -m uvicorn gateway.main:app \
  --host 0.0.0.0 --port $PORT --log-level info
