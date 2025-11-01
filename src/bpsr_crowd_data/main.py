from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models
from .adapters import apply_adapter
from .db import get_session, init_db
from .settings import get_settings


# Structured logging setup
logger = logging.getLogger("bpsr_crowd_data")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()


class StructuredFormatter(logging.Formatter):
    """Formatter that adds structured fields for path and status."""

    def format(self, record: logging.LogRecord) -> str:
        path = getattr(record, "path", record.pathname)
        status = getattr(record, "status", "unknown")
        return f"{record.levelname}: {record.getMessage()} | path={path} | status={status}"


handler.setFormatter(StructuredFormatter())
logger.addHandler(handler)


ALLOWED_SOURCES = {"bp_timer", "bpsr_logs", "manual", "other"}

settings = get_settings()

app = FastAPI(title="BPSR Crowd Data", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class IngestPayload(BaseModel):
    source: str
    payload: Dict[str, Any]

    def validate_source(self) -> None:
        if self.source not in ALLOWED_SOURCES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "invalid_source", "message": f"Source must be one of: {ALLOWED_SOURCES}"},
            )


class ReportResponse(BaseModel):
    id: str
    source: str
    ingested_at: datetime
    data: Dict[str, Any]


# In-memory rate limiter with tiny limit
# NOTE: This is NOT multi-instance safe - each process maintains separate state.
# For multi-instance deployments, use Redis or another shared state store.
class RateLimiter:
    def __init__(self, limit_per_minute: int = 10) -> None:
        self.limit = max(1, limit_per_minute)
        self._state: Dict[str, Dict[str, float]] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> bool:
        async with self._lock:
            record = self._state.get(
                key, {"tokens": float(self.limit), "updated": datetime.utcnow().timestamp()}
            )
            now = datetime.utcnow().timestamp()
            elapsed = now - record["updated"]
            refill = elapsed * (self.limit / 60.0)
            tokens = min(float(self.limit), record["tokens"] + refill)
            if tokens < 1.0:
                record["tokens"] = tokens
                record["updated"] = now
                self._state[key] = record
                return False
            record["tokens"] = tokens - 1.0
            record["updated"] = now
            self._state[key] = record
            return True


rate_limiter = RateLimiter(limit_per_minute=10)


def compute_payload_hash(normalized_data: Dict[str, Any]) -> str:
    """Compute stable SHA256 hash from normalized data (sorted keys for determinism)."""
    serialized = json.dumps(normalized_data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


@app.on_event("startup")
async def startup_event() -> None:
    await init_db()


@app.get("/health")
async def health() -> Dict[str, str]:
    """Health check endpoint returning static JSON."""
    return {"status": "ok"}


@app.post("/v1/ingest")
async def ingest_submission(
    request: Request,
    payload: IngestPayload,
    session: AsyncSession = Depends(get_session),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> JSONResponse:
    """Ingest a payload from an adapter. Returns existing report if hash matches (idempotency)."""
    payload.validate_source()

    # Auth check: compare against DEFAULT_API_KEY env var
    if not x_api_key:
        logger.info("Missing API key", extra={"path": "/v1/ingest", "status": 401})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_api_key", "message": "Missing X-API-Key header"},
        )

    if not settings.default_api_key or x_api_key != settings.default_api_key:
        logger.info("Invalid API key", extra={"path": "/v1/ingest", "status": 403})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "invalid_api_key", "message": "Invalid API key"},
        )

    # Rate limit check (skip if disabled via BPSR_DISABLE_RATELIMIT env var)
    if not settings.disable_ratelimit:
        allowed = await rate_limiter.check(x_api_key)
        if not allowed:
            logger.info("Rate limit exceeded", extra={"path": "/v1/ingest", "status": 429})
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "rate_limit_exceeded", "message": "Rate limit exceeded"},
            )

    # Normalize payload via adapter
    adapter_result = apply_adapter(payload.source, payload.payload)
    
    # Merge normalized fields with raw payload in data JSON
    normalized_data = {
        "normalized": adapter_result,
        "raw": payload.payload,
    }

    # Compute hash for idempotency
    payload_hash = compute_payload_hash(normalized_data)

    # Check for existing report with same hash
    stmt = select(models.Report).where(models.Report.hash == payload_hash)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # Idempotency: return existing report
        logger.info("Duplicate payload detected", extra={"path": "/v1/ingest", "status": 200})
        return JSONResponse({"ok": True, "id": existing.id}, status_code=200)

    # Create new report
    report = models.Report(
        source=payload.source,
        hash=payload_hash,
        data=normalized_data,
    )

    session.add(report)
    await session.commit()

    logger.info("Report ingested", extra={"path": "/v1/ingest", "status": 200})
    return JSONResponse({"ok": True, "id": report.id})


@app.get("/v1/reports/{id}", response_model=ReportResponse)
async def get_report(
    id: str,
    session: AsyncSession = Depends(get_session),
) -> ReportResponse:
    """Fetch a single report by ID."""
    stmt = select(models.Report).where(models.Report.id == id)
    result = await session.execute(stmt)
    report = result.scalar_one_or_none()

    if not report:
        logger.info("Report not found", extra={"path": f"/v1/reports/{id}", "status": 404})
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "report_not_found", "message": f"Report {id} not found"},
        )

    logger.info("Report retrieved", extra={"path": f"/v1/reports/{id}", "status": 200})
    return ReportResponse(
        id=report.id,
        source=report.source,
        ingested_at=report.ingested_at,
        data=report.data,
    )


@app.get("/v1/reports", response_model=List[ReportResponse])
async def list_reports(
    source: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
) -> List[ReportResponse]:
    """List reports with optional filtering by source and pagination."""
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)

    stmt = select(models.Report).order_by(models.Report.ingested_at.desc())

    if source:
        stmt = stmt.where(models.Report.source == source)

    stmt = stmt.offset(offset).limit(limit)

    result = await session.execute(stmt)
    reports = result.scalars().all()

    logger.info("Reports listed", extra={"path": "/v1/reports", "status": 200})
    return [
        ReportResponse(
            id=report.id,
            source=report.source,
            ingested_at=report.ingested_at,
            data=report.data,
        )
        for report in reports
    ]