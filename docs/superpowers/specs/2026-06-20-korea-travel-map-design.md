# Korea Travel Map — 설계 문서

**작성일**: 2026-06-20  
**서비스명**: korea-travel-map  
**포트**: 8094

---

## 개요

대한민국 전국 지도를 웹에 띄우고, 여행한 지역을 원하는 색으로 색칠하며 해당 지역의 Immich 사진을 볼 수 있는 개인 여행 기록 서비스.

---

## 지도 단위

- **특별시·광역시·특별자치시** (서울·부산·대구·인천·광주·대전·울산·세종): 시 전체를 단일 단위
- **도 산하 시**: 구가 있더라도 구를 합쳐서 시 단위로 (수원시, 창원시 등)
- **도 산하 군**: 군 단위 그대로
- 결과: 약 160~170개 단위

GeoJSON 데이터는 GADM 또는 행정안전부 공개 데이터를 기반으로 사전 전처리(시/군 병합).

---

## 아키텍처

```
[브라우저]
    │
    ├── GET /              → HTML/JS/CSS (정적 파일)
    ├── GET /api/geojson   → 전처리된 시/군 GeoJSON
    ├── GET /api/regions   → 방문 색상 기록 (SQLite)
    ├── PUT /api/regions/{id}    → 색상 저장
    ├── DELETE /api/regions/{id} → 색상 초기화
    └── GET /api/photos/{region_id} → Immich 사진 프록시
                                          │
                                    [Immich :2283]
```

- **컨테이너 1개**: FastAPI (Uvicorn) — API + 정적 파일 서빙 통합
- **데이터 저장**: SQLite → Docker Volume (`korea_travel_data`)
- **환경변수**: `IMMICH_URL`, `IMMICH_API_KEY`

---

## 데이터 모델

```sql
CREATE TABLE region_colors (
    region_id  TEXT PRIMARY KEY,   -- e.g. "수원시", "강릉시", "서울특별시"
    color      TEXT NOT NULL,      -- e.g. "#4CAF50"
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## API

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/geojson` | 시/군 병합된 GeoJSON 반환 |
| GET | `/api/regions` | 전체 색상 기록 `{region_id: color}` |
| PUT | `/api/regions/{region_id}` | 색상 저장 `{"color": "#4CAF50"}` |
| DELETE | `/api/regions/{region_id}` | 색상 초기화 |
| GET | `/api/photos/{region_id}` | Immich 사진 목록 (썸네일 URL + asset ID) |

### Immich 사진 조회 전략

1. 해당 시/군의 **바운딩 박스**로 GPS 검색 (`POST /api/search/metadata`)
2. Immich **앨범명**에 지역명 포함 여부 검색 (`GET /api/albums`)
3. 두 결과 합산 → 중복 제거 → 날짜 내림차순 정렬
4. 최대 100장 반환

---

## 프론트엔드

**기술**: Vanilla JS + D3.js (CDN) — 빌드 과정 없음

**인터랙션 흐름:**
1. 페이지 로드 → `/api/geojson` + `/api/regions` 동시 fetch
2. D3로 SVG 렌더링, 색상 기록 있는 지역은 저장된 색으로 칠함
3. 지역 클릭 → 컬러 피커 팝업 (`<input type="color">`)
4. 색 확인 → `PUT /api/regions/{id}` → SVG 즉시 갱신
5. 색칠된 지역 재클릭 → 우측 패널에 Immich 썸네일 그리드
6. 썸네일 클릭 → Immich 원본 뷰어로 이동 (`{IMMICH_URL}/photos/{assetId}`)

**레이아웃:**
- 상단 툴바: 퀵 색상 팔레트 + 방문 지역 카운터
- 중앙: SVG 지도 (흰 바탕, 검은 경계선)
- 우측 패널: 클릭한 지역 사진 그리드 (2열, 스크롤)

---

## 파일 구조

```
korea_travel_map/
├── Dockerfile
├── requirements.txt
├── main.py              # FastAPI 앱 (API + 정적 파일 서빙)
├── db.py                # SQLite 연결·쿼리
├── immich.py            # Immich API 클라이언트
├── geojson/
│   └── korea_sigun.geojson  # 전처리된 시/군 병합 GeoJSON
└── static/
    ├── index.html
    ├── map.js           # D3 SVG 렌더링 + 인터랙션
    └── style.css
```

---

## Docker 설정

```yaml
korea-travel-map:
  build: ./korea_travel_map
  container_name: korea-travel-map
  restart: unless-stopped
  ports:
    - "8094:8000"
  volumes:
    - korea_travel_data:/data
  environment:
    - IMMICH_URL=http://host.docker.internal:2283
    - IMMICH_API_KEY=
```

---

## 미결 사항

- GeoJSON 원본 데이터 출처 확정 (GADM v4 사용 예정)
- 바운딩 박스 데이터는 GeoJSON에서 자동 계산
