# Dockerfile for Audit Service
FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared module
COPY shared/ ./shared/

# Copy service code
COPY audit_service/ ./audit_service/

WORKDIR /app/audit_service

EXPOSE 8004

CMD ["python", "main.py"]
