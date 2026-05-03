"""
Audit/Logging Service - Privacy-preserving logging service.
Logs actions without storing PHI (drug names, patient info).
"""

from __future__ import annotations

import os
import sys
from collections import deque
from datetime import datetime
from typing import Deque, List, Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent directory to path for shared imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import get_settings, SERVICE_NAMES
from shared.models import AuditLogEntry, HealthStatus

settings = get_settings()

app = FastAPI(
    title="Audit Service",
    description="Privacy-preserving logging service",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory log storage (limited size for privacy)
# In production, use a proper logging system with retention policies
MAX_LOG_ENTRIES = 1000
audit_logs: Deque[AuditLogEntry] = deque(maxlen=MAX_LOG_ENTRIES)


class LogRequest(BaseModel):
    """Request to create an audit log entry."""
    action: str
    prescription_id: Optional[str] = None
    drug_count: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint."""
    return HealthStatus(
        service=SERVICE_NAMES["audit"],
        status="healthy",
        version="1.0.0"
    )


@app.post("/log", response_model=AuditLogEntry)
async def create_log(request: LogRequest):
    """
    Create a new audit log entry.
    
    Note: Does not store PHI (drug names, patient information).
    Only stores action type, counts, and success/failure status.
    """
    entry = AuditLogEntry(
        action=request.action,
        prescription_id=request.prescription_id,
        drug_count=request.drug_count,
        success=request.success,
        error_message=request.error_message,
        timestamp=datetime.utcnow()
    )
    
    audit_logs.append(entry)
    return entry


@app.get("/logs", response_model=List[AuditLogEntry])
async def get_logs(
    limit: int = 100,
    action: Optional[str] = None
):
    """
    Get recent audit logs.
    
    Args:
        limit: Maximum number of entries to return
        action: Filter by action type
    """
    logs = list(audit_logs)
    
    if action:
        logs = [log for log in logs if log.action == action]
    
    return logs[-limit:]


@app.get("/logs/stats")
async def get_log_stats():
    """Get aggregated statistics from audit logs."""
    logs = list(audit_logs)
    
    if not logs:
        return {"total": 0, "by_action": {}, "success_rate": 0}
    
    by_action = {}
    success_count = 0
    
    for log in logs:
        by_action[log.action] = by_action.get(log.action, 0) + 1
        if log.success:
            success_count += 1
    
    return {
        "total": len(logs),
        "by_action": by_action,
        "success_rate": success_count / len(logs) if logs else 0
    }


@app.delete("/logs")
async def clear_logs():
    """Clear all audit logs (admin operation)."""
    audit_logs.clear()
    return {"message": "All logs cleared"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.AUDIT_SERVICE_PORT,
        reload=True
    )
