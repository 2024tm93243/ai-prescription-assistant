# Dockerfile for Drug Info Service
FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared module
COPY shared/ ./shared/

# Copy service code
COPY drug_info_service/ ./drug_info_service/

WORKDIR /app/drug_info_service

EXPOSE 8003

CMD ["python", "main.py"]
