"""Smoke tests for ingest and retrieval with idempotency."""

import os
import pytest
import pytest_asyncio
import httpx

from bpsr_crowd_data.main import app
from bpsr_crowd_data.db import init_db
from bpsr_crowd_data.settings import get_settings


@pytest_asyncio.fixture
async def client() -> httpx.AsyncClient:
    """Create async test client with app lifespan."""
    # Set API key for testing - use a consistent key
    test_api_key = "test-key-12345"
    os.environ["DEFAULT_API_KEY"] = test_api_key
    os.environ["BPSR_DISABLE_RATELIMIT"] = "1"  # Disable rate limiting in tests
    
    # Clear settings cache to pick up new env var
    get_settings.cache_clear()
    
    # Reimport app module to get fresh settings
    import importlib
    import bpsr_crowd_data.main as main_module
    importlib.reload(main_module)
    test_app = main_module.app
    
    # Initialize DB before tests
    await init_db()
    
    # Create async client with app lifespan
    async with httpx.AsyncClient(app=test_app, base_url="http://test") as client:
        yield client
    
    # Cleanup
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_smoke_bp_timer(client: httpx.AsyncClient) -> None:
    """Test bp_timer adapter: POST sample payload, GET by ID, verify idempotency."""
    api_key = os.environ.get("DEFAULT_API_KEY", "test-key-12345")
    assert api_key == "test-key-12345", f"Expected test API key, got: {api_key}"
    
    # Sample payload
    payload = {
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

    # 1. POST sample payload → assert 200 and get id
    response = await client.post(
        "/v1/ingest",
        headers={"X-API-Key": api_key},
        json=payload,
    )
    assert response.status_code == 200
    result = response.json()
    assert result["ok"] is True
    report_id = result["id"]
    assert report_id is not None

    # 2. GET /v1/reports/{id} → assert fields present
    response = await client.get(f"/v1/reports/{report_id}")
    assert response.status_code == 200
    report = response.json()
    assert report["id"] == report_id
    assert report["source"] == "bp_timer"
    assert "data" in report
    assert "normalized" in report["data"]
    assert "raw" in report["data"]

    # 3. POST same payload again → assert dedupe (same id or 409 with existing id)
    response = await client.post(
        "/v1/ingest",
        headers={"X-API-Key": api_key},
        json=payload,
    )
    assert response.status_code == 200  # Returns 200 with existing id
    result = response.json()
    assert result["ok"] is True
    # Should return same id due to hash-based idempotency
    assert result["id"] == report_id


@pytest.mark.asyncio
async def test_pagination_and_dedupe(client: httpx.AsyncClient) -> None:
    """Test pagination and idempotency with multiple reports."""
    api_key = os.environ.get("DEFAULT_API_KEY", "test-key-12345")
    
    # Insert 5 reports (mix of bp_timer and bpsr_logs)
    payloads = [
        {
            "source": "bp_timer",
            "payload": {"boss": "Frostclaw", "boss_id": "frostclaw_001", "timestamp": "2024-01-01T12:00:00Z", "hp_percent": 100.0},
        },
        {
            "source": "bpsr_logs",
            "payload": {"fight_id": "fight_001", "player_id": "player_001", "timestamp": "2024-01-01T12:00:01Z", "damage": 1000},
        },
        {
            "source": "bp_timer",
            "payload": {"boss": "Fireclaw", "boss_id": "fireclaw_001", "timestamp": "2024-01-01T12:00:02Z", "hp_percent": 75.0},
        },
        {
            "source": "bpsr_logs",
            "payload": {"fight_id": "fight_002", "player_id": "player_002", "timestamp": "2024-01-01T12:00:03Z", "damage": 2000},
        },
        {
            "source": "bp_timer",
            "payload": {"boss": "Iceclaw", "boss_id": "iceclaw_001", "timestamp": "2024-01-01T12:00:04Z", "hp_percent": 50.0},
        },
    ]
    
    inserted_ids = []
    for payload in payloads:
        response = await client.post(
            "/v1/ingest",
            headers={"X-API-Key": api_key},
            json=payload,
        )
        assert response.status_code == 200
        result = response.json()
        assert result["ok"] is True
        inserted_ids.append(result["id"])
    
    # Test pagination: first page (limit=2, offset=0)
    response = await client.get("/v1/reports?limit=2&offset=0")
    assert response.status_code == 200
    page1 = response.json()
    assert len(page1) == 2
    page1_ids = {r["id"] for r in page1}
    
    # Test pagination: second page (limit=2, offset=2)
    response = await client.get("/v1/reports?limit=2&offset=2")
    assert response.status_code == 200
    page2 = response.json()
    assert len(page2) == 2
    page2_ids = {r["id"] for r in page2}
    
    # Assert results are disjoint (no overlapping IDs)
    assert page1_ids.isdisjoint(page2_ids), "Pagination pages should have disjoint results"
    
    # Assert combined size equals at least limit*2 (or we got all results)
    total_seen = len(page1_ids | page2_ids)
    assert total_seen >= 4, f"Expected at least 4 results across 2 pages, got {total_seen}"
    
    # Test idempotency: re-post first payload
    response = await client.post(
        "/v1/ingest",
        headers={"X-API-Key": api_key},
        json=payloads[0],
    )
    assert response.status_code == 200
    result = response.json()
    assert result["ok"] is True
    # Should return same ID due to hash-based idempotency
    assert result["id"] == inserted_ids[0], "Re-posting same payload should return same ID"

