import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sys, os
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("IMMICH_URL", "http://immich:2283")
os.environ.setdefault("IMMICH_API_KEY", "test")

import db
from main import app

@pytest.fixture(autouse=True)
def tmp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

@pytest.fixture
def client():
    return TestClient(app)

def test_get_regions_empty(client):
    resp = client.get("/api/regions")
    assert resp.status_code == 200
    assert resp.json() == {}

def test_put_region(client):
    resp = client.put("/api/regions/서울특별시", json={"color": "#ff0000"})
    assert resp.status_code == 200
    assert client.get("/api/regions").json()["서울특별시"] == "#ff0000"

def test_delete_region(client):
    client.put("/api/regions/부산광역시", json={"color": "#00ff00"})
    client.delete("/api/regions/부산광역시")
    assert "부산광역시" not in client.get("/api/regions").json()

def test_geojson_returns_json(client):
    resp = client.get("/api/geojson")
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 100
