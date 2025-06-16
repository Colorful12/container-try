import sys
from pathlib import Path
from fastapi.testclient import TestClient
from main import app

# Add the parent directory to Python path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
