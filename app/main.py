from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models
from .adapters import apply_adapter
from .db import get_session, init_db
from .settings import get_settings


ALLOWED_SOURCES = {"bp_timer", "bpsr_logs", "manual", "other"}
ALLOWED_CATEGORIES = {"combat", "heal", "boss_event", "trade"}

settings = get_settings()

app = FastAPI(title="BPSR Crowd Data", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.allowed_origins else settings.allowed_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"]
)


class IngestPayload(BaseModel):
    source: str
    category: str
    region: Optional[str] = None
    boss_name: Optional[str] = None
    payload: Dict[str, Any]

    def validate_enums(self) -> None:
        if self.source not in ALLOWED_SOURCES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid source")
        if self.category not in ALLOWED_CATEGORIES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid category")


class SubmissionResponse(BaseModel):
    id: str
    source: str
    category: str
    region: Optional[str]
    boss_name: Optional[str]
    payload: Dict[str, Any]
    ingested_at: datetime


class RateLimiter:
    def __init__(self, limit_per_minute: int) -> None:
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


rate_limiter = RateLimiter(settings.rate_limit_per_minute)


@app.on_event("startup")
async def startup_event() -> None:
    await init_db()


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/.well-known/health")
async def well_known_health() -> Dict[str, str]:
    return await health()


def _status_html(counts: Dict[str, int]) -> str:
    total = sum(counts.values())
    health = "✅" if total >= 0 else "❌"
    curl_snippet = (
        "curl -X POST https://<your-app>/v1/ingest "
        "-H 'X-API-Key: <your-key>' -H 'Content-Type: application/json' "
        "-d '{\"source\":\"bp_timer\",\"category\":\"boss_event\",\"region\":\"NA\",\"payload\":{}}'"
    )
    rows = "".join(
        f"<tr><td>{category}</td><td>{count}</td></tr>" for category, count in counts.items()
    )
    return f"""
    <html>
      <head>
        <title>BPSR Crowd Data</title>
        <style>body{{font-family:Arial,sans-serif;margin:2rem}}table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:0.5rem}}</style>
      </head>
      <body>
        <h1>Blue Protocol: Star Resonance Crowd Data</h1>
        <p>API health: <strong>{health}</strong></p>
        <h2>Records in last 24h</h2>
        <table>
          <tr><th>Category</th><th>Count</th></tr>
          {rows or '<tr><td colspan="2">No data yet</td></tr>'}
        </table>
        <h2>Submit data</h2>
        <pre>{curl_snippet}</pre>
        <p>OpenAPI docs available at <a href="/docs">/docs</a>.</p>
      </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
async def status_page(session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    since = datetime.utcnow() - timedelta(hours=24)
    stmt: Select = (
        select(models.Submission.category, func.count())
        .where(models.Submission.ingested_at >= since)
        .group_by(models.Submission.category)
    )
    result = await session.execute(stmt)
    raw_counts = {row[0]: row[1] for row in result.all()}
    counts = {category: raw_counts.get(category, 0) for category in sorted(ALLOWED_CATEGORIES)}
    return HTMLResponse(content=_status_html(counts))


async def verify_key(session: AsyncSession, key: str) -> bool:
    stmt = select(models.ApiKey).where(models.ApiKey.key == key)
    res = await session.execute(stmt)
    return res.scalar_one_or_none() is not None


def serialize_submission(submission: models.Submission) -> Dict[str, Any]:
    return {
        "id": submission.id,
        "source": submission.source,
        "category": submission.category,
        "region": submission.region,
        "boss_name": submission.boss_name,
        "payload": submission.payload,
        "ingested_at": submission.ingested_at,
    }


@app.get("/v1/submissions/recent", response_model=List[SubmissionResponse])
async def get_recent(
    category: Optional[str] = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
) -> List[SubmissionResponse]:
    limit = min(max(limit, 1), 200)
    stmt = select(models.Submission).order_by(models.Submission.ingested_at.desc()).limit(limit)
    if category:
        stmt = stmt.where(models.Submission.category == category)
    result = await session.execute(stmt)
    submissions = [serialize_submission(row[0]) for row in result.all()]
    return submissions


@app.get("/v1/submissions/search", response_model=List[SubmissionResponse])
async def search_submissions(
    category: Optional[str] = None,
    boss_name: Optional[str] = None,
    since: Optional[datetime] = None,
    session: AsyncSession = Depends(get_session),
) -> List[SubmissionResponse]:
    stmt = select(models.Submission)
    if category:
        stmt = stmt.where(models.Submission.category == category)
    if boss_name:
        stmt = stmt.where(models.Submission.boss_name == boss_name)
    if since:
        stmt = stmt.where(models.Submission.ingested_at >= since)
    stmt = stmt.order_by(models.Submission.ingested_at.desc()).limit(200)
    result = await session.execute(stmt)
    return [serialize_submission(row[0]) for row in result.all()]


@app.get("/v1/export")
async def export_submissions(
    category: Optional[str] = None,
    since: Optional[datetime] = None,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    stmt = select(models.Submission)
    if category:
        stmt = stmt.where(models.Submission.category == category)
    if since:
        stmt = stmt.where(models.Submission.ingested_at >= since)
    stmt = stmt.order_by(models.Submission.ingested_at.desc())

    result = await session.execute(stmt)
    rows = [row[0] for row in result.all()]

    async def streamer() -> AsyncGenerator[bytes, None]:
        for submission in rows:
            payload = serialize_submission(submission)
            yield json.dumps(payload, default=str).encode("utf-8") + b"\n"

    return StreamingResponse(streamer(), media_type="application/jsonlines")


@app.post("/v1/ingest")
async def ingest_submission(
    request: Request,
    payload: IngestPayload,
    session: AsyncSession = Depends(get_session),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> JSONResponse:
    payload.validate_enums()

    if settings.allowed_origins and request.headers.get("origin") not in settings.allowed_origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin not allowed")

    if not x_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    if not await verify_key(session, x_api_key):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")

    allowed = await rate_limiter.check(x_api_key)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")

    incoming = payload.model_dump()
    adapter_meta = apply_adapter(payload.source, payload.payload)

    category = adapter_meta.get("category", incoming["category"])
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid category")

    boss_name = adapter_meta.get("boss_name") or incoming.get("boss_name")
    region = adapter_meta.get("region") or incoming.get("region")
    prepared_payload = dict(payload.payload)
    if "payload_metadata" in adapter_meta:
        if not isinstance(prepared_payload.get("metadata"), dict):
            prepared_payload["metadata"] = {}
        prepared_payload["metadata"].update(adapter_meta["payload_metadata"])

    submission = models.Submission(
        source=payload.source,
        category=category,
        region=region,
        boss_name=boss_name,
        payload=prepared_payload,
    )

    session.add(submission)
    await session.commit()

    return JSONResponse({"ok": True, "id": submission.id})


@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.method == "GET":
        response.headers.setdefault("Cache-Control", "public, max-age=15")
    return response
