#!/usr/bin/env python
"""Post sample payloads to the local BPSR Crowd Data API."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx


BP_TIMER_SAMPLE = {
    "source": "bp_timer",
    "payload": {
        "boss": "Frostclaw",
        "boss_id": "frostclaw_001",
        "event": "boss_spawn",
        "timestamp": "2024-01-01T12:00:00Z",
        "region": "NA",
        "hp_percent": 100.0,
    },
}

BPSR_LOGS_SAMPLE = {
    "source": "bpsr_logs",
    "payload": {
        "fight_id": "fight_123",
        "player_id": "player_456",
        "damage": 50000,
        "mitigation": 2500,
        "timestamp": "2024-01-01T12:00:00Z",
        "boss": {"name": "Frostclaw"},
        "region": "NA",
        "type": "combat",
    },
}


def post_file(file_path: str, api_key: str, url: str = "http://localhost:8000") -> None:
    """Post a payload from a JSON file."""
    try:
        path = Path(file_path)
        if not path.exists():
            print(f"ERROR: File not found: {file_path}", file=sys.stderr)
            sys.exit(1)
        
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        
        # Validate payload has source field
        if "source" not in payload:
            print("ERROR: JSON file must contain 'source' field", file=sys.stderr)
            sys.exit(1)
        
        # Wrap payload if needed (check if already has payload wrapper)
        if "payload" not in payload:
            # If source is at top level, wrap the entire object
            ingest_payload = {"source": payload.get("source"), "payload": payload}
        else:
            # Already wrapped correctly
            ingest_payload = payload
        
        _post_payload(ingest_payload, api_key, url)
        
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in file: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error reading file: {e}", file=sys.stderr)
        sys.exit(1)


def post_sample(adapter: str, api_key: str, url: str = "http://localhost:8000") -> None:
    """Post a sample payload for the specified adapter."""
    if adapter == "bp_timer":
        payload = BP_TIMER_SAMPLE
    elif adapter == "bpsr_logs":
        payload = BPSR_LOGS_SAMPLE
    else:
        print(f"ERROR: Unknown adapter '{adapter}'. Use 'bp_timer' or 'bpsr_logs'", file=sys.stderr)
        sys.exit(1)
    
    _post_payload(payload, api_key, url)


def _post_payload(payload: dict, api_key: str, url: str) -> None:
    """Post a payload to the API."""
    try:
        response = httpx.post(
            f"{url}/v1/ingest",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=5.0,
        )
        response.raise_for_status()

        result = response.json()
        report_id = result.get("id")
        if report_id:
            print(f"SUCCESS: Report ingested with ID: {report_id}")
        else:
            print(f"SUCCESS: {result}")
    except httpx.HTTPStatusError as e:
        error_detail = e.response.json() if e.response.headers.get("content-type", "").startswith("application/json") else e.response.text
        print(f"ERROR: HTTP {e.response.status_code}: {error_detail}", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"ERROR: Request failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Post sample payloads to BPSR Crowd Data API")
    parser.add_argument("--file", help="Path to JSON file to post")
    parser.add_argument("--adapter", choices=["bp_timer", "bpsr_logs"], help="Adapter name (required if --file not provided)")
    parser.add_argument("--key", required=True, help="API key (X-API-Key header)")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL (default: http://localhost:8000)")

    args = parser.parse_args()
    
    # Validate that either --file or --adapter is provided
    if not args.file and not args.adapter:
        print("ERROR: Either --file or --adapter must be provided", file=sys.stderr)
        sys.exit(1)
    
    if args.file and args.adapter:
        print("ERROR: Cannot use both --file and --adapter. Use one or the other.", file=sys.stderr)
        sys.exit(1)
    
    if args.file:
        post_file(args.file, args.key, args.url)
    else:
        post_sample(args.adapter, args.key, args.url)


if __name__ == "__main__":
    main()

