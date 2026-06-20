import pytest
import httpx
import respx
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from immich import ImmichClient

BASE = "http://immich:2283"

@pytest.fixture
def client():
    return ImmichClient(BASE, "test-key")

@pytest.mark.asyncio
@respx.mock
async def test_metadata_search(client):
    respx.post(f"{BASE}/api/search/metadata").mock(return_value=httpx.Response(
        200,
        json={"assets": {"items": [{"id": "aaa", "localDateTime": "2024-01-01T00:00:00"}]}},
    ))
    respx.get(f"{BASE}/api/albums").mock(return_value=httpx.Response(200, json=[]))

    results = await client.search_by_region("서울특별시")
    assert any(r["id"] == "aaa" for r in results)

@pytest.mark.asyncio
@respx.mock
async def test_album_search(client):
    respx.post(f"{BASE}/api/search/metadata").mock(return_value=httpx.Response(
        200, json={"assets": {"items": []}}
    ))
    respx.get(f"{BASE}/api/albums").mock(return_value=httpx.Response(
        200, json=[{"id": "album1", "albumName": "강릉 여행"}]
    ))
    respx.get(f"{BASE}/api/albums/album1").mock(return_value=httpx.Response(
        200, json={"assets": [{"id": "bbb", "localDateTime": "2024-06-01T00:00:00"}]}
    ))

    results = await client.search_by_region("강릉시")
    assert any(r["id"] == "bbb" for r in results)

@pytest.mark.asyncio
@respx.mock
async def test_deduplication(client):
    respx.post(f"{BASE}/api/search/metadata").mock(return_value=httpx.Response(
        200,
        json={"assets": {"items": [{"id": "same", "localDateTime": "2024-01-01T00:00:00"}]}},
    ))
    respx.get(f"{BASE}/api/albums").mock(return_value=httpx.Response(
        200, json=[{"id": "album1", "albumName": "수원"}]
    ))
    respx.get(f"{BASE}/api/albums/album1").mock(return_value=httpx.Response(
        200, json={"assets": [{"id": "same", "localDateTime": "2024-01-01T00:00:00"}]}
    ))

    results = await client.search_by_region("수원시")
    assert len([r for r in results if r["id"] == "same"]) == 1

@pytest.mark.asyncio
@respx.mock
async def test_thumbnail(client):
    respx.get(f"{BASE}/api/assets/abc/thumbnail").mock(
        return_value=httpx.Response(200, content=b"fake-image")
    )
    data = await client.get_thumbnail("abc")
    assert data == b"fake-image"
