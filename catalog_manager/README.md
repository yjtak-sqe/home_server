# 카탈로그 교정 시스템

**신세계 문화아카데미 카탈로그 교정 · 생성 자동화 도구**

---

## 버전 히스토리

### v2.1.0 (2026-04-13) — 새 카탈로그 생성 로직 개선
- **랜딩 URL 매칭 기준 변경**: 기획자료 강좌명 → 카탈로그_공란(템플릿) 강좌명을 기준으로 랜딩주소 파일과 매칭
- **기획자료 선택 사항으로 변경**: `새 카탈로그 만들기` 기능에서 기획자료 없이도 실행 가능
  - 기획자료 있을 때: 요일·강좌시간·강좌일자·강사명·강좌비까지 자동 채움 (기존 동작 유지)
  - 기획자료 없을 때: 랜딩주소 파일 기준으로 URL 열만 채움
- **CLI `build` 커맨드**: `--planning` 인자 선택 사항으로 변경

### v2.0.0 (2026-04-13) — 전면 리팩토링
- **모듈화**: 단일 파일(`catalog_checker.py`) → 패키지 구조로 분리
  - `config.py` — 중앙 설정 (URL, 컬럼 별칭, 임계값)
  - `core/schema.py` — 유연한 컬럼 자동 감지 엔진
  - `core/loaders.py` — 파일 로더
  - `core/matcher.py` — 비교/매칭 엔진
  - `core/exporters.py` — 내보내기
  - `gui/` — UI 컴포넌트 분리
- **유연한 스키마 감지**: Excel 컬럼 위치·이름이 변경돼도 `config.py`의 별칭 목록만 수정하면 자동 대응
- **UI 전면 재설계**: 다크 테마, 사이드바 네비게이션, 통계 카드
- **CLI 지원**: `python main.py --cli run/build` 서브커맨드
- **빌드 스크립트**: `build.py` — PyInstaller로 Python 없이 실행 가능한 `.exe` 생성
- **URL 수정**: `deptmapp.shinsegae.com` → `www.shinsegae.com`

### v1.21 (이전 버전)
- 교정 표시 색상 빨간색 → 파란색 밑줄로 변경
- 누락 현상(10개만 표시) 수정 — 헤더 동적 스캔
- 결과 파일 생성 오류(행 번호 어긋남) 수정

### v1.0 (초기 버전)
- 기획자료 ↔ 카탈로그 비교 (강좌명·요일·시간·강좌비·재료비·강사명)
- 랜딩 URL 검토 (lectCode·yearCode·smstCode)
- 교정 카탈로그 Excel 출력 (빨간색 밑줄)
- 유사강좌명 검토 파일 생성
- 새 카탈로그 생성 (카탈로그_공란 템플릿 기반)

---

## 폴더 구조

```
catalog_v2/
├── main.py            # 진입점 (GUI / CLI 분기)
├── cli.py             # CLI 인터페이스
├── config.py          # 전역 설정 ← 컬럼 이름 바뀌면 여기만 수정
├── build.py           # PyInstaller 빌드 스크립트
├── README.md
├── core/
│   ├── schema.py      # 유연한 컬럼 자동 감지 엔진
│   ├── loaders.py     # Excel 파일 로더
│   ├── matcher.py     # 비교·매칭 엔진 + URL 검증
│   ├── exporters.py   # 모든 내보내기 함수
│   └── utils.py       # 공통 유틸리티
├── gui/
│   ├── theme.py       # 다크 테마 색상·폰트
│   ├── widgets.py     # 재사용 커스텀 위젯
│   ├── app.py         # 메인 앱 윈도우
│   └── panels/
│       ├── home.py    # 파일 선택·설정·로그
│       ├── results.py # 비교결과 테이블
│       ├── urls.py    # URL 검토 테이블
│       └── fuzzy.py   # 유사강좌명 수동 확인
└── raw_data/          # Excel 파일 저장 위치
    ├── 기획자료.xlsx
    ├── 카탈로그.xlsx
    ├── 랜딩주소.xls
    └── 카탈로그_공란.xlsx
```

---

## 설치 및 실행

### 필수 패키지

```bash
pip install pandas openpyxl xlrd
```

### GUI 실행

```bash
python main.py
```

### CLI 실행

```bash
# 기획자료 ↔ 카탈로그 비교 검토
python main.py --cli run \
  --folder ./raw_data \
  --year 2026 \
  --smst S2 \
  --out ./output

# 새 카탈로그 생성
python main.py --cli build \
  --folder ./raw_data \
  --year 2026 \
  --smst S2 \
  --out ./output/카탈로그_완성본.xlsx
```

### Python 없이 실행 (.exe 빌드)

```bash
pip install pyinstaller
python build.py
# → dist/카탈로그교정시스템/ 폴더에 실행 파일 생성
```

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| **기획자료 ↔ 카탈로그 비교** | 강좌명(정확/유사), 요일, 강좌일자, 강좌시간, 강좌비, 재료비, 강사명 |
| **랜딩 URL 검증** | lectCode 존재 여부, yearCode/smstCode 일치 여부 |
| **교정 카탈로그 출력** | 불일치 셀에 파란색 밑줄 + 코멘트 |
| **유사강좌명 검토** | 퍼지매칭 항목 별도 파일로 저장 |
| **새 카탈로그 생성** | 공란 템플릿에 기획자료+랜딩주소 기반으로 자동 채움 |
| **CSV 내보내기** | 비교결과를 Excel에서 열 수 있는 CSV로 저장 |

---

## 컬럼 이름 변경 대응 방법

Excel 파일의 헤더 이름이 바뀐 경우 `config.py` 의 해당 항목에 새 이름을 추가합니다.

```python
# config.py 예시
CATALOG_COLUMNS = {
    "course_name": ["강좌명", "과목명", "새로운헤더이름"],  # ← 추가
    ...
}
```

코드를 수정할 필요 없이 별칭 목록에 추가하는 것만으로 자동 대응됩니다.

---

## URL 형식

```
https://www.shinsegae.com/culture/academy/lecture.do
  ?yearCode={연도}
  &smstCode={학기코드}
  &storeCode=90
  &lectCode={강좌코드}
```

| smstCode | 학기 |
|----------|------|
| S1 | 봄 학기 |
| S2 | 여름 학기 |
| W1 | 겨울1 학기 |
| W2 | 겨울2 학기 |

---

## 출력 파일 색상 기준

| 색상 | 의미 |
|------|------|
| 파란색 밑줄 + 연청 배경 | 값 불일치 (기획자료와 다름) |
| 주황색 밑줄 + 연황 배경 | 강좌명 유사매칭 (수동 확인 필요) |
