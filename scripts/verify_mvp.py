#!/usr/bin/env python
"""End-to-end MVP validation script."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import httpx

# Ensure _scratch directory exists
_scratch_dir = Path("_scratch")
_scratch_dir.mkdir(exist_ok=True)


def read_api_key_from_env() -> str | None:
    """Read DEFAULT_API_KEY from .env file."""
    env_file = Path(".env")
    if not env_file.exists():
        return None
    
    try:
        with env_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("DEFAULT_API_KEY="):
                    # Remove quotes if present
                    value = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return value
    except Exception:
        pass
    
    return None


def check_server(url: str) -> bool:
    """Check if server is reachable via /health endpoint."""
    try:
        response = httpx.get(f"{url}/health", timeout=5.0)
        if response.status_code == 200:
            data = response.json()
            return data == {"status": "ok"}
    except Exception:
        pass
    return False


def post_sample_file(file_path: Path, api_key: str, url: str) -> dict:
    """Post a sample file and return result."""
    try:
        with file_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        
        # Wrap payload if needed
        if "payload" not in payload:
            ingest_payload = {"source": payload.get("source"), "payload": payload}
        else:
            ingest_payload = payload
        
        response = httpx.post(
            f"{url}/v1/ingest",
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            json=ingest_payload,
            timeout=5.0,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise RuntimeError(f"Failed to post {file_path}: {e}")


def list_reports(api_key: str, url: str, limit: int = 2, offset: int = 0) -> list:
    """List reports with pagination."""
    try:
        response = httpx.get(
            f"{url}/v1/reports?limit={limit}&offset={offset}",
            timeout=5.0,
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise RuntimeError(f"Failed to list reports: {e}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="End-to-end MVP validation")
    parser.add_argument("--key", help="API key (X-API-Key header). If not provided, reads from .env")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL (default: http://localhost:8000)")
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.key or read_api_key_from_env()
    if not api_key:
        print("ERROR: API key required. Provide --key or set DEFAULT_API_KEY in .env file", file=sys.stderr)
        sys.exit(1)
    
    url = args.url
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "url": url,
        "api_key_preview": f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else api_key,
        "post_results": [],
        "dedupe_result": None,
        "pagination_check": None,
        "exceptions": [],
    }
    
    try:
        # 1. Check server reachability
        print(f"Checking server reachability at {url}...")
        if not check_server(url):
            raise RuntimeError(f"Server not reachable or /health endpoint failed at {url}")
        print("✓ Server is reachable")
        
        # 2. Post sample_bp_timer.json
        print("Posting sample_bp_timer.json...")
        bp_timer_file = _scratch_dir / "sample_bp_timer.json"
        if not bp_timer_file.exists():
            raise RuntimeError(f"Sample file not found: {bp_timer_file}")
        
        bp_timer_result = post_sample_file(bp_timer_file, api_key, url)
        bp_timer_id = bp_timer_result.get("id")
        results["post_results"].append({"file": "sample_bp_timer.json", "id": bp_timer_id})
        print(f"✓ Posted sample_bp_timer.json, ID: {bp_timer_id}")
        
        # 3. Post sample_bpsr_logs.json
        print("Posting sample_bpsr_logs.json...")
        bpsr_logs_file = _scratch_dir / "sample_bpsr_logs.json"
        if not bpsr_logs_file.exists():
            raise RuntimeError(f"Sample file not found: {bpsr_logs_file}")
        
        bpsr_logs_result = post_sample_file(bpsr_logs_file, api_key, url)
        bpsr_logs_id = bpsr_logs_result.get("id")
        results["post_results"].append({"file": "sample_bpsr_logs.json", "id": bpsr_logs_id})
        print(f"✓ Posted sample_bpsr_logs.json, ID: {bpsr_logs_id}")
        
        # 4. Re-post bp_timer sample to confirm dedupe
        print("Re-posting sample_bp_timer.json to confirm dedupe...")
        dedupe_result = post_sample_file(bp_timer_file, api_key, url)
        dedupe_id = dedupe_result.get("id")
        if dedupe_id == bp_timer_id:
            results["dedupe_result"] = {"success": True, "original_id": bp_timer_id, "dedupe_id": dedupe_id}
            print(f"✓ Dedupe confirmed: same ID returned ({dedupe_id})")
        else:
            results["dedupe_result"] = {"success": False, "original_id": bp_timer_id, "dedupe_id": dedupe_id}
            raise RuntimeError(f"Dedupe failed: expected ID {bp_timer_id}, got {dedupe_id}")
        
        # 5. List reports with pagination
        print("Testing pagination (limit=2)...")
        page1 = list_reports(api_key, url, limit=2, offset=0)
        page1_ids = [r["id"] for r in page1]
        results["pagination_check"] = {
            "page1_count": len(page1),
            "page1_ids": page1_ids,
        }
        print(f"✓ Pagination page 1: {len(page1)} reports, IDs: {', '.join(page1_ids[:3])}{'...' if len(page1_ids) > 3 else ''}")
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        results["exceptions"].append({"type": type(e).__name__, "message": str(e)})
        print(f"ERROR: {error_msg}", file=sys.stderr)
        
        # Write partial results
        report_path = _scratch_dir / "MVP_validation.md"
        _write_report(report_path, results)
        
        sys.exit(1)
    
    # Write success report
    report_path = _scratch_dir / "MVP_validation.md"
    _write_report(report_path, results)
    
    print("\n" + "=" * 60)
    print("✓ MVP validation completed successfully")
    print(f"Report written to: {report_path}")
    print("=" * 60)


def _write_report(report_path: Path, results: dict) -> None:
    """Write validation report to markdown file."""
    with report_path.open("w", encoding="utf-8") as f:
        f.write("# MVP Validation Report\n\n")
        f.write(f"**Timestamp**: {results['timestamp']}\n")
        f.write(f"**URL**: {results['url']}\n")
        f.write(f"**API Key Preview**: {results['api_key_preview']}\n\n")
        
        f.write("## Post Results\n\n")
        if results["post_results"]:
            for post_result in results["post_results"]:
                f.write(f"- **{post_result['file']}**: ID `{post_result['id']}`\n")
        else:
            f.write("No posts completed.\n")
        f.write("\n")
        
        f.write("## Dedupe Result\n\n")
        if results["dedupe_result"]:
            dedupe = results["dedupe_result"]
            if dedupe["success"]:
                f.write(f"✓ **Success**: Re-post returned same ID `{dedupe['dedupe_id']}`\n")
            else:
                f.write(f"✗ **Failed**: Expected ID `{dedupe['original_id']}`, got `{dedupe['dedupe_id']}`\n")
        else:
            f.write("Dedupe test not completed.\n")
        f.write("\n")
        
        f.write("## Pagination Check\n\n")
        if results["pagination_check"]:
            pagination = results["pagination_check"]
            f.write(f"- **Page 1** (limit=2, offset=0): {pagination['page1_count']} reports\n")
            f.write(f"- **Report IDs**: {', '.join(f'`{id}`' for id in pagination['page1_ids'])}\n")
        else:
            f.write("Pagination check not completed.\n")
        f.write("\n")
        
        f.write("## Exceptions\n\n")
        if results["exceptions"]:
            for exc in results["exceptions"]:
                f.write(f"- **{exc['type']}**: {exc['message']}\n")
        else:
            f.write("No exceptions occurred.\n")
        f.write("\n")
        
        f.write("---\n\n")
        f.write(f"*Report generated at {results['timestamp']}*\n")


if __name__ == "__main__":
    main()

