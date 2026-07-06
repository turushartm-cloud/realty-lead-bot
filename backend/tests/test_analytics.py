import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_summary_unauthorized():
    response = client.get("/api/v1/analytics/summary")
    assert response.status_code == 401
