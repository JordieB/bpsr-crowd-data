from __future__ import annotations

import asyncio
from pathlib import Path
from typing import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .settings import get_settings


_settings = get_settings()

engine: AsyncEngine = create_async_engine(_settings.database_url, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


def _migration_sql_for_dialect(dialect: str) -> str:
    migration_path = Path("db/migrations/0001_init.sql")
    if not migration_path.exists():
        raise FileNotFoundError("Migration file not found: db/migrations/0001_init.sql")

    blocks: dict[str, list[str]] = {}
    current: str | None = None
    for line in migration_path.read_text().splitlines():
        if line.startswith("-- dialect:"):
            current = line.split(":", 1)[1].strip()
            blocks[current] = []
            continue
        if current is None:
            blocks.setdefault("default", []).append(line)
        else:
            blocks[current].append(line)

    target = blocks.get(dialect) or blocks.get("default")
    if not target:
        raise ValueError(f"No migration block found for dialect '{dialect}'")
    return "\n".join(target).strip()


async def apply_migrations() -> None:
    sql = _migration_sql_for_dialect(engine.dialect.name)
    if not sql:
        return
    async with engine.begin() as conn:
        statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]
        for statement in statements:
            await conn.execute(text(statement))


async def init_db() -> None:
    await apply_migrations()


def run_sync(func) -> None:
    asyncio.run(func())
