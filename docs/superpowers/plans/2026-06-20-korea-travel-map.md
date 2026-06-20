# Korea Travel Map — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 대한민국 시/군 단위 SVG 지도를 웹에 띄우고 방문 지역을 색칠하며 Immich 사진을 볼 수 있는 FastAPI+Docker 서비스를 포트 8094에 배포한다.

**Architecture:** FastAPI 단일 컨테이너가 REST API + 정적 파일 서빙을 담당. SQLite(`/data/travel.db`)에 색상 기록 저장. 브라우저에서 D3.js v7로 SVG 지도 렌더링, Immich API 프록시는 백엔드가 처리해 API 키가 브라우저에 노출되지 않도록 한다.

**Tech Stack:** Python 3.11, FastAPI, SQLite(표준 라이브러리), httpx, respx(테스트), D3.js v7(CDN), Docker

---

## 파일 구조

```
korea_travel_map/
├── Dockerfile
├── requirements.txt
├── main.py             # FastAPI 앱 + 라우트
├── db.py               # SQLite CRUD
├── immich.py           # Immich API 클라이언트
├── geojson/
│   ├── preprocess.py   # 1회성 전처리 스크립트 (로컬 실행)
│   └── korea_sigun.geojson  # 전처리 완료 데이터 (커밋)
├── static/
│   ├── index.html
│   ├── style.css
│   └── map.js
└── tests/
    ├── conftest.py
    ├── test_db.py
    ├── test_api.py
    └── test_immich.py
```

---

## Task 1: GeoJSON 전처리 (로컬 1회 실행)

**Files:**
- Create: `korea_travel_map/geojson/preprocess.py`
- Output: `korea_travel_map/geojson/korea_sigun.geojson`

- [ ] **Step 1: 로컬에 geopandas 설치 및 원본 데이터 다운로드**

```bash
pip install geopandas requests
mkdir -p /home/tak/home_server/korea_travel_map/geojson
cd /home/tak/home_server/korea_travel_map/geojson
curl -L -o raw_sigungu.geojson \
  "https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2018/json/skorea_municipalities_2018_geo.json"
```

- [ ] **Step 2: 원본 데이터 구조 확인**

```bash
python3 -c "
import json
with open('raw_sigungu.geojson') as f:
    data = json.load(f)
feat = data['features'][0]
print('property keys:', list(feat['properties'].keys()))
print('sample:', feat['properties'])
"
```

Expected: `code`, `name`, `name_eng` 필드 확인 (다르면 Step 3에서 필드명 조정)

- [ ] **Step 3: 전처리 스크립트 작성**

`korea_travel_map/geojson/preprocess.py`:
```python
"""
시/군/구 GeoJSON을 시/군 단위로 병합하는 전처리 스크립트.
실행: python preprocess.py
"""
import geopandas as gpd
import json

# 광역시/특별시/특별자치시: 코드 앞 2자리 → 시 이름
METRO = {
    "11": "서울특별시",
    "26": "부산광역시",
    "27": "대구광역시",
    "28": "인천광역시",
    "29": "광주광역시",
    "30": "대전광역시",
    "31": "울산광역시",
    "36": "세종특별자치시",
}

# 도내 구가 있는 시: 코드 앞 4자리 → 시 이름
GU_TO_SI = {
    "4111": "수원시",
    "4113": "성남시",
    "4117": "안양시",
    "4127": "안산시",
    "4128": "고양시",
    "4146": "용인시",
    "4311": "청주시",
    "4511": "전주시",
    "4711": "포항시",
    "4812": "창원시",
    "4413": "천안시",
}

def get_merge_key(row) -> str:
    code = str(row["code"]).zfill(5)
    name = row["name"]

    # 광역시/특별시 내 구 → 시 단위로
    if code[:2] in METRO:
        return METRO[code[:2]]

    # 도내 시 내 구 → 시 단위로
    if code[:4] in GU_TO_SI:
        return GU_TO_SI[code[:4]]

    return name


gdf = gpd.read_file("raw_sigungu.geojson")
gdf["merge_key"] = gdf.apply(get_merge_key, axis=1)
merged = gdf.dissolve(by="merge_key").reset_index()[["merge_key", "geometry"]]
merged = merged.rename(columns={"merge_key": "name"})
merged.to_file("korea_sigun.geojson", driver="GeoJSON")
print(f"완료: {len(merged)}개 단위 생성")
```

- [ ] **Step 4: 스크립트 실행 및 결과 확인**

```bash
cd /home/tak/home_server/korea_travel_map/geojson
python3 preprocess.py
```

Expected: `완료: 160개 단위 생성` (150~180개 사이면 정상)

```bash
python3 -c "
import json
with open('korea_sigun.geojson') as f:
    data = json.load(f)
names = [f['properties']['name'] for f in data['features']]
print(f'총 {len(names)}개')
print('서울특별시 포함:', '서울특별시' in names)
print('수원시 포함:', '수원시' in names)
print('장안구 포함(없어야 함):', '장안구' in names)
"
```

Expected:
```
총 16X개
서울특별시 포함: True
수원시 포함: True
장안구 포함(없어야 함): False
```

- [ ] **Step 5: raw 파일 삭제, 결과 커밋**

```bash
rm /home/tak/home_server/korea_travel_map/geojson/raw_sigungu.geojson
git add korea_travel_map/geojson/
git commit -m "feat(korea-travel-map): add preprocessed sigun GeoJSON"
```

---

## Task 2: 프로젝트 기본 구조

**Files:**
- Create: `korea_travel_map/requirements.txt`
- Create: `korea_travel_map/Dockerfile`

- [ ] **Step 1: requirements.txt 작성**

`korea_travel_map/requirements.txt`:
```
fastapi==0.111.0
uvicorn==0.29.0
httpx==0.27.0
pytest==8.2.0
pytest-asyncio==0.23.7
respx==0.21.1
```

- [ ] **Step 2: Dockerfile 작성**

`korea_travel_map/Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: 빈 디렉토리 및 파일 생성 확인**

```bash
mkdir -p /home/tak/home_server/korea_travel_map/static
mkdir -p /home/tak/home_server/korea_travel_map/tests
touch /home/tak/home_server/korea_travel_map/tests/__init__.py
ls /home/tak/home_server/korea_travel_map/
```

Expected: `Dockerfile  geojson/  requirements.txt  static/  tests/`

- [ ] **Step 4: 커밋**

```bash
git add korea_travel_map/
git commit -m "feat(korea-travel-map): project scaffold"
```

---

## Task 3: SQLite DB 모듈

**Files:**
- Create: `korea_travel_map/db.py`
- Create: `korea_travel_map/tests/test_db.py`

- [ ] **Step 1: 테스트 먼저 작성**

`korea_travel_map/tests/test_db.py`:
```python
import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import db

@pytest.fixture(autouse=True)
def tmp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

def test_empty_returns_empty_dict():
    assert db.get_all_colors() == {}

def test_set_and_get():
    db.set_color("서울특별시", "#ff0000")
    assert db.get_all_colors()["서울특별시"] == "#ff0000"

def test_replace():
    db.set_color("부산광역시", "#ff0000")
    db.set_color("부산광역시", "#0000ff")
    assert db.get_all_colors()["부산광역시"] == "#0000ff"

def test_delete():
    db.set_color("대구광역시", "#ff0000")
    db.delete_color("대구광역시")
    assert "대구광역시" not in db.get_all_colors()

def test_delete_nonexistent_is_noop():
    db.delete_color("없는지역")  # 예외 없이 통과해야 함
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /home/tak/home_server/korea_travel_map
python -m pytest tests/test_db.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError: No module named 'db'`

- [ ] **Step 3: db.py 작성**

`korea_travel_map/db.py`:
```python
import sqlite3
from pathlib import Path

DB_PATH = Path("/data/travel.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS region_colors (
                region_id  TEXT PRIMARY KEY,
                color      TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)


def get_all_colors() -> dict[str, str]:
    with get_conn() as conn:
        rows = conn.execute("SELECT region_id, color FROM region_colors").fetchall()
    return {row["region_id"]: row["color"] for row in rows}


def set_color(region_id: str, color: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO region_colors (region_id, color) VALUES (?, ?)",
            (region_id, color),
        )


def delete_color(region_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM region_colors WHERE region_id = ?", (region_id,))
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /home/tak/home_server/korea_travel_map
python -m pytest tests/test_db.py -v
```

Expected: `5 passed`

- [ ] **Step 5: 커밋**

```bash
git add korea_travel_map/db.py korea_travel_map/tests/
git commit -m "feat(korea-travel-map): sqlite db module with tests"
```

---

## Task 4: Immich 클라이언트

**Files:**
- Create: `korea_travel_map/immich.py`
- Create: `korea_travel_map/tests/test_immich.py`

- [ ] **Step 1: 테스트 먼저 작성**

`korea_travel_map/tests/test_immich.py`:
```python
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
    """메타데이터 검색과 앨범 검색에서 같은 asset이 나오면 중복 제거"""
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /home/tak/home_server/korea_travel_map
python -m pytest tests/test_immich.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'immich'`

- [ ] **Step 3: immich.py 작성**

`korea_travel_map/immich.py`:
```python
import httpx


def _keyword(region_name: str) -> str:
    """지역명에서 검색 키워드 추출: "수원시" → "수원", "서울특별시" → "서울" """
    for suffix in ("특별자치시", "광역시", "특별시", "특별자치도", "시", "군", "구"):
        if region_name.endswith(suffix):
            return region_name[: -len(suffix)]
    return region_name


class ImmichClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {"x-api-key": api_key}

    async def search_by_region(self, region_name: str) -> list[dict]:
        keyword = _keyword(region_name)
        results: dict[str, dict] = {}

        async with httpx.AsyncClient(headers=self.headers, timeout=10) as client:
            # 1. EXIF city 기반 검색
            try:
                resp = await client.post(
                    f"{self.base_url}/api/search/metadata",
                    json={"city": keyword, "size": 100, "page": 1},
                )
                if resp.status_code == 200:
                    for asset in resp.json().get("assets", {}).get("items", []):
                        results[asset["id"]] = {
                            "id": asset["id"],
                            "date": asset.get("localDateTime", ""),
                        }
            except Exception:
                pass

            # 2. 앨범명 기반 검색
            try:
                resp = await client.get(f"{self.base_url}/api/albums")
                if resp.status_code == 200:
                    matching = [a for a in resp.json() if keyword in a.get("albumName", "")]
                    for album in matching:
                        detail = await client.get(f"{self.base_url}/api/albums/{album['id']}")
                        if detail.status_code == 200:
                            for asset in detail.json().get("assets", []):
                                results[asset["id"]] = {
                                    "id": asset["id"],
                                    "date": asset.get("localDateTime", ""),
                                }
            except Exception:
                pass

        return sorted(results.values(), key=lambda x: x["date"], reverse=True)[:100]

    async def get_thumbnail(self, asset_id: str) -> bytes:
        async with httpx.AsyncClient(headers=self.headers, timeout=10) as client:
            resp = await client.get(f"{self.base_url}/api/assets/{asset_id}/thumbnail")
            resp.raise_for_status()
            return resp.content
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /home/tak/home_server/korea_travel_map
python -m pytest tests/test_immich.py -v
```

Expected: `4 passed`

- [ ] **Step 5: 커밋**

```bash
git add korea_travel_map/immich.py korea_travel_map/tests/test_immich.py
git commit -m "feat(korea-travel-map): immich client with tests"
```

---

## Task 5: FastAPI 앱 + 전체 API

**Files:**
- Create: `korea_travel_map/main.py`
- Create: `korea_travel_map/tests/test_api.py`

- [ ] **Step 1: API 테스트 작성**

`korea_travel_map/tests/test_api.py`:
```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd /home/tak/home_server/korea_travel_map
python -m pytest tests/test_api.py -v 2>&1 | head -10
```

Expected: `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: main.py 작성**

`korea_travel_map/main.py`:
```python
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db
from immich import ImmichClient

GEOJSON_PATH = Path(__file__).parent / "geojson" / "korea_sigun.geojson"
immich_client: ImmichClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    global immich_client
    db.init_db()
    immich_client = ImmichClient(
        os.environ["IMMICH_URL"],
        os.environ["IMMICH_API_KEY"],
    )
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/api/geojson")
def get_geojson():
    if not GEOJSON_PATH.exists():
        raise HTTPException(status_code=500, detail="GeoJSON not found")
    return Response(GEOJSON_PATH.read_text(), media_type="application/json")


@app.get("/api/regions")
def get_regions():
    return db.get_all_colors()


class ColorPayload(BaseModel):
    color: str


@app.put("/api/regions/{region_id}")
def set_region(region_id: str, payload: ColorPayload):
    db.set_color(region_id, payload.color)
    return {"ok": True}


@app.delete("/api/regions/{region_id}")
def delete_region(region_id: str):
    db.delete_color(region_id)
    return {"ok": True}


@app.get("/api/photos/{region_id}")
async def get_photos(region_id: str):
    return await immich_client.search_by_region(region_id)


@app.get("/api/thumbnails/{asset_id}")
async def get_thumbnail(asset_id: str):
    try:
        data = await immich_client.get_thumbnail(asset_id)
        return Response(data, media_type="image/jpeg")
    except Exception:
        raise HTTPException(status_code=502, detail="Immich thumbnail fetch failed")


app.mount("/", StaticFiles(directory=str(Path(__file__).parent / "static"), html=True))
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
cd /home/tak/home_server/korea_travel_map
python -m pytest tests/test_api.py -v
```

Expected: `4 passed`

- [ ] **Step 5: 커밋**

```bash
git add korea_travel_map/main.py korea_travel_map/tests/test_api.py
git commit -m "feat(korea-travel-map): fastapi app with full api"
```

---

## Task 6: 프론트엔드 HTML + CSS

**Files:**
- Create: `korea_travel_map/static/index.html`
- Create: `korea_travel_map/static/style.css`

- [ ] **Step 1: index.html 작성**

`korea_travel_map/static/index.html`:
```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>나의 여행 지도</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body>
  <div id="toolbar">
    <span class="label">🗺️ 나의 대한민국 여행 지도</span>
    <span id="counter">방문: <strong id="visit-count">0</strong>곳</span>
  </div>

  <div id="app">
    <div id="map-container">
      <svg id="map"></svg>

      <!-- 컬러 피커 팝업 -->
      <div id="color-popup" class="hidden">
        <div id="popup-region-name"></div>
        <input type="color" id="color-input" value="#4CAF50">
        <div id="popup-actions">
          <button id="btn-apply">색칠</button>
          <button id="btn-clear">지우기</button>
          <button id="btn-cancel">취소</button>
        </div>
      </div>
    </div>

    <div id="photo-panel">
      <div id="panel-header">
        <div id="panel-region"></div>
        <div id="panel-count"></div>
      </div>
      <div id="photo-grid"></div>
      <div id="panel-empty" class="hidden">지역을 클릭하면 사진이 표시됩니다</div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
  <script src="/map.js"></script>
</body>
</html>
```

- [ ] **Step 2: style.css 작성**

`korea_travel_map/static/style.css`:
```css
* { box-sizing: border-box; margin: 0; padding: 0; }

body { font-family: 'Malgun Gothic', sans-serif; background: #f5f5f5; height: 100vh; display: flex; flex-direction: column; }

#toolbar {
  display: flex; align-items: center; gap: 16px;
  padding: 10px 16px; background: #fff; border-bottom: 1px solid #ddd;
  font-size: 14px;
}
.label { font-weight: 700; color: #333; }
#counter { margin-left: auto; color: #666; }
#counter strong { color: #1a73e8; }

#app { display: flex; flex: 1; overflow: hidden; }

#map-container {
  flex: 1; background: #fff; position: relative;
  display: flex; align-items: center; justify-content: center;
}

#map { width: 100%; height: 100%; }

.region {
  fill: #fff; stroke: #333; stroke-width: 0.5px; cursor: pointer;
  transition: fill 0.15s;
}
.region:hover { stroke: #000; stroke-width: 1.2px; filter: brightness(0.9); }

/* 컬러 피커 팝업 */
#color-popup {
  position: absolute; background: #fff; border: 1px solid #ddd;
  border-radius: 8px; padding: 12px; box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  width: 160px; z-index: 100;
}
#color-popup.hidden { display: none; }
#popup-region-name { font-size: 12px; font-weight: 700; color: #333; margin-bottom: 8px; }
#color-input { width: 100%; height: 36px; border: none; border-radius: 4px; cursor: pointer; margin-bottom: 8px; }
#popup-actions { display: flex; gap: 4px; }
#popup-actions button { flex: 1; padding: 5px; border: none; border-radius: 4px; cursor: pointer; font-size: 11px; }
#btn-apply { background: #1a73e8; color: #fff; }
#btn-clear { background: #f0f0f0; color: #555; }
#btn-cancel { background: #f0f0f0; color: #999; }

/* 사진 패널 */
#photo-panel {
  width: 260px; border-left: 1px solid #e8e8e8; background: #fafafa;
  display: flex; flex-direction: column; overflow: hidden;
}
#panel-header {
  padding: 10px 12px; border-bottom: 1px solid #e8e8e8;
  font-size: 13px; flex-shrink: 0;
}
#panel-region { font-weight: 700; color: #222; }
#panel-count { font-size: 11px; color: #999; margin-top: 2px; }

#photo-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 4px;
  padding: 8px; overflow-y: auto; flex: 1;
}

.photo-thumb {
  aspect-ratio: 1; border-radius: 4px; object-fit: cover;
  cursor: pointer; background: #e0e0e0;
}
.photo-thumb:hover { opacity: 0.85; }

#panel-empty {
  padding: 20px; text-align: center; color: #bbb; font-size: 13px; margin-top: 40px;
}
#panel-empty.hidden { display: none; }
```

- [ ] **Step 3: 커밋**

```bash
git add korea_travel_map/static/index.html korea_travel_map/static/style.css
git commit -m "feat(korea-travel-map): frontend html and css"
```

---

## Task 7: D3 SVG 지도 렌더링 + 인터랙션

**Files:**
- Create: `korea_travel_map/static/map.js`

- [ ] **Step 1: map.js 작성**

`korea_travel_map/static/map.js`:
```javascript
(async () => {
  // ── 상태 ──────────────────────────────────────────────
  let regionColors = {};       // { 지역명: "#rrggbb" }
  let selectedRegion = null;   // 현재 선택된 지역명
  let geojson = null;

  // ── SVG 초기화 ─────────────────────────────────────────
  const container = document.getElementById("map-container");
  const svg = d3.select("#map");
  let width = container.clientWidth;
  let height = container.clientHeight;

  const g = svg.append("g");

  const projection = d3.geoMercator();
  const pathGen = d3.geoPath().projection(projection);

  // ── 데이터 로드 ────────────────────────────────────────
  const [geoData, colorData] = await Promise.all([
    fetch("/api/geojson").then(r => r.json()),
    fetch("/api/regions").then(r => r.json()),
  ]);
  geojson = geoData;
  regionColors = colorData;

  // ── 지도 렌더링 ────────────────────────────────────────
  function render() {
    width = container.clientWidth;
    height = container.clientHeight;
    svg.attr("viewBox", `0 0 ${width} ${height}`);

    projection.fitSize([width, height], geojson);

    g.selectAll(".region").remove();
    g.selectAll(".region")
      .data(geojson.features)
      .join("path")
      .attr("class", "region")
      .attr("d", pathGen)
      .attr("fill", d => regionColors[d.properties.name] || "#ffffff")
      .on("click", onRegionClick);

    updateCounter();
  }

  render();
  window.addEventListener("resize", render);

  // ── 카운터 업데이트 ────────────────────────────────────
  function updateCounter() {
    document.getElementById("visit-count").textContent =
      Object.keys(regionColors).length;
  }

  // ── 지역 클릭 핸들러 ───────────────────────────────────
  function onRegionClick(event, d) {
    const name = d.properties.name;
    selectedRegion = name;

    // 컬러 피커 팝업 위치 설정
    const popup = document.getElementById("color-popup");
    document.getElementById("popup-region-name").textContent = name;
    document.getElementById("color-input").value = regionColors[name] || "#4CAF50";

    const rect = container.getBoundingClientRect();
    let x = event.clientX - rect.left + 10;
    let y = event.clientY - rect.top - 20;
    // 팝업이 화면 밖으로 나가지 않도록
    if (x + 170 > width) x = width - 175;
    if (y + 120 > height) y = height - 125;

    popup.style.left = x + "px";
    popup.style.top = y + "px";
    popup.classList.remove("hidden");

    // 사진 패널 로드
    loadPhotos(name);

    event.stopPropagation();
  }

  // 지도 빈 곳 클릭 시 팝업 닫기
  container.addEventListener("click", () => {
    document.getElementById("color-popup").classList.add("hidden");
  });

  // ── 색상 적용 ──────────────────────────────────────────
  document.getElementById("btn-apply").addEventListener("click", async () => {
    if (!selectedRegion) return;
    const color = document.getElementById("color-input").value;
    await fetch(`/api/regions/${encodeURIComponent(selectedRegion)}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ color }),
    });
    regionColors[selectedRegion] = color;
    // SVG 즉시 반영
    g.selectAll(".region")
      .filter(d => d.properties.name === selectedRegion)
      .attr("fill", color);
    document.getElementById("color-popup").classList.add("hidden");
    updateCounter();
  });

  // ── 색상 지우기 ────────────────────────────────────────
  document.getElementById("btn-clear").addEventListener("click", async () => {
    if (!selectedRegion) return;
    await fetch(`/api/regions/${encodeURIComponent(selectedRegion)}`, { method: "DELETE" });
    delete regionColors[selectedRegion];
    g.selectAll(".region")
      .filter(d => d.properties.name === selectedRegion)
      .attr("fill", "#ffffff");
    document.getElementById("color-popup").classList.add("hidden");
    updateCounter();
  });

  document.getElementById("btn-cancel").addEventListener("click", () => {
    document.getElementById("color-popup").classList.add("hidden");
  });

  // ── 사진 패널 ──────────────────────────────────────────
  async function loadPhotos(regionName) {
    const panel = document.getElementById("photo-panel");
    const grid = document.getElementById("photo-grid");
    const empty = document.getElementById("panel-empty");

    document.getElementById("panel-region").textContent = "📍 " + regionName;
    document.getElementById("panel-count").textContent = "불러오는 중...";
    grid.innerHTML = "";

    const photos = await fetch(`/api/photos/${encodeURIComponent(regionName)}`)
      .then(r => r.json());

    if (photos.length === 0) {
      document.getElementById("panel-count").textContent = "사진 없음";
      empty.classList.remove("hidden");
      return;
    }

    empty.classList.add("hidden");
    document.getElementById("panel-count").textContent = `사진 ${photos.length}장`;

    photos.forEach(photo => {
      const img = document.createElement("img");
      img.className = "photo-thumb";
      img.src = `/api/thumbnails/${photo.id}`;
      img.alt = photo.date?.slice(0, 10) || "";
      img.title = photo.date?.slice(0, 10) || "";
      img.loading = "lazy";
      img.addEventListener("click", () => {
        // Immich 원본으로 이동 (새 탭)
        window.open(`${location.origin.replace("8094", "2283")}/photos/${photo.id}`, "_blank");
      });
      grid.appendChild(img);
    });
  }
})();
```

- [ ] **Step 2: 커밋**

```bash
git add korea_travel_map/static/map.js
git commit -m "feat(korea-travel-map): d3 svg map with color picker and photo panel"
```

---

## Task 8: Docker Compose 업데이트 + 배포

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: docker-compose.yml에 서비스 추가**

`docker-compose.yml`의 `volumes:` 섹션 바로 위에 추가:
```yaml
  # ──────────────────────────────────────────
  # 나의 여행 지도 — 대한민국 방문 기록
  # 접속: http://서버IP:8094
  # ──────────────────────────────────────────
  korea-travel-map:
    build: ./korea_travel_map
    image: korea-travel-map:latest
    container_name: korea-travel-map
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"
    ports:
      - "8094:8000"
    volumes:
      - korea_travel_data:/data
    environment:
      - IMMICH_URL=http://host.docker.internal:2283
      - IMMICH_API_KEY=여기에_API_키_입력
```

`volumes:` 섹션에도 추가:
```yaml
  korea_travel_data:
```

- [ ] **Step 2: Immich API 키 확인 및 입력**

```
Immich 웹 UI → 우상단 프로필 → Account Settings → API Keys → New API Key
생성 후 키를 복사해서 docker-compose.yml의 IMMICH_API_KEY 값에 입력
```

- [ ] **Step 3: 전체 테스트 실행**

```bash
cd /home/tak/home_server/korea_travel_map
python -m pytest tests/ -v
```

Expected: `모든 테스트 통과`

- [ ] **Step 4: Docker 빌드 및 실행**

```bash
cd /home/tak/home_server
docker compose build korea-travel-map
docker compose up -d korea-travel-map
docker compose logs korea-travel-map --tail=20
```

Expected: `Application startup complete.`

- [ ] **Step 5: 동작 확인**

```bash
curl http://localhost:8094/api/geojson | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'지역 수: {len(d[\"features\"])}')"
curl http://localhost:8094/api/regions
```

Expected:
```
지역 수: 16X
{}
```

- [ ] **Step 6: 커밋**

```bash
cd /home/tak/home_server
git add docker-compose.yml
git commit -m "feat: add korea-travel-map service to docker-compose"
```

---

## 완료 기준

- [ ] `http://서버IP:8094` 접속 시 한국 지도 SVG가 렌더링된다
- [ ] 지역 클릭 → 컬러 피커 → 색칠 후 새로고침해도 색상 유지
- [ ] 색칠된 지역 클릭 → 우측 패널에 Immich 썸네일 표시
- [ ] 썸네일 클릭 → Immich 원본으로 이동
