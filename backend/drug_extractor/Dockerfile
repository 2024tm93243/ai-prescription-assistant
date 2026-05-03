# Dockerfile for Drug Extractor Service
FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared module
COPY shared/ ./shared/

# Copy service code
COPY drug_extractor/ ./drug_extractor/

WORKDIR /app/drug_extractor

EXPOSE 8002

CMD ["python", "main.py"]
