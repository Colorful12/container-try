import os
import sys
from fastapi.testclient import TestClient
from main import app

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
