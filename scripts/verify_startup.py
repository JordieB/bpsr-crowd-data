#!/usr/bin/env python
"""Verify that bpsr_crowd_data can be imported and the app starts correctly."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

import httpx

# Fix Windows encoding issues
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure _scratch directory exists
_scratch_dir = Path("_scratch")
_scratch_dir.mkdir(exist_ok=True)

log_file = _scratch_dir / "startup_check.log"


def log_message(message: str) -> None:
    """Write timestamped message to log file."""
    timestamp = datetime.utcnow().isoformat()
    log_line = f"[{timestamp}] {message}\n"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(log_line)
    print(message)


async def verify_startup() -> bool:
    """Import and test the FastAPI app."""
    try:
        log_message("Attempting to import bpsr_crowd_data.main...")
        from bpsr_crowd_data.main import app

        log_message("[OK] Successfully imported bpsr_crowd_data.main")

        log_message("Creating httpx.AsyncClient with app...")
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            log_message("Sending GET request to /health...")
            response = await client.get("/health")
            
            if response.status_code == 200:
                data = response.json()
                if data == {"status": "ok"}:
                    log_message("[OK] Health check passed: /health returned 200 with correct JSON")
                    return True
                else:
                    log_message(f"[FAIL] Health check failed: unexpected response data: {data}")
                    return False
            else:
                log_message(f"[FAIL] Health check failed: got status {response.status_code}")
                return False

    except ImportError as e:
        log_message(f"[FAIL] Import failed: {e}")
        log_message("Make sure to run 'poetry install' to install the package")
        return False
    except Exception as e:
        log_message(f"[FAIL] Unexpected error: {type(e).__name__}: {e}")
        import traceback
        log_message(f"Traceback:\n{traceback.format_exc()}")
        return False


def main() -> None:
    """Main entry point."""
    log_message("=" * 60)
    log_message("Starting startup verification...")
    log_message("=" * 60)

    try:
        success = asyncio.run(verify_startup())
        if success:
            log_message("=" * 60)
            log_message("[OK] startup ok")
            log_message("=" * 60)
            sys.exit(0)
        else:
            log_message("=" * 60)
            log_message("[FAIL] startup verification failed")
            log_message("=" * 60)
            sys.exit(1)
    except Exception as e:
        log_message(f"[FAIL] Fatal error: {e}")
        import traceback
        log_message(f"Traceback:\n{traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()

