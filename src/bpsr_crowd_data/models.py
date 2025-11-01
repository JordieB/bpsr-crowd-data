from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


json_type = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    pass


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    data: Mapped[dict[str, Any]] = mapped_column(json_type, nullable=False)


Index("idx_reports_hash", Report.hash)
Index("idx_reports_source_ingested_at", Report.source, Report.ingested_at.desc())
