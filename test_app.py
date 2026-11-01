from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_home_returns_message():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()