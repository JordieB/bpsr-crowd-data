#!/usr/bin/env python
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import uuid

import httpx

BASE_PORT = int(os.environ.get("SMOKE_PORT", "8070"))
BASE_URL = f"http://127.0.0.1:{BASE_PORT}"
API_KEY = os.environ.get("SMOKE_API_KEY", "smoke-test-key")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./smoke.db")


def run_cmd(args: list[str], env: dict[str, str]) -> None:
    result = subprocess.run(args, check=True, env=env)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def wait_for_ready(url: str, timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=2.0)
            if response.status_code == 200:
                return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"Service not ready after {timeout} seconds")


def main() -> None:
    env = os.environ.copy()
    env.setdefault("DATABASE_URL", DATABASE_URL)

    run_cmd([sys.executable, "-m", "bpsr_crowd_data.cli_db", "apply"], env)
    run_cmd([sys.executable, "-m", "bpsr_crowd_data.cli_db", "seed-key", API_KEY, "--label", "smoke"], env)

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "bpsr_crowd_data.main:app", "--port", str(BASE_PORT)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        wait_for_ready(f"{BASE_URL}/health")
        client = httpx.Client(base_url=BASE_URL)
        payload_id = str(uuid.uuid4())
        ingest_payload = {
            "source": "bp_timer",
            "category": "boss_event",
            "region": "NA",
            "boss_name": "Test Boss",
            "payload": {"note": "smoke", "uuid": payload_id},
        }
        ingest_resp = client.post(
            "/v1/ingest",
            headers={"X-API-Key": API_KEY},
            json=ingest_payload,
            timeout=5.0,
        )
        ingest_resp.raise_for_status()
        returned_id = ingest_resp.json()["id"]

        recent_resp = client.get(
            "/v1/submissions/recent",
            params={"category": "boss_event", "limit": 1},
            timeout=5.0,
        )
        recent_resp.raise_for_status()
        data = recent_resp.json()
        if not data or data[0]["id"] != returned_id:
            raise RuntimeError("Smoke test failed: submission not retrievable")

        print("SMOKE OK")
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    main()
