#!/bin/bash

# Start all backend services for local development
# Run from the backend directory

echo "Starting Prescription Reader Backend Services..."
echo "================================================"

# Check if LM Studio is running
echo "Checking LM Studio..."
curl -s http://localhost:1234/v1/models > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "WARNING: LM Studio is not running at http://localhost:1234"
    echo "Please start LM Studio before using Drug Info Service"
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Start services in background
echo ""
echo "Starting OCR Service (Port 8001)..."
python -m ocr_service.main &
OCR_PID=$!

echo "Starting Drug Extractor Service (Port 8002)..."
python -m drug_extractor.main &
EXTRACTOR_PID=$!

echo "Starting Drug Info Service (Port 8003)..."
python -m drug_info_service.main &
INFO_PID=$!

echo "Starting Audit Service (Port 8004)..."
python -m audit_service.main &
AUDIT_PID=$!

sleep 2

echo "Starting API Gateway (Port 8000)..."
python -m gateway.main &
GATEWAY_PID=$!

echo ""
echo "================================================"
echo "All services started!"
echo ""
echo "Service URLs:"
echo "  - Gateway:       http://localhost:8000"
echo "  - OCR Service:   http://localhost:8001"
echo "  - Extractor:     http://localhost:8002"
echo "  - Drug Info:     http://localhost:8003"
echo "  - Audit:         http://localhost:8004"
echo ""
echo "API Documentation: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for all background processes
trap "kill $OCR_PID $EXTRACTOR_PID $INFO_PID $AUDIT_PID $GATEWAY_PID 2>/dev/null" EXIT
wait
