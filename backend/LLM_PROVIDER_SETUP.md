# LLM Provider Configuration

## Overview

The Prescription Reader application supports two LLM providers for generating educational drug information:

1. **LM Studio** (local) - Run models locally on your machine
2. **Groq** (cloud) - Fast, free-tier cloud inference via Groq API

Provider selection is controlled via environment variables, allowing you to easily switch between local and cloud inference without code changes.

## Quick Start

### Option 1: Using Groq (Recommended for Testing)

1. Get a free API key from [https://console.groq.com](https://console.groq.com)

2. Set environment variables:
```bash
export LLM_PROVIDER=groq
export GROQ_API_KEY="your-api-key-here"
```

3. Start the drug info service:
```bash
cd backend
python3 -m uvicorn drug_info_service.main:app --host 0.0.0.0 --port 8003
```

### Option 2: Using LM Studio (Local)

1. Install and start LM Studio:
   - Download from [https://lmstudio.ai](https://lmstudio.ai)
   - Load a model (recommended: llama-3.1-8b-instruct or similar)
   - Start the local server (default port: 1234)

2. Set environment variables:
```bash
export LLM_PROVIDER=lmstudio
export LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
export LMSTUDIO_MODEL="your-loaded-model-name"
```

3. Start the drug info service:
```bash
cd backend
python3 -m uvicorn drug_info_service.main:app --host 0.0.0.0 --port 8003
```

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_PROVIDER` | Provider selection | `groq` or `lmstudio` |

### Groq Provider Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | **Yes** | - | Your Groq API key from console.groq.com |
| `GROQ_BASE_URL` | No | `https://api.groq.com/openai/v1` | Groq API base URL |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Model to use |
| `GROQ_TEMPERATURE` | No | `0.3` | Response randomness (0.0-1.0) |

### LM Studio Provider Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LMSTUDIO_BASE_URL` | No | `http://127.0.0.1:1234/v1` | LM Studio server URL |
| `LMSTUDIO_MODEL` | **Yes** | - | Name of loaded model |
| `LMSTUDIO_API_KEY` | No | `lm-studio` | Placeholder (not used) |
| `LMSTUDIO_TEMPERATURE` | No | `0.2` | Response randomness (0.0-1.0) |

### Common LLM Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_TIMEOUT_SECONDS` | `120` | Request timeout |
| `LLM_MAX_RETRIES` | `2` | Max retry attempts |
| `LLM_LOG_LEVEL` | `info` | Logging level (debug/info/warn/error) |
| `APP_ENV` | `dev` | Application environment (dev/prod) |

## Health Checks

After starting the service, verify your LLM provider is working:

```bash
# Check service health
curl http://localhost:8003/health

# Check LLM provider status
curl http://localhost:8003/health/llm
```

The `/health/llm` endpoint returns:
- Provider name (groq or lmstudio)
- Connectivity status
- Configuration summary (API keys redacted)

## Example .env File

Create a `.env` file in the `backend/` directory:

```bash
# For Groq (Cloud)
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_actual_key_here
GROQ_MODEL=llama-3.3-70b-versatile

# For LM Studio (Local)
# LLM_PROVIDER=lmstudio
# LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
# LMSTUDIO_MODEL=llama-3.1-8b-instruct

# Common Settings
LLM_TIMEOUT_SECONDS=120
LLM_LOG_LEVEL=info
APP_ENV=dev
```

## Switching Providers

To switch providers, simply change the `LLM_PROVIDER` environment variable and restart the service:

```bash
# Switch to Groq
export LLM_PROVIDER=groq
export GROQ_API_KEY="your-key"

# OR switch to LM Studio
export LLM_PROVIDER=lmstudio
export LMSTUDIO_MODEL="your-model"

# Restart service
cd backend
python3 -m uvicorn drug_info_service.main:app --host 0.0.0.0 --port 8003
```

## Troubleshooting

### "LLM client not initialized"

**Cause**: Configuration validation failed at startup.

**Solution**: Check the service logs for specific error messages. Common issues:
- Missing `GROQ_API_KEY` when using Groq
- Missing `LMSTUDIO_MODEL` when using LM Studio
- Invalid `LLM_PROVIDER` value (must be "groq" or "lmstudio")

### "LM Studio server is not available"

**Cause**: LM Studio server is not running or not reachable.

**Solution**:
1. Ensure LM Studio is running
2. Check that a model is loaded
3. Verify the local server is started (usually port 1234)
4. Test connectivity: `curl http://127.0.0.1:1234/v1/models`

### "Invalid GROQ_API_KEY"

**Cause**: API key is incorrect or expired.

**Solution**:
1. Generate a new key at [console.groq.com](https://console.groq.com)
2. Update your `.env` file or environment variable
3. Restart the service

### "Groq API rate limit exceeded"

**Cause**: Free tier rate limit reached.

**Solution**:
- Wait a few minutes and try again
- Consider switching to LM Studio for unlimited local inference
- Upgrade to Groq paid tier if needed

## Security Best Practices

1. **Never commit API keys**: Add `.env` to `.gitignore`
2. **Use environment variables**: Don't hardcode secrets in code
3. **Rotate keys regularly**: Generate new API keys periodically
4. **Restrict key permissions**: Use the minimum required permissions
5. **Monitor usage**: Check Groq dashboard for unexpected activity

## Architecture

The application uses a clean provider abstraction:

```
┌─────────────────────────────────────┐
│      Drug Info Service              │
│  (FastAPI + LLM Client Factory)     │
└─────────────────┬───────────────────┘
                  │
                  ├──> create_llm_client(config)
                  │
         ┌────────┴────────┐
         │                 │
    ┌────▼────┐      ┌────▼────┐
    │  Groq   │      │ LM      │
    │ Client  │      │ Studio  │
    └─────────┘      └─────────┘
         │                 │
         ▼                 ▼
    Groq API      LM Studio Local Server
```

Benefits:
- **Single interface**: Both providers implement the same `LLMClient` interface
- **Easy switching**: Change one environment variable to switch providers
- **Fail-fast validation**: Configuration errors detected at startup
- **Consistent output**: Both providers return identical JSON structure
- **Health monitoring**: Built-in health checks for connectivity

## Testing

Test the LLM provider integration:

```bash
# Test drug info endpoint
curl -X GET "http://localhost:8003/drug-info/Paracetamol" | jq .

# Expected response includes:
# - uses
# - side_effects  
# - warnings
# - otc_for_side_effects (OTC recommendations)
# - disclaimer
```

## Support

For issues or questions:
1. Check service logs for detailed error messages
2. Verify environment variables are set correctly
3. Test provider connectivity using health endpoints
4. Review this README for configuration examples
