# 💊 Prescription Understanding & Patient Education Assistant

> An AI-powered web application that extracts medication information from prescription images and provides educational content about drugs, including OTC recommendations for managing side effects.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)

---

## ⚠️ Important Disclaimer

**THIS IS AN EDUCATIONAL PROTOTYPE - NOT FOR CLINICAL USE**

This application is developed as an academic project for educational purposes only. It does not provide medical advice, diagnosis, or treatment recommendations. Always consult qualified healthcare professionals for medical decisions.

---

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Development Setup](#local-development-setup)
  - [Environment Configuration](#environment-configuration)
- [Deployment](#deployment)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## ✨ Features

### Core Functionality
- 📸 **Prescription Image Upload**: Drag-and-drop or click to upload prescription images (JPG, PNG)
- 🔍 **OCR Text Extraction**: Extracts text from both printed and handwritten prescriptions using EasyOCR
- 💊 **Drug Name Identification**: Intelligent fuzzy matching against database of 80+ common medications
- 📊 **Confidence Scoring**: HIGH (≥85%), MEDIUM (60-85%), LOW (<60%) confidence levels
- ✅ **User Confirmation**: Low-confidence extractions require user verification
- 📚 **Educational Information**: AI-generated content for each medication:
  - General uses and indications
  - Common side effects
  - Safety warnings and precautions
  - OTC recommendations for managing side effects
- 💬 **Chat Interface**: Direct drug queries via natural language chat
- 📱 **Responsive Design**: Works on desktop, tablet, and mobile devices

### Technical Features
- 🏗️ **Microservices Architecture**: 5 independent services (Gateway, OCR, Extractor, DrugInfo, Audit)
- 🤖 **LLM Provider Flexibility**: Switch between Groq Cloud LLM and LM Studio (local)
- 🔐 **Privacy-First Design**: No PHI storage, immediate image deletion, audit logging without sensitive data
- 🚀 **Fast Inference**: Sub-second LLM responses using Groq's infrastructure
- 🎯 **Clean Configuration**: Environment-based settings with validation
- ❤️ **Health Monitoring**: Built-in health check endpoints for all services

---

## 🏗️ Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────┐
│                     Client (Web Browser)                      │
└───────────────────────────┬──────────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │ React Frontend │
                    │  (Port 3000)   │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │  API Gateway   │
                    │  (Port 8000)   │
                    └───────┬────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼─────┐      ┌─────▼──────┐     ┌─────▼──────┐
   │   OCR    │      │   Drug     │     │    Drug    │
   │ Service  │──────│ Extractor  │─────│    Info    │
   │(Pt 8001) │      │ (Pt 8002)  │     │ (Pt 8003)  │
   └──────────┘      └────────────┘     └─────┬──────┘
                                               │
                                          ┌────▼─────┐
                                          │ Groq API │
                                          │ (Cloud)  │
                                          └──────────┘
```

### Service Responsibilities

| Service | Port | Purpose |
|---------|------|---------|
| **API Gateway** | 8000 | Request routing, CORS, response aggregation |
| **OCR Service** | 8001 | Image-to-text extraction (EasyOCR) |
| **Drug Extractor** | 8002 | Drug name parsing, fuzzy matching, confidence scoring |
| **Drug Info Service** | 8003 | LLM-based educational content generation |
| **Audit Service** | 8004 | Privacy-preserving logging |

---

## 🛠️ Technology Stack

### Frontend
- **React** 18 - Modern UI library
- **Axios** - HTTP client
- **react-dropzone** - File upload component
- **CSS3** - Responsive styling with flexbox/grid

### Backend
- **FastAPI** - High-performance Python web framework
- **Pydantic** - Data validation and settings management
- **EasyOCR** - OCR engine (CPU mode)
- **httpx** - Async HTTP client for microservices
- **Levenshtein** - Fuzzy string matching

### AI/LLM
- **Groq Cloud** - Production LLM provider (llama-3.3-70b-versatile)
- **LM Studio** - Local development LLM option

### Deployment
- **Render.com** - Cloud platform (free tier)
- **Uvicorn** - ASGI server
- **GitHub** - Version control and CI/CD trigger

---

## 🚀 Getting Started

### Prerequisites

**System Requirements:**
- Python 3.9 or higher
- Node.js 16+ and npm
- 4GB+ RAM (for OCR model)
- macOS, Linux, or Windows

**External Services:**
- Groq API account and API key (free tier available)
- GitHub account (for deployment)

### Local Development Setup

#### 1. Clone Repository

```bash
git clone https://github.com/yourusername/prescription-reader.git
cd prescription-reader
```

#### 2. Backend Setup

```bash
# Create virtual environment
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Edit .env and add your Groq API key
nano .env  # or use your preferred editor
```

**Required environment variables in `backend/.env`:**
```bash
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
```

#### 3. Frontend Setup

```bash
cd ../frontend
npm install

# Create environment file
cp .env.example .env

# For local development, leave REACT_APP_API_URL empty (uses proxy)
```

#### 4. Start All Services

**Option A: Using the startup script (recommended)**
```bash
cd backend
chmod +x start.sh
./start.sh
```

**Option B: Start each service manually**

Open 5 separate terminal windows:

```bash
# Terminal 1 - OCR Service
cd backend
source venv/bin/activate
python -m uvicorn ocr_service.main:app --port 8001

# Terminal 2 - Drug Extractor
cd backend
source venv/bin/activate
python -m uvicorn drug_extractor.main:app --port 8002

# Terminal 3 - Drug Info Service
cd backend
source venv/bin/activate
python -m uvicorn drug_info_service.main:app --port 8003

# Terminal 4 - Audit Service
cd backend
source venv/bin/activate
python -m uvicorn audit_service.main:app --port 8004

# Terminal 5 - API Gateway
cd backend
source venv/bin/activate
python -m uvicorn gateway.main:app --port 8000
```

#### 5. Start Frontend

```bash
cd frontend
npm start
```

Frontend will open at http://localhost:3000

#### 6. Verify Installation

```bash
# Test backend health
curl http://localhost:8000/health

# Expected: {"service":"API Gateway","status":"healthy"}

# Test LLM provider
curl http://localhost:8000/health/llm

# Expected: {"llm_provider":"groq","llm_status":"available"}
```

### Environment Configuration

#### Backend Environment Variables

Create `backend/.env` with these settings:

```bash
# ============================================
# LLM Provider Configuration
# ============================================
LLM_PROVIDER=groq              # Options: groq, lmstudio
GROQ_API_KEY=your_key_here     # Get from console.groq.com
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_BASE_URL=https://api.groq.com/openai/v1

# ============================================
# Service Configuration
# ============================================
GATEWAY_PORT=8000
OCR_SERVICE_PORT=8001
DRUG_EXTRACTOR_PORT=8002
DRUG_INFO_SERVICE_PORT=8003
AUDIT_SERVICE_PORT=8004

OCR_SERVICE_URL=http://localhost:8001
DRUG_EXTRACTOR_URL=http://localhost:8002
DRUG_INFO_SERVICE_URL=http://localhost:8003
AUDIT_SERVICE_URL=http://localhost:8004

# ============================================
# OCR Settings
# ============================================
OCR_USE_GPU=false
OCR_LANGUAGES=["en"]

# ============================================
# Confidence Thresholds
# ============================================
CONFIDENCE_HIGH_THRESHOLD=0.85
CONFIDENCE_MEDIUM_THRESHOLD=0.60

# ============================================
# CORS Configuration
# ============================================
CORS_ORIGINS=["http://localhost:3000"]

# ============================================
# File Handling
# ============================================
MAX_FILE_SIZE_MB=10
UPLOAD_DIR=/tmp/uploads
IMAGE_RETENTION_HOURS=1
```

#### Frontend Environment Variables

Create `frontend/.env`:

```bash
# Leave empty for local development (uses proxy)
REACT_APP_API_URL=

# Set to 'production' to show disclaimer banner
REACT_APP_ENV=development
```

---

## 🚀 Deployment

### Deploy to Render.com (Free Tier)

Follow the comprehensive deployment guide:

📖 **[RENDER_DEPLOYMENT_GUIDE.md](./RENDER_DEPLOYMENT_GUIDE.md)** - Complete step-by-step instructions

📋 **[DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)** - Interactive checklist

### Quick Deployment Steps

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **Deploy Backend to Render**
   - Create Web Service
   - Build command: `pip install -r backend/requirements.txt`
   - Start command: `cd backend && chmod +x start.sh && ./start.sh`
   - Add environment variables (especially `GROQ_API_KEY`)

3. **Deploy Frontend to Render**
   - Create Static Site
   - Build command: `cd frontend && npm install && npm run build`
   - Publish directory: `frontend/build`
   - Set `REACT_APP_API_URL` to backend URL

4. **Update CORS**
   - Add frontend URL to backend's `CORS_ORIGINS`

5. **Test Deployment**
   - Visit frontend URL
   - Upload prescription or query drug
   - Verify all features work

**Estimated deployment time**: 15-20 minutes

---

## 📖 Usage

### 1. Direct Drug Query

1. Open the application
2. Type a drug name in the chat input (e.g., "Ibuprofen")
3. Press Enter
4. View educational information in the panel below

### 2. Prescription Upload

1. Click "Choose File" or drag-and-drop a prescription image
2. Wait for OCR processing (30-90 seconds)
3. Review extracted drug names with confidence scores
4. For low-confidence drugs, type the correct name when prompted
5. View detailed information for each medication

### 3. OTC Recommendations

1. After drug information loads, scroll to "Managing Side Effects"
2. Review OTC options for each side effect
3. Read caution messages carefully
4. Always consult healthcare provider before using OTC medications

---

## 📚 API Documentation

### Health Check Endpoints

#### GET /health
Check gateway service status

**Response:**
```json
{
  "service": "API Gateway",
  "status": "healthy",
  "version": "1.0.0"
}
```

#### GET /health/llm
Check LLM provider status

**Response:**
```json
{
  "service": "drug_info",
  "llm_provider": "groq",
  "llm_status": "available",
  "llm_config": {
    "provider": "groq",
    "model": "llama-3.3-70b-versatile",
    "api_key": "***REDACTED***"
  }
}
```

### Drug Information Endpoints

#### POST /api/upload-prescription
Upload and process prescription image

**Request:**
- Content-Type: multipart/form-data
- Body: `file` (image file, max 10MB)

**Response:**
```json
{
  "prescription_id": "uuid",
  "medications": [
    {
      "drug_id": "uuid",
      "drug_name": "Paracetamol",
      "confidence": 0.92,
      "confidence_level": "HIGH",
      "dosage": "500mg",
      "frequency": "Twice daily"
    }
  ]
}
```

#### GET /api/drug-info/{drug_name}
Get educational information for a drug

**Response:**
```json
{
  "drug_name": "Ibuprofen",
  "uses": "Pain relief, fever reduction, anti-inflammatory",
  "side_effects": ["Nausea", "Heartburn", "Dizziness"],
  "warnings": ["Do not exceed recommended dose"],
  "otc_for_side_effects": [
    {
      "side_effect": "Nausea",
      "otc_options": ["Ginger tea", "Vitamin B6"],
      "caution": "If nausea persists, consult your doctor"
    }
  ],
  "disclaimer": "This information is for educational purposes only...",
  "otc_disclaimer": "Always consult your healthcare provider..."
}
```

---

## 🤝 Contributing

This is an academic project. For suggestions or issues:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -m 'Add improvement'`)
4. Push to branch (`git push origin feature/improvement`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

### Technologies Used
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://reactjs.org/) - Frontend library
- [EasyOCR](https://github.com/JaidedAI/EasyOCR) - OCR engine
- [Groq](https://groq.com/) - Cloud LLM inference platform
- [Render](https://render.com/) - Deployment platform

### Inspiration
This project was inspired by the need for accessible patient education tools and the potential of AI to democratize healthcare information.

### Academic Context
Developed as part of M.Tech final project.

---

## 📞 Support & Contact

For questions or issues:
- **GitHub Issues**: Create an issue in this repository

---

## 🔮 Future Enhancements (Roadmap)

- [ ] **RAG Integration**: Retrieval-augmented generation with drug databases
- [ ] **Multi-Language Support**: Support for regional language prescriptions
- [ ] **Drug Interaction Checker**: Detect potential interactions between medications
- [ ] **Mobile App**: Native iOS/Android applications
- [ ] **Enhanced OCR**: Deep learning models for better handwriting recognition
- [ ] **Voice Interface**: Voice-based drug queries
- [ ] **Personalization**: User profiles with medication history
- [ ] **Telemedicine Integration**: Connect with healthcare providers

---

<div align="center">

**Made with ❤️ for improving healthcare accessibility**

⭐ Star this repository if you find it helpful!

</div>
