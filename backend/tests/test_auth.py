import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_auth_without_init_data():
    response = client.post("/api/v1/auth/telegram")
    assert response.status_code == 401
