"""Test health endpoint."""

import pytest
from fastapi.testclient import TestClient

from bpsr_crowd_data.main import app


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


def test_health(client: TestClient) -> None:
    """Test health endpoint returns 200 with static JSON."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok"}

