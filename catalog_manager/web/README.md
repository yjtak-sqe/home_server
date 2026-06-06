# 카탈로그 교정 시스템 — 웹 버전

데스크톱 GUI(`gui/`)와 **동일한 `core/` 로직**을 브라우저에서 사용할 수 있게 한 웹 인터페이스입니다.
파이썬 설치나 .exe 배포 없이, 서버에 띄워두면 어느 기기(노트북·태블릿·폰)에서나 접속해서 사용할 수 있습니다.

## 구조

```
web/
├── app.py              # FastAPI 서버 (라우팅·업로드·다운로드)
├── service.py          # core/ 로직 래핑 → UI용 구조화 데이터 반환
├── templates/
│   └── index.html      # 단일 페이지 UI
└── static/
    ├── style.css       # 다크 테마 (gui/theme.py 팔레트 공유)
    └── app.js          # 업로드·검토·생성·결과 렌더링
```

기존 데스크톱 코드는 **전혀 수정하지 않았습니다.** `web/`는 `core/`와 `config.py`를
그대로 import 해서 재사용하므로, 검증 규칙이 두 곳으로 갈라지지 않습니다.

## 기능

| 모드 | 설명 | 입력 | 출력 |
|------|------|------|------|
| **카탈로그 검토** | 기획자료 ↔ 카탈로그 비교 + URL 검증 | 기획자료·카탈로그·랜딩주소 | 교정 카탈로그·유사강좌명·URL오류·CSV |
| **새 카탈로그 생성** | 공란 템플릿에 자동 채움 | 카탈로그_공란·랜딩주소(+기획자료 선택) | 완성된 카탈로그 |

## 도커로 실행 (권장)

리포지토리 루트의 `docker-compose.yml`에 `catalog-manager` 서비스로 포함되어 있습니다.

```bash
cd ~/home_server
docker compose up -d --build catalog-manager
```

접속: `http://서버IP:8090`

## 단독 실행 (개발용)

```bash
cd catalog_manager
pip install -r requirements.txt
uvicorn web.app:app --host 0.0.0.0 --port 8000
```

## 환경 변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `CATALOG_DATA_DIR` | `web/_jobs` | 결과 파일 저장 위치 (도커는 `/data/jobs` 볼륨) |
| `CATALOG_JOB_TTL` | `86400` | 결과 파일 보관 시간(초). 지나면 자동 삭제 |

## 참고

- **카탈로그·카탈로그_공란**은 `.xlsx`만 가능합니다 (openpyxl로 셀 서식을 직접 편집하기 때문).
- **랜딩주소**는 `.xls`/`.xlsx` 모두 가능합니다.
- 결과 파일은 TTL(기본 24시간) 후 자동 삭제되므로, 받은 파일은 따로 저장하세요.
