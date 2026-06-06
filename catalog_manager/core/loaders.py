"""
core/loaders.py — Excel 파일 로더

schema.py의 detect()를 통해 컬럼 위치가 변경돼도 유연하게 대처합니다.
"""
import os

import pandas as pd

from core import schema
from config import PLANNING_COLUMNS, CATALOG_COLUMNS, LANDING_COLUMNS


def load_planning(path: str) -> tuple[pd.DataFrame, list[str]]:
    """
    기획자료 Excel 로드.

    Returns:
        (DataFrame, warnings) — 내부키 컬럼명으로 정제된 DataFrame과 경고 목록
    """
    df_raw = pd.read_excel(path, header=None)
    s = schema.detect(df_raw, PLANNING_COLUMNS)
    df = schema.apply(df_raw, s)

    df["_row"] = range(len(df))
    df = df[df["course_name"].notna() & (df["course_name"].astype(str).str.strip() != "")].copy()
    return df, s.warnings


def load_catalog(path: str) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """
    카탈로그 Excel 로드 (다중 시트).

    Returns:
        ({시트명: DataFrame}, warnings)
    """
    xl = pd.ExcelFile(path)
    sheets: dict[str, pd.DataFrame] = {}
    all_warnings: list[str] = []

    for sheet_name in xl.sheet_names:
        df_raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
        if df_raw.shape[0] < 2:
            continue

        s = schema.detect(df_raw, CATALOG_COLUMNS)
        all_warnings.extend([f"[{sheet_name}] {w}" for w in s.warnings])

        df = schema.apply(df_raw, s)

        # _excel_row: 실제 openpyxl 행 번호 (1-based)
        df["_excel_row"] = range(s.header_row + 2, s.header_row + 2 + len(df))
        df["_sheet"] = sheet_name

        df = df[df["course_name"].notna() & (df["course_name"].astype(str).str.strip() != "")].copy()
        df["_excel_row"] = list(range(s.header_row + 2, s.header_row + 2 + len(df)))

        sheets[sheet_name] = df

    return sheets, all_warnings


def load_landing(path: str) -> tuple[pd.DataFrame, list[str]]:
    """
    랜딩주소 Excel 로드.
    .xls 파일은 xlrd 또는 LibreOffice를 통해 처리합니다.

    Returns:
        (DataFrame, warnings)
    """
    actual = _ensure_xlsx(path)
    df_raw = pd.read_excel(actual, header=None)
    s = schema.detect(df_raw, LANDING_COLUMNS)
    df = schema.apply(df_raw, s)

    df = df[df["lect_code"].notna()].copy()
    return df, s.warnings


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────

def _ensure_xlsx(path: str) -> str:
    """
    .xls 파일을 xlsx로 변환 후 경로 반환.
    변환 실패 시 원본 경로 반환 (xlrd가 있으면 직접 처리 가능).
    """
    if not path.lower().endswith(".xls"):
        return path

    base = os.path.splitext(os.path.basename(path))[0]
    converted = os.path.join("/tmp", f"{base}_conv.xlsx")

    if not os.path.exists(converted):
        ret = os.system(
            f'libreoffice --headless --convert-to xlsx "{path}" --outdir /tmp/ 2>/dev/null'
        )
        tmp = os.path.join("/tmp", f"{base}.xlsx")
        if os.path.exists(tmp):
            os.rename(tmp, converted)

    if os.path.exists(converted):
        return converted

    # fallback: xlrd로 직접 시도
    try:
        import xlrd  # noqa
        return path
    except ImportError:
        pass

    return path
