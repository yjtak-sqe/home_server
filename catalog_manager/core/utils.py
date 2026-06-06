"""core/utils.py — 공통 유틸리티 함수."""
import os
import re
import glob
import difflib

import pandas as pd


# ── 문자열 정규화 ─────────────────────────────────────────────────────────

def normalize_name(s: str) -> str:
    """강좌명 앞의 [날짜] 태그를 제거하고 공백 정규화."""
    if not isinstance(s, str):
        return ""
    s = re.sub(r"^\[.*?]", "", s)
    return re.sub(r"\s+", " ", s.replace("\n", " ")).strip()


def normalize_fee(s) -> int | None:
    """수강료 문자열 → 정수. 파싱 실패 시 None."""
    if s is None or (isinstance(s, float) and str(s) == "nan"):
        return None
    try:
        v = int(float(str(s)))
        if v > 100:
            return v
    except (ValueError, TypeError):
        pass
    s2 = str(s)
    m = re.search(r"([\d,]+)\s*원", s2)
    if m:
        return int(m.group(1).replace(",", ""))
    nums_c = re.findall(r"\d{1,3}(?:,\d{3})+", s2)
    if nums_c:
        return int(nums_c[0].replace(",", ""))
    nums = [int(n) for n in re.findall(r"\d+", s2.replace(",", ""))]
    if nums:
        large = [n for n in nums if n >= 1000]
        return max(large) if large else nums[-1]
    return None


def extract_lect_code(url: str) -> str | None:
    """URL에서 lectCode 파라미터 값을 추출."""
    if not isinstance(url, str):
        return None
    m = re.search(r"lectCode=([A-Za-z0-9]+)", url)
    return m.group(1) if m else None


def extract_date_range(name: str) -> str | None:
    """강좌명의 [날짜 범위] 태그를 'M.D - M.D' 형식으로 추출."""
    if not isinstance(name, str):
        return None
    m = re.search(r"\[?(\d+)[/.](\d+)\s*[~-]\s*(\d+)[/.](\d+)]?", name)
    if m:
        return f"{m.group(1)}.{m.group(2)} - {m.group(3)}.{m.group(4)}"
    m2 = re.search(r"\[?(\d+)[/.](\d+)]?", name)
    if m2:
        return f"{m2.group(1)}.{m2.group(2)}"
    return None


def fuzzy_ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def clean_instructor(s: str) -> str:
    """강사명에서 '新', '신' 접두어와 공동 강사 구분자를 정리."""
    if not isinstance(s, str):
        return ""
    return re.sub(r"^[新신]", "", s.replace("\n", " ").split("&")[0]).strip()


# ── 데이터 처리 ───────────────────────────────────────────────────────────

def get_lines(s) -> list[str]:
    """셀 값을 줄바꿈으로 분리해 리스트 반환."""
    if pd.isna(s) or s is None:
        return []
    return [x.strip() for x in str(s).split("\n") if x.strip() and str(x).strip() != "nan"]


def norm_day(d) -> str:
    """요일 문자열에서 한글(요일명)만 추출."""
    return re.sub(r"[^가-힣]", "", str(d))


def norm_time(t) -> str:
    """시간 문자열에서 숫자만 추출."""
    return re.sub(r"\D", "", str(t))


def norm_date(d) -> str:
    """날짜 문자열에서 숫자만 추출 (휴강 정보 제외)."""
    base = str(d).split("*")[0]
    return re.sub(r"\D", "", base)


def dedup(seq: list) -> list:
    """순서를 유지하면서 중복 제거."""
    seen = set()
    return [x for x in seq if not (x in seen or seen.add(x))]


# ── 파일 탐색 ─────────────────────────────────────────────────────────────

def find_file(folder: str, keywords: list[str]) -> str | None:
    """폴더에서 키워드를 포함하는 Excel 파일을 찾아 경로 반환."""
    for kw in keywords:
        for ext in ("*.xlsx", "*.xls"):
            hits = glob.glob(os.path.join(folder, f"*{kw}*{ext[1:]}"))
            if hits:
                return hits[0]
    return None
