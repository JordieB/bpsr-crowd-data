from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON


json_type = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    pass


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source: Mapped[str] = mapped_column(String(32))
    category: Mapped[str] = mapped_column(String(32))
    region: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    boss_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(json_type)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )


Index(
    "idx_submissions_category_ingested_at",
    Submission.category,
    Submission.ingested_at.desc(),
)


class ApiKey(Base):
    __tablename__ = "api_keys"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    label: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
