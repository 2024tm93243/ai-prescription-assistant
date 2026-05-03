# 📋 Render Deployment Checklist

Complete this checklist to deploy your Prescription Reader application to Render.com.

---

## ✅ Pre-Deployment Checklist

### 1. Code Preparation
- [ ] All code committed to Git repository
- [ ] `.gitignore` includes `.env` files (no secrets in repo)
- [ ] `backend/requirements.txt` exists with all dependencies
- [ ] `backend/start.sh` is executable (`chmod +x backend/start.sh`)
- [ ] `frontend/package.json` has all npm dependencies
- [ ] `frontend/src/services/api.js` uses `REACT_APP_API_URL` environment variable

### 2. Groq API Key
- [ ] Created account at https://console.groq.com
- [ ] Generated API key (starts with `gsk_`)
- [ ] Copied key to secure location (e.g., password manager)
- [ ] Tested key locally (set in `backend/.env` and run services)

### 3. GitHub Repository
- [ ] Created GitHub repository
- [ ] Pushed code to main branch
- [ ] Repository is accessible (public or private with Render access)
- [ ] Verified all files are present in GitHub

### 4. Render Account
- [ ] Created account at https://render.com
- [ ] Connected GitHub account to Render
- [ ] Authorized Render to access repositories

---

## 🚀 Deployment Steps

### Phase 1: Deploy Backend

#### Step 1.1: Create Web Service
1. [ ] Log in to Render Dashboard
2. [ ] Click **"New +"** → **"Web Service"**
3. [ ] Select your GitHub repository
4. [ ] Click **"Connect"**

#### Step 1.2: Configure Backend Service
Fill in the form:

- [ ] **Name**: `prescription-reader-backend`
- [ ] **Region**: Choose closest to your location (e.g., Oregon)
- [ ] **Branch**: `main`
- [ ] **Runtime**: `Python 3`
- [ ] **Build Command**: `pip install -r backend/requirements.txt`
- [ ] **Start Command**: `cd backend && chmod +x start.sh && ./start.sh`

#### Step 1.3: Add Environment Variables
Click **"Advanced"** and add these environment variables:

**Critical Variables:**
- [ ] `LLM_PROVIDER` = `groq`
- [ ] `GROQ_API_KEY` = `your_actual_api_key_here` ⚠️ Replace with your key
- [ ] `GROQ_MODEL` = `llama-3.3-70b-versatile`
- [ ] `GROQ_BASE_URL` = `https://api.groq.com/openai/v1`

**Application Settings:**
- [ ] `APP_ENV` = `production`
- [ ] `APP_VERSION` = `1.0.0`

**LLM Configuration:**
- [ ] `LLM_TIMEOUT_SECONDS` = `60`
- [ ] `LLM_MAX_RETRIES` = `2`
- [ ] `LLM_LOG_LEVEL` = `info`

**Service Ports:**
- [ ] `GATEWAY_PORT` = `8000`
- [ ] `OCR_SERVICE_PORT` = `8001`
- [ ] `DRUG_EXTRACTOR_PORT` = `8002`
- [ ] `DRUG_INFO_SERVICE_PORT` = `8003`
- [ ] `AUDIT_SERVICE_PORT` = `8004`

**Service URLs:**
- [ ] `OCR_SERVICE_URL` = `http://localhost:8001`
- [ ] `DRUG_EXTRACTOR_URL` = `http://localhost:8002`
- [ ] `DRUG_INFO_SERVICE_URL` = `http://localhost:8003`
- [ ] `AUDIT_SERVICE_URL` = `http://localhost:8004`

**OCR Configuration:**
- [ ] `OCR_USE_GPU` = `false`
- [ ] `OCR_LANGUAGES` = `["en"]`

**Thresholds:**
- [ ] `CONFIDENCE_HIGH_THRESHOLD` = `0.85`
- [ ] `CONFIDENCE_MEDIUM_THRESHOLD` = `0.60`

**File Handling:**
- [ ] `MAX_FILE_SIZE_MB` = `10`
- [ ] `UPLOAD_DIR` = `/tmp/uploads`
- [ ] `IMAGE_RETENTION_HOURS` = `1`

**CORS (temporary - will update later):**
- [ ] `CORS_ORIGINS` = `["http://localhost:3000"]`

#### Step 1.4: Deploy Backend
1. [ ] Review all settings
2. [ ] Click **"Create Web Service"**
3. [ ] Wait for build to complete (5-10 minutes)
4. [ ] Note backend URL (e.g., `https://prescription-reader-backend.onrender.com`)

#### Step 1.5: Verify Backend
Run these tests in terminal:

```bash
# Test basic health
curl https://prescription-reader-backend.onrender.com/health

# Expected output:
# {"service":"API Gateway","status":"healthy","version":"1.0.0"}

# Test LLM provider health
curl https://prescription-reader-backend.onrender.com/health/llm

# Expected output:
# {"service":"drug_info","llm_provider":"groq","llm_status":"available"}
```

- [ ] Health check returns healthy status
- [ ] LLM health check shows `groq` provider
- [ ] No errors in Render logs

**Backend URL**: ___________________________

---

### Phase 2: Deploy Frontend

#### Step 2.1: Create Static Site
1. [ ] Return to Render Dashboard
2. [ ] Click **"New +"** → **"Static Site"**
3. [ ] Select same GitHub repository
4. [ ] Click **"Connect"**

#### Step 2.2: Configure Frontend Service
Fill in the form:

- [ ] **Name**: `prescription-reader-frontend`
- [ ] **Branch**: `main`
- [ ] **Build Command**: `cd frontend && npm install && npm run build`
- [ ] **Publish Directory**: `frontend/build`

#### Step 2.3: Add Environment Variables
Click **"Advanced"** and add:

- [ ] `REACT_APP_API_URL` = `https://your-backend-url.onrender.com` ⚠️ Use URL from Step 1.4
- [ ] `REACT_APP_ENV` = `production`

#### Step 2.4: Deploy Frontend
1. [ ] Review all settings
2. [ ] Click **"Create Static Site"**
3. [ ] Wait for build to complete (3-5 minutes)
4. [ ] Note frontend URL (e.g., `https://prescription-reader-frontend.onrender.com`)

**Frontend URL**: ___________________________

---

### Phase 3: Connect Services

#### Step 3.1: Update Backend CORS
1. [ ] Go to Render Dashboard → Backend Service
2. [ ] Click **"Environment"** tab
3. [ ] Find `CORS_ORIGINS` variable
4. [ ] Update value to: `["https://your-frontend-url.onrender.com"]` ⚠️ Use actual frontend URL
5. [ ] Click **"Save Changes"**
6. [ ] Wait for backend to redeploy (~2 minutes)

#### Step 3.2: Test Connection
1. [ ] Open frontend URL in browser
2. [ ] Open browser DevTools (F12) → Console tab
3. [ ] Check for CORS errors (should be none)
4. [ ] Try typing a drug name (e.g., "Paracetamol")
5. [ ] Verify response appears

- [ ] No CORS errors in browser console
- [ ] Drug info requests complete successfully

---

## 🧪 Full Application Testing

### Test 1: Direct Drug Query
1. [ ] Open frontend in browser
2. [ ] Type "Ibuprofen" in chat input
3. [ ] Press Enter
4. [ ] Wait for response (30-60 seconds on first request - cold start)
5. [ ] Verify drug information displays in panel below

**Expected Results:**
- [ ] Chat shows "Here's the information about Ibuprofen"
- [ ] Drug info panel appears with uses, side effects, warnings
- [ ] OTC recommendations section displays
- [ ] Disclaimer banner visible at top

### Test 2: Prescription Upload
1. [ ] Prepare a prescription image (JPG/PNG)
2. [ ] Click "Choose File" or drag-and-drop
3. [ ] Upload the image
4. [ ] Wait for OCR processing (30-90 seconds)
5. [ ] Verify extracted drug names appear in chat

**Expected Results:**
- [ ] OCR extracts text successfully
- [ ] Drug names identified with confidence scores
- [ ] High/medium confidence drugs show info automatically
- [ ] Low confidence drugs ask for confirmation

### Test 3: OTC Recommendations
1. [ ] Query any drug (e.g., "Aspirin")
2. [ ] Scroll to drug info panel
3. [ ] Look for "Managing Side Effects" section
4. [ ] Verify OTC options listed (e.g., antacids, antihistamines)

**Expected Results:**
- [ ] OTC section visible with red/pink background
- [ ] Side effects listed with OTC options
- [ ] Caution messages displayed
- [ ] Strong disclaimer at top and bottom

### Test 4: Mobile Responsiveness
1. [ ] Open frontend on mobile device or resize browser
2. [ ] Test all features on small screen
3. [ ] Verify layout adapts properly

**Expected Results:**
- [ ] Disclaimer banner stacks vertically
- [ ] Chat interface usable on mobile
- [ ] Upload button accessible
- [ ] Drug info panel scrollable

---

## 🐛 Troubleshooting

### Backend Won't Start
**Symptom**: Build fails or service crashes immediately

**Check:**
- [ ] Review build logs for missing dependencies
- [ ] Verify `start.sh` has execute permission
- [ ] Check for typos in environment variables
- [ ] Ensure `GROQ_API_KEY` is set and valid

**Fix:**
1. Update `requirements.txt` if dependencies missing
2. Verify start command includes `chmod +x start.sh`
3. Re-deploy service

### LLM Requests Fail
**Symptom**: Drug info returns errors like "Information temporarily unavailable"

**Check:**
- [ ] Visit `/health/llm` endpoint
- [ ] Verify `LLM_PROVIDER=groq` in environment
- [ ] Check `GROQ_API_KEY` is correct
- [ ] Test API key at console.groq.com

**Fix:**
1. Regenerate Groq API key if invalid
2. Update environment variable
3. Redeploy service

### CORS Errors
**Symptom**: Browser console shows "CORS policy blocked" errors

**Check:**
- [ ] `CORS_ORIGINS` includes frontend URL
- [ ] Frontend URL matches exactly (no trailing slash)
- [ ] Backend has redeployed after CORS update

**Fix:**
1. Go to backend environment settings
2. Update `CORS_ORIGINS` to `["https://exact-frontend-url.onrender.com"]`
3. Save and wait for redeploy

### Cold Start Delays
**Symptom**: First request takes 30-60 seconds

**This is expected behavior** on Render free tier.

**Mitigation:**
1. [ ] Add loading message to frontend
2. [ ] Warm up service before demo (visit URL 2 minutes prior)
3. [ ] Explain cold start during presentation

### OCR Fails
**Symptom**: "Failed to process prescription" error

**Check:**
- [ ] Image file size < 10MB
- [ ] Image format is JPG/PNG
- [ ] EasyOCR model downloaded (check logs for "Downloading model")

**Fix:**
1. Try clearer image with better contrast
2. Wait for first request to complete (model download)
3. Retry upload

---

## 📊 Post-Deployment

### Monitor Application
- [ ] Save backend URL for monitoring
- [ ] Save frontend URL for demos
- [ ] Bookmark Render dashboard
- [ ] Set up uptime monitoring (optional - uptimerobot.com)

### Document URLs
- **Frontend**: ________________________________
- **Backend API**: ________________________________
- **Health Check**: ________________________________/health
- **LLM Health**: ________________________________/health/llm

### Prepare for Demo
- [ ] Test application end-to-end
- [ ] Record demo video (backup)
- [ ] Take screenshots for presentation
- [ ] Prepare 2-3 sample prescription images
- [ ] Practice demo script (5-7 minutes)
- [ ] Warm up service before viva (visit URL)

### Cost Monitoring
- [ ] Confirm using free tier (no charges)
- [ ] Check bandwidth usage in Render dashboard
- [ ] Monitor build minutes (500/month limit)
- [ ] Track Groq API usage (30 req/min limit)

---

## 🎉 Success Criteria

You're ready for demo when:

- [x] Backend health check returns healthy
- [x] Frontend loads without errors
- [x] Drug queries return information
- [x] Prescription upload works
- [x] OTC recommendations display
- [x] Disclaimer banner visible
- [x] No CORS errors in console
- [x] Application accessible via public URLs

---

## 📞 Support Resources

- **Render Documentation**: https://render.com/docs
- **Groq Console**: https://console.groq.com
- **Render Status**: https://status.render.com
- **Render Community**: https://community.render.com

---

## 🎓 For Viva Presentation

### Key Talking Points
1. **Architecture**: Microservices deployed as monolith for cost efficiency
2. **LLM Selection**: Groq chosen for speed and free tier availability
3. **Security**: No PHI storage, secrets in environment variables
4. **Scalability**: Can migrate to paid tier with minimal changes
5. **Privacy**: Images deleted immediately, no data persistence

### Demo Preparation
- [ ] Application warmed up (visited 2 minutes before)
- [ ] Backup video ready
- [ ] Screenshots prepared
- [ ] Sample prescriptions ready
- [ ] Architecture diagram printed/displayed
- [ ] Limitations documented

### Questions to Anticipate
1. Why Groq instead of local LLM? (Free tier, performance, deployment simplicity)
2. How do you ensure accuracy? (Confidence scores, user confirmation, disclaimers)
3. What about privacy? (No storage, immediate deletion, no PHI in logs)
4. How to scale? (Move to paid tier, add database, implement caching)
5. Why not RAG? (Future enhancement, LLM knowledge sufficient for prototype)

---

**Deployment Date**: _______________
**Deployed By**: _______________
**Version**: 1.0.0
**Status**: [ ] Deployed [ ] Tested [ ] Demo-Ready
