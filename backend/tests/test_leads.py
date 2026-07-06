import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_leads_unauthorized():
    response = client.get("/api/v1/leads/")
    assert response.status_code == 401
