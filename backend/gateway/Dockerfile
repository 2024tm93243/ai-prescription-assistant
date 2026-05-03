# Base Dockerfile for Python microservices
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for OpenCV and PDF processing
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared module
COPY shared/ ./shared/

# Copy service code (will be overridden by specific Dockerfile)
COPY gateway/ ./gateway/

WORKDIR /app/gateway

CMD ["python", "main.py"]
