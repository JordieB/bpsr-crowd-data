from __future__ import annotations

import argparse
import asyncio
from typing import Optional

from sqlalchemy import text

from .db import apply_migrations, engine


async def _apply() -> None:
    await apply_migrations()


async def _seed_key(key: str, label: Optional[str]) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO api_keys(key, label) VALUES (:key, :label) "
                "ON CONFLICT(key) DO NOTHING"
            ),
            {"key": key, "label": label or "manual"},
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Utility commands for BPSR crowd data")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("apply", help="Apply database migrations")

    seed = sub.add_parser("seed-key", help="Insert an API key")
    seed.add_argument("key", help="API key value")
    seed.add_argument("--label", help="Optional label", default="seeded")

    args = parser.parse_args()

    if args.command == "apply":
        asyncio.run(_apply())
    elif args.command == "seed-key":
        asyncio.run(_seed_key(args.key, args.label))


if __name__ == "__main__":
    main()
