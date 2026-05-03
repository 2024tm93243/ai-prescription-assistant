# Prescription Understanding & Patient Education Assistant - Render Deployment Guide

**Document Version**: 1.0  
**Target Platform**: Render.com (Free Tier)  
**Project Type**: Academic Prototype (M.Tech)  
**Date**: May 3, 2026

---

## 1. Deployment Architecture Overview

This application follows a modern three-tier architecture optimized for Render's free tier deployment:

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                ┌─────────┴──────────┐
                │                    │
        ┌───────▼────────┐   ┌──────▼────────┐
        │  React Frontend│   │ Backend API   │
        │  (Static Site) │   │ (Web Service) │
        │  Render Static │   │ Render Web    │
        └───────┬────────┘   └──────┬────────┘
                │                    │
                └────────┬───────────┘
                         │
                    ┌────▼────────────────────┐
                    │  Backend Components     │
                    ├─────────────────────────┤
                    │ • API Gateway (FastAPI) │
                    │ • OCR Service (EasyOCR) │
                    │ • Drug Extractor        │
                    │ • Drug Info Service     │
                    │ • Audit Service         │
                    └────┬────────────────────┘
                         │
                    ┌────▼────────┐
                    │  Groq API   │
                    │  (External) │
                    └─────────────┘
```

### Key Design Principles

1. **Stateless Services**: No persistent storage required for prototype
2. **Environment-Based Configuration**: All provider selection via environment variables
3. **Single Groq API Key**: Shared across all sessions (not per-user)
4. **Microservices-in-Monolith**: All backend services run in single Render web service
5. **Free Tier Optimized**: Minimal resource usage, accepts cold starts

### Deployment Components

| Component | Render Service Type | Purpose |
|-----------|-------------------|---------|
| React UI | Static Site | User interface for prescription upload and chat |
| Backend API | Web Service | FastAPI gateway + all microservices |
| Groq LLM | External API | Cloud LLM provider for drug information |
| EasyOCR | Bundled Library | OCR processing within backend service |

---

## 2. Render Service Breakdown

### 2.1 Frontend (React Static Site)

**Service Configuration:**
- **Type**: Static Site
- **Build Command**: `cd frontend && npm install && npm run build`
- **Publish Directory**: `frontend/build`
- **Runtime**: Node.js (for build only)

**Responsibilities:**
- Serve React single-page application
- Handle file uploads (client-side validation)
- Display chat interface with drug information
- Show educational disclaimers and warnings
- Display OTC recommendations with cautions

**Environment Variables Required:**
```
REACT_APP_API_URL=https://your-backend.onrender.com
REACT_APP_ENV=production
```

**Build Process:**
1. Install npm dependencies
2. Build React production bundle with optimizations
3. Generate static HTML, CSS, JS files
4. Serve via Render's CDN

### 2.2 Backend (API + OCR + LLM)

**Service Configuration:**
- **Type**: Web Service (Free Tier)
- **Runtime**: Python 3.9+
- **Build Command**: `pip install -r backend/requirements.txt`
- **Start Command**: `cd backend && uvicorn gateway.main:app --host 0.0.0.0 --port $PORT`

**Responsibilities:**
- API Gateway: Route requests, CORS handling
- OCR Service: Extract text from prescription images using EasyOCR
- Drug Extractor: Parse OCR output, identify drugs, compute confidence scores
- Drug Info Service: Generate educational information via Groq LLM
- Audit Service: Privacy-preserving logging (no PHI retention)

**Key Features:**
- Multi-service architecture in single process (cost optimization)
- In-memory session storage (no database needed for prototype)
- Automatic LLM provider selection based on `LLM_PROVIDER` env variable
- Fail-fast configuration validation on startup
- Health check endpoints for monitoring

**Port Configuration:**
- Render assigns `$PORT` dynamically
- Internal services use fixed ports (8001-8004)
- Gateway binds to `$PORT` for external access

---

## 3. Environment Variable Design

### 3.1 Common Environment Variables

**Application Settings:**
```bash
APP_ENV=production
APP_NAME="Prescription Understanding & Patient Education Assistant"
APP_VERSION=1.0.0
```

**Service Ports (Internal):**
```bash
GATEWAY_PORT=8000
OCR_SERVICE_PORT=8001
DRUG_EXTRACTOR_PORT=8002
DRUG_INFO_SERVICE_PORT=8003
AUDIT_SERVICE_PORT=8004
```

**CORS Configuration:**
```bash
CORS_ORIGINS=["https://your-frontend.onrender.com"]
```

**File Upload Settings:**
```bash
MAX_FILE_SIZE_MB=10
UPLOAD_DIR=/tmp/uploads
IMAGE_RETENTION_HOURS=1
```

### 3.2 LLM Provider Configuration

**Primary: Groq Cloud LLM (Production)**
```bash
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TEMPERATURE=0.3
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=2
LLM_LOG_LEVEL=info
```

**Why Groq for Deployment:**
- Free tier available with generous limits
- Fast inference (sub-second response times)
- No local GPU required
- Simple REST API integration
- Reliable uptime for demos

**API Key Reuse Strategy:**
- Single Groq API key shared across all users and sessions
- Key stored securely in Render environment variables
- Never exposed to frontend
- No per-user billing (suitable for academic prototype)
- Rate limits managed at application level

### 3.3 Development-Only Variables (LM Studio)

**Not Used in Deployed Environment:**
```bash
# LM Studio (local development only)
# LLM_PROVIDER=lmstudio
# LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
# LMSTUDIO_MODEL=llama-3.1-8b-instruct
```

**Note**: LM Studio requires local server and cannot run on Render free tier. Always use `LLM_PROVIDER=groq` for deployment.

### 3.4 OCR Configuration

```bash
OCR_USE_GPU=false
OCR_LANGUAGES=["en"]
CONFIDENCE_HIGH_THRESHOLD=0.85
CONFIDENCE_MEDIUM_THRESHOLD=0.60
```

**Note**: GPU disabled for free tier compatibility. CPU-based OCR is sufficient for prototype.

### 3.5 Demo Mode Variables (Optional)

```bash
DEMO_MODE=true
DEMO_BANNER_TEXT="Educational Prototype Only - Not for Clinical Use"
RATE_LIMIT_ENABLED=false
```

---

## 4. Backend Startup & Validation Logic

### 4.1 Startup Sequence

The backend service follows this startup sequence:

1. **Load Configuration** (`shared/config.py`)
   - Read environment variables
   - Apply defaults where appropriate
   - Parse JSON arrays (CORS_ORIGINS, OCR_LANGUAGES)

2. **Validate LLM Configuration** (`shared/config.py::validate_llm_config()`)
   - Check `LLM_PROVIDER` value (must be "groq" or "lmstudio")
   - Verify required provider-specific variables
   - Fail fast if configuration invalid

3. **Initialize LLM Client** (`drug_info_service/main.py::startup_event()`)
   - Create appropriate LLM client based on provider
   - Test connectivity to LLM API
   - Log provider status (redact secrets)

4. **Start FastAPI Application**
   - Initialize all microservice routes
   - Configure CORS middleware
   - Bind to assigned port

5. **Health Check Ready**
   - `/health` endpoint responds with service status
   - `/health/llm` endpoint shows LLM provider status

### 4.2 Configuration Validation Logic

```python
def validate_llm_config(settings: Settings) -> tuple[bool, str]:
    provider = settings.LLM_PROVIDER.lower()
    
    if provider not in ["lmstudio", "groq"]:
        return False, f"Invalid LLM_PROVIDER: '{provider}'"
    
    if provider == "groq":
        if not settings.GROQ_API_KEY:
            return False, "GROQ_API_KEY required for groq provider"
    
    return True, ""
```

### 4.3 Fail-Fast Behavior

**Invalid Configuration Example:**
```
❌ LLM Configuration Error: GROQ_API_KEY is required when LLM_PROVIDER=groq
⚠️  Service will start but requests will fail until configuration is fixed.
📝 See documentation for configuration instructions.
```

**Valid Configuration Example:**
```
✅ LLM Provider initialized: groq
   Model: llama-3.3-70b-versatile
   Base URL: https://api.groq.com/openai/v1
✅ LLM Provider connectivity: OK
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:10000
```

### 4.4 Graceful Degradation

If LLM provider is temporarily unavailable:
- Service continues to run
- OCR and drug extraction still work
- Drug info requests return fallback response with clear message
- User sees: "Information temporarily unavailable. Please try again."

---

## 5. OCR & Drug Extraction Deployment Considerations

### 5.1 EasyOCR Deployment

**Library Installation:**
- EasyOCR installed via `requirements.txt`
- Includes CPU-only dependencies
- Model files downloaded on first run (cached in `/tmp`)

**Memory Considerations:**
- EasyOCR model: ~200MB
- First request triggers model download (30-60 seconds)
- Subsequent requests use cached model
- Free tier memory limit: 512MB (sufficient)

**Cold Start Handling:**
```python
@app.on_event("startup")
async def warmup_ocr():
    """Pre-load OCR model to reduce first-request latency."""
    try:
        reader = easyocr.Reader(['en'], gpu=False)
        # Model now cached
    except Exception as e:
        logger.warning(f"OCR warmup failed: {e}")
```

### 5.2 Drug Name Extraction

**Fuzzy Matching Database:**
- 80+ common drug names hardcoded in `drug_extractor/main.py`
- No external database required
- Levenshtein distance for typo tolerance
- Confidence scores computed locally

**Fallback Strategy:**
1. Primary: Regex pattern matching for prescription format
2. Secondary: Fuzzy matching against known drugs
3. Tertiary: Return low confidence candidates for user confirmation

---

## 6. LLM Usage in Deployed Environment

### 6.1 Why Groq is Used in Cloud

**Technical Reasons:**
1. **No Local Resources**: LM Studio requires local GPU/CPU and server process
2. **Render Limitations**: Cannot run persistent local LLM servers on free tier
3. **Performance**: Groq provides <1s inference times vs. local CPU inference (10-30s)
4. **Reliability**: Cloud API more stable than local server for demonstrations
5. **Free Tier**: Groq offers generous free tier suitable for academic projects

**Comparison:**

| Aspect | LM Studio (Local) | Groq (Cloud) |
|--------|------------------|--------------|
| Cost | Free (local compute) | Free tier available |
| Latency | 10-30s (CPU) | <1s |
| Deployment | Requires local server | REST API only |
| Reliability | Depends on local machine | 99.9% uptime |
| Render Compatible | No | Yes |

### 6.2 API Key Reuse Explanation

**Why Single Shared API Key:**
1. **Academic Prototype**: Not a production application with paying users
2. **Cost Control**: No risk of per-user billing
3. **Simplicity**: No user authentication or API key management required
4. **Groq Free Tier**: Allows shared key usage with rate limits

**Security Implementation:**
- API key stored in Render environment variables (encrypted at rest)
- Never sent to frontend or logged
- Never exposed in API responses
- Health check endpoint redacts key: `"api_key": "***REDACTED***"`

**Rate Limit Handling:**
- Groq free tier: 30 requests/minute, 14,400 requests/day
- Application-level caching (in-memory for 5 minutes per drug)
- Graceful error messages if rate limit exceeded
- No user data sent to Groq (only drug names)

**Prompt Template (Fixed):**
```json
{
  "system": "You are a medical educator. Provide only: general uses, common side effects, safety warnings. No prescribing, no dosage advice. Output JSON only.",
  "user": "Explain Paracetamol"
}
```

### 6.3 LLM Request Flow

```
User Request
    ↓
API Gateway
    ↓
Drug Info Service
    ↓
Check Cache (5 min TTL)
    ↓ (if miss)
LLM Client Factory
    ↓
Groq Client (selected via env)
    ↓
HTTPS POST to api.groq.com
    ↓
Parse JSON Response
    ↓
Return to User
```

---

## 7. Security & Privacy Best Practices (Prototype Level)

### 7.1 Data Handling

**No PHI Storage:**
- Prescription images deleted immediately after OCR processing
- No database or persistent storage
- OCR text stored in memory only (session-scoped)
- Audit logs contain no personally identifiable information

**Data Retention Policy:**
```python
IMAGE_RETENTION_HOURS=1   # Images deleted after 1 hour
LOG_RETENTION_HOURS=168   # Logs rotated after 7 days
# In practice: In-memory only, cleared on service restart
```

### 7.2 API Security

**CORS Configuration:**
```python
CORS_ORIGINS=[
    "https://your-frontend.onrender.com",
    "http://localhost:3000"  # Development only
]
```

**Input Validation:**
- File type validation (images only)
- File size limits (10MB max)
- Drug name sanitization (no SQL injection risk)
- Request timeouts (60 seconds max)

**Secret Management:**
- All secrets in Render environment variables
- No secrets in code or version control
- `.env` files in `.gitignore`
- Health endpoints redact sensitive values

### 7.3 Disclaimer Strategy

**Frontend Disclaimer (Persistent Banner):**
```javascript
<div className="disclaimer-banner">
  ⚠️ EDUCATIONAL PROTOTYPE ONLY - NOT FOR CLINICAL USE
  This application does not provide medical advice.
  Always consult your healthcare provider.
</div>
```

**API Response Disclaimer (Every Response):**
```json
{
  "disclaimer": "This information is for educational purposes only and is not intended as medical advice. Do not change your medication regimen without consulting your healthcare provider."
}
```

### 7.4 Rate Limiting (Lightweight)

**Application-Level:**
```python
# In-memory rate limiter
MAX_REQUESTS_PER_IP_PER_MINUTE = 10
```

**Groq API Level:**
- Handled by Groq (30 req/min)
- Return clear error message to user
- Suggest retry after 1 minute

---

## 8. Render Deployment Steps (Step-by-Step)

### 8.1 Prerequisites

1. **GitHub Repository Setup:**
   - Create GitHub account if needed
   - Create new repository: `prescription-reader-prototype`
   - Push your code to repository:
     ```bash
     git init
     git add .
     git commit -m "Initial commit"
     git branch -M main
     git remote add origin https://github.com/yourusername/prescription-reader-prototype.git
     git push -u origin main
     ```

2. **Groq API Key:**
   - Visit https://console.groq.com
   - Sign up for free account
   - Generate API key
   - Copy key (starts with `gsk_`)

3. **Render Account:**
   - Sign up at https://render.com
   - Connect GitHub account
   - Authorize Render to access repositories

### 8.2 Deploy Backend Service

**Step 1: Create Web Service**
1. Go to Render Dashboard
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure service:
   - **Name**: `prescription-reader-backend`
   - **Region**: Select closest to your location
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn gateway.main:app --host 0.0.0.0 --port $PORT`

**Step 2: Set Environment Variables**
In Render dashboard, go to "Environment" tab and add:

```bash
# Application
APP_ENV=production
APP_VERSION=1.0.0

# LLM Provider (CRITICAL)
LLM_PROVIDER=groq
GROQ_API_KEY=your_actual_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_BASE_URL=https://api.groq.com/openai/v1
LLM_TIMEOUT_SECONDS=60

# Service Configuration
GATEWAY_PORT=8000
OCR_SERVICE_PORT=8001
DRUG_EXTRACTOR_PORT=8002
DRUG_INFO_SERVICE_PORT=8003
AUDIT_SERVICE_PORT=8004

# Service URLs (Internal)
OCR_SERVICE_URL=http://localhost:8001
DRUG_EXTRACTOR_URL=http://localhost:8002
DRUG_INFO_SERVICE_URL=http://localhost:8003
AUDIT_SERVICE_URL=http://localhost:8004

# OCR Configuration
OCR_USE_GPU=false
OCR_LANGUAGES=["en"]

# Thresholds
CONFIDENCE_HIGH_THRESHOLD=0.85
CONFIDENCE_MEDIUM_THRESHOLD=0.60

# File Handling
MAX_FILE_SIZE_MB=10
UPLOAD_DIR=/tmp/uploads
IMAGE_RETENTION_HOURS=1

# CORS (Update after frontend deployed)
CORS_ORIGINS=["http://localhost:3000"]
```

**Step 3: Deploy**
1. Click "Create Web Service"
2. Wait for build and deployment (5-10 minutes)
3. Note the service URL: `https://prescription-reader-backend.onrender.com`

**Step 4: Verify Backend**
```bash
curl https://prescription-reader-backend.onrender.com/health
# Expected: {"service":"API Gateway","status":"healthy"}

curl https://prescription-reader-backend.onrender.com/health/llm
# Expected: {"llm_provider":"groq","llm_status":"available"}
```

### 8.3 Deploy Frontend Service

**Step 1: Create Static Site**
1. Go to Render Dashboard
2. Click "New +" → "Static Site"
3. Connect same GitHub repository
4. Configure site:
   - **Name**: `prescription-reader-frontend`
   - **Branch**: `main`
   - **Root Directory**: Leave empty or `frontend`
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Publish Directory**: `frontend/build`

**Step 2: Set Environment Variables**
In Render dashboard, add:

```bash
REACT_APP_API_URL=https://prescription-reader-backend.onrender.com
REACT_APP_ENV=production
```

**Step 3: Deploy**
1. Click "Create Static Site"
2. Wait for build (3-5 minutes)
3. Note frontend URL: `https://prescription-reader-frontend.onrender.com`

**Step 4: Update Backend CORS**
1. Go back to backend service
2. Update `CORS_ORIGINS` environment variable:
   ```bash
   CORS_ORIGINS=["https://prescription-reader-frontend.onrender.com"]
   ```
3. Backend will automatically redeploy

### 8.4 Create Frontend Proxy Configuration

**Create `frontend/package.json` proxy (if needed):**
```json
{
  "proxy": "https://prescription-reader-backend.onrender.com"
}
```

**Or use environment variable in React:**
```javascript
// frontend/src/services/api.js
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
```

### 8.5 Test Full Application

1. Visit frontend URL
2. Upload a prescription image
3. Verify OCR extraction works
4. Check drug information displays
5. Confirm OTC recommendations appear
6. Verify disclaimers are visible

---

## 9. Cost Considerations & Free Tier Limits

### 9.1 Render Free Tier Limits

**Web Service (Backend):**
- **CPU**: Shared
- **Memory**: 512MB
- **Bandwidth**: 100GB/month
- **Build Minutes**: 500/month
- **Cold Starts**: Service spins down after 15 minutes of inactivity
- **Spin-Up Time**: 30-60 seconds on first request

**Static Site (Frontend):**
- **Bandwidth**: 100GB/month
- **Build Minutes**: Counted toward total
- **CDN**: Global, no cold starts

**Total Cost**: **$0/month** for prototype

### 9.2 Groq Free Tier Limits

- **Requests**: 30 per minute, 14,400 per day
- **Cost**: Free
- **Models**: Full access to llama-3.3-70b-versatile
- **Upgrade Path**: Paid tier available if needed

**Sufficient For:**
- Academic demonstrations
- Viva presentations
- Portfolio showcases
- Small-scale testing (10-50 users/day)

### 9.3 Cold Start Management

**Problem**: Free tier services spin down after 15 minutes of inactivity.

**Solutions:**

1. **Accept Cold Starts** (Recommended for Free Prototype)
   - First request after idle: 30-60 seconds
   - Subsequent requests: <1 second
   - Display loading message: "Waking up service..."

2. **Keep-Alive Pings** (Optional, May Hit Limits)
   - Cron job pings health endpoint every 10 minutes
   - Use external service like cron-job.org
   - May consume bandwidth limits

3. **Pre-Demo Warm-Up**
   - Visit application 2 minutes before demo
   - Trigger OCR + LLM request
   - Service stays warm for 15 minutes

**Frontend Implementation:**
```javascript
if (response.status === 503) {
  setMessage("Service is waking up (cold start). Please wait 30 seconds...");
  // Retry after delay
}
```

---

## 10. Common Deployment Pitfalls & How to Avoid Them

### 10.1 Environment Variable Issues

**Pitfall**: Forgetting to set `LLM_PROVIDER=groq` in production
**Solution**: Check startup logs for provider initialization message
**Verification**: `curl https://your-backend.onrender.com/health/llm`

**Pitfall**: CORS_ORIGINS still set to localhost
**Solution**: Update after frontend deploys
**Symptom**: Frontend cannot connect to backend (CORS errors in browser console)

### 10.2 Build Failures

**Pitfall**: `requirements.txt` missing dependencies
**Solution**: Generate complete requirements:
```bash
pip freeze > backend/requirements.txt
```

**Pitfall**: Frontend build fails due to missing dependencies
**Solution**: Ensure `package.json` includes all dependencies:
```bash
cd frontend
npm install
npm run build  # Test locally first
```

### 10.3 Port Configuration

**Pitfall**: Backend hardcodes port 8000 instead of using `$PORT`
**Solution**: Use Render's dynamic port:
```python
# Wrong
uvicorn.run(app, host="0.0.0.0", port=8000)

# Correct
import os
port = int(os.environ.get("PORT", 8000))
uvicorn.run(app, host="0.0.0.0", port=port)
```

Or in start command:
```bash
uvicorn gateway.main:app --host 0.0.0.0 --port $PORT
```

### 10.4 File System Issues

**Pitfall**: Trying to write files to `/uploads` (read-only filesystem)
**Solution**: Use `/tmp` for temporary files:
```python
UPLOAD_DIR=/tmp/uploads
```

**Pitfall**: Assuming files persist between requests
**Solution**: Clean up files immediately after processing

### 10.5 Memory Limits

**Pitfall**: Loading too many models simultaneously
**Solution**: Lazy load models, use CPU-only mode
```python
OCR_USE_GPU=false  # CRITICAL for free tier
```

**Pitfall**: Not clearing in-memory caches
**Solution**: Implement cache size limits:
```python
MAX_CACHE_SIZE = 100  # entries
```

### 10.6 LLM Provider Errors

**Pitfall**: Groq API key expired or invalid
**Symptom**: All drug info requests fail with 401 error
**Solution**: Regenerate key at console.groq.com, update env var

**Pitfall**: Rate limit exceeded during demo
**Solution**: Pre-cache common drugs, implement exponential backoff

---

## 11. Demo Strategy for Viva & Evaluation

### 11.1 Preparation Checklist

**One Week Before:**
- [ ] Deploy to Render and verify all services healthy
- [ ] Test with 5-10 different prescription images
- [ ] Record screen capture of full workflow (backup video)
- [ ] Take screenshots of key features
- [ ] Document any known limitations
- [ ] Prepare fallback local demo (in case of network issues)

**One Day Before:**
- [ ] Verify application is still running
- [ ] Check Groq API key is valid
- [ ] Test from presentation room network if possible
- [ ] Warm up service (visit URL to prevent cold start during demo)

**30 Minutes Before:**
- [ ] Open application in browser tab
- [ ] Load backup video on laptop
- [ ] Have 2-3 prescription images ready
- [ ] Trigger warm-up requests

### 11.2 Demo Script (5-7 Minutes)

**Minute 1-2: Introduction**
- Show landing page with disclaimer
- Explain educational purpose
- Mention microservices architecture

**Minute 3-4: Core Functionality**
1. Upload handwritten prescription image
2. Show OCR extraction with confidence scores
3. Demonstrate user confirmation for low-confidence drugs
4. Display drug information panel with:
   - General uses
   - Side effects
   - Safety warnings
   - OTC recommendations

**Minute 5-6: Technical Highlights**
- Mention LLM provider architecture (Groq)
- Explain confidence scoring system
- Show health check endpoints
- Demonstrate chat interface for direct drug queries

**Minute 7: Limitations & Future Work**
- Acknowledge prototype limitations
- Discuss potential enhancements (RAG, multiple languages)
- Answer questions

### 11.3 Screenshot Requirements

**Capture these screens:**
1. Landing page with disclaimer
2. Prescription upload interface
3. OCR extraction results with confidence bars
4. Drug confirmation dialog (medium/low confidence)
5. Complete drug information panel with OTC section
6. Chat interface with direct query
7. Architecture diagram
8. Health check endpoint response (redacted API key)

### 11.4 Handling Technical Issues

**If service is cold:**
- "The service is on free tier and wakes up from sleep. This typically takes 30-60 seconds on first request."

**If network is slow:**
- Switch to backup video recording

**If LLM fails:**
- Explain graceful degradation
- Show fallback response

**If demo crashes:**
- Have backup screenshots ready
- Explain what should happen

### 11.5 Questions to Anticipate

**Q: Why not use RAG?**
A: This prototype focuses on LLM-based general knowledge. RAG with drug databases is planned for future enhancement.

**Q: How do you ensure accuracy?**
A: We display confidence scores, require user confirmation for low-confidence extractions, and provide strong disclaimers.

**Q: What about privacy?**
A: No data is stored. Images are deleted immediately after OCR. No PHI is logged.

**Q: How do you scale this?**
A: Current architecture supports moving to paid tier with minimal changes. Can add database, caching layer, load balancer.

**Q: Why Groq instead of OpenAI?**
A: Free tier availability, faster inference times, and suitable for academic projects.

---

## 12. Future Enhancements (Optional, Clearly Marked)

These features are **NOT implemented** in the current prototype but can be considered for future versions:

### 12.1 RAG Integration (Not Implemented)

**Potential Enhancement:**
- Vector database (Pinecone, Weaviate)
- Drug database embeddings (FDA, DrugBank)
- Retrieval-augmented generation for more accurate information
- Citation of sources for each fact

**Why Not Now:**
- Adds complexity to deployment
- Requires external services (cost)
- LLM general knowledge sufficient for prototype
- RAG best suited for production applications

### 12.2 User Authentication (Not Implemented)

**Potential Enhancement:**
- User accounts for history tracking
- Personalized drug interaction warnings
- Saved prescription history

**Why Not Now:**
- Privacy concerns (PHI storage)
- Adds database requirement
- Increases deployment complexity
- Not required for educational prototype

### 12.3 Multi-Language Support (Not Implemented)

**Potential Enhancement:**
- Support for prescriptions in multiple languages
- Multi-language UI
- OCR models for non-Latin scripts

**Why Not Now:**
- Increases model size (memory constraints)
- Adds translation complexity
- English sufficient for prototype demonstration

### 12.4 Mobile Application (Not Implemented)

**Potential Enhancement:**
- React Native mobile app
- Camera integration for direct prescription capture
- Offline mode with cached drug information

**Why Not Now:**
- Requires separate deployment pipeline
- Additional development effort
- Web application sufficient for demonstration

### 12.5 Enhanced OCR (Not Implemented)

**Potential Enhancement:**
- TrOCR transformer model for better handwriting recognition
- Multiple OCR model ensemble
- Preprocessing pipeline (deskew, denoise, enhance)

**Why Not Now:**
- Requires more memory (free tier limits)
- Longer processing times
- EasyOCR sufficient for common prescriptions

### 12.6 Drug Interaction Checker (Not Implemented)

**Potential Enhancement:**
- Check interactions between multiple drugs
- Alert for contraindications
- Integration with drug interaction databases

**Why Not Now:**
- Requires clinical-grade databases
- Liability concerns (medical advice)
- Beyond scope of educational prototype

---

## Appendix A: Environment Variables Reference

### Complete .env.example for Backend

```bash
# ============================================
# Prescription Reader - Production Environment
# ============================================

# ---------- Application Settings ----------
APP_ENV=production
APP_NAME="Prescription Understanding & Patient Education Assistant"
APP_VERSION=1.0.0

# ---------- LLM Provider (CRITICAL) ----------
LLM_PROVIDER=groq
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=2
LLM_LOG_LEVEL=info

# ---------- Groq Configuration ----------
GROQ_API_KEY=  # Get from console.groq.com
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TEMPERATURE=0.3

# ---------- Service Ports (Internal) ----------
GATEWAY_PORT=8000
OCR_SERVICE_PORT=8001
DRUG_EXTRACTOR_PORT=8002
DRUG_INFO_SERVICE_PORT=8003
AUDIT_SERVICE_PORT=8004

# ---------- Service URLs ----------
OCR_SERVICE_URL=http://localhost:8001
DRUG_EXTRACTOR_URL=http://localhost:8002
DRUG_INFO_SERVICE_URL=http://localhost:8003
AUDIT_SERVICE_URL=http://localhost:8004

# ---------- OCR Configuration ----------
OCR_USE_GPU=false
OCR_LANGUAGES=["en"]

# ---------- Confidence Thresholds ----------
CONFIDENCE_HIGH_THRESHOLD=0.85
CONFIDENCE_MEDIUM_THRESHOLD=0.60

# ---------- File Handling ----------
MAX_FILE_SIZE_MB=10
UPLOAD_DIR=/tmp/uploads
IMAGE_RETENTION_HOURS=1

# ---------- CORS ----------
CORS_ORIGINS=["https://your-frontend.onrender.com"]

# ---------- Demo Mode ----------
DEMO_MODE=true
```

### Frontend Environment Variables

```bash
# frontend/.env.production
REACT_APP_API_URL=https://your-backend.onrender.com
REACT_APP_ENV=production
```

---

## Appendix B: Render Service Health Monitoring

### Backend Health Checks

**Basic Health:**
```bash
GET /health

Response:
{
  "service": "API Gateway",
  "status": "healthy",
  "version": "1.0.0"
}
```

**LLM Provider Health:**
```bash
GET /health/llm

Response:
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

**Service Status Dashboard:**
```bash
GET /health/services

Response:
{
  "gateway": "healthy",
  "ocr_service": "healthy",
  "drug_extractor": "healthy",
  "drug_info_service": "healthy",
  "audit_service": "healthy"
}
```

---

## Appendix C: Troubleshooting Decision Tree

```
Problem: Application not working
    |
    ├─> Frontend loads but cannot connect to backend
    |   └─> Check CORS_ORIGINS in backend env vars
    |       └─> Verify frontend URL is whitelisted
    |
    ├─> Backend returns 503 errors
    |   └─> Check /health/llm endpoint
    |       ├─> "llm_status": "unavailable"
    |       |   └─> Verify GROQ_API_KEY is set
    |       |       └─> Test key at console.groq.com
    |       |
    |       └─> "error": "rate limit exceeded"
    |           └─> Wait 1 minute, try again
    |               └─> Consider caching responses
    |
    ├─> OCR not extracting text
    |   └─> Check logs for EasyOCR errors
    |       ├─> "Out of memory"
    |       |   └─> Verify OCR_USE_GPU=false
    |       |
    |       └─> "Model download failed"
    |           └─> Check /tmp has write access
    |
    ├─> Service won't start
    |   └─> Check build logs in Render dashboard
    |       ├─> "Module not found"
    |       |   └─> Update requirements.txt
    |       |
    |       └─> "Port already in use"
    |           └─> Use $PORT in start command
    |
    └─> Slow first request (30-60s)
        └─> Cold start (expected on free tier)
            └─> Display "Waking up service" message
```

---

## Conclusion

This deployment guide provides a complete, step-by-step approach to deploying the Prescription Understanding & Patient Education Assistant on Render's free tier. The architecture is optimized for academic demonstrations while maintaining professional-grade security and reliability standards.

**Key Takeaways:**
- Zero-cost deployment suitable for M.Tech project demonstrations
- Clean LLM provider architecture with environment-based selection
- Groq cloud LLM provides fast, reliable inference without local resources
- Graceful handling of free tier limitations (cold starts, memory)
- Strong privacy and security practices (no PHI storage, secret management)
- Comprehensive demo strategy for successful viva presentation

**Success Metrics:**
- ✅ Application accessible via public URL
- ✅ Full functionality: OCR → Drug Extraction → LLM Education → OTC Recommendations
- ✅ Response times: <3s (warm), <60s (cold start)
- ✅ Zero deployment costs
- ✅ Ready for academic evaluation and portfolio showcase

For additional support, refer to:
- Render Documentation: https://render.com/docs
- Groq Documentation: https://console.groq.com/docs
- Project Repository: https://github.com/yourusername/prescription-reader-prototype
