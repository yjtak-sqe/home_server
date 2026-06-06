"""
core/schema.py — 유연한 스키마 감지 엔진

Excel 파일의 헤더 위치와 컬럼 이름이 달라져도
config.py의 별칭 목록을 기반으로 자동으로 매핑합니다.
"""
import re
import difflib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pandas as pd

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import HEADER_SCAN_ROWS, MIN_HEADER_NONBLANK, SCHEMA_MIN_SCORE, SCHEMA_WARN_SCORE


@dataclass
class SchemaResult:
    """스키마 감지 결과."""
    header_row: int                   # 헤더가 있는 행 인덱스 (0-based)
    col_map: Dict[str, str]           # {내부키: 실제 컬럼명}
    confidence: Dict[str, float]      # {내부키: 신뢰도 0~1}
    warnings: List[str] = field(default_factory=list)

    def get(self, key: str) -> Optional[str]:
        return self.col_map.get(key)

    @property
    def unmapped(self) -> List[str]:
        return [k for k in self.confidence if self.confidence[k] == 0.0]

    @property
    def is_healthy(self) -> bool:
        return len(self.unmapped) == 0

    def summary(self) -> str:
        lines = [f"헤더행={self.header_row}, 매핑={len(self.col_map)}개"]
        if self.unmapped:
            lines.append(f"매핑실패: {', '.join(self.unmapped)}")
        lines.extend(self.warnings)
        return " | ".join(lines)


def _normalize(s: str) -> str:
    """비교용 정규화: 공백·개행 제거 후 소문자."""
    return re.sub(r"\s+", "", str(s).replace("\n", "").replace("\r", "")).strip().lower()


def _score_header(header: str, aliases: List[str]) -> Tuple[float, str]:
    """헤더 문자열이 별칭 목록과 얼마나 일치하는지 점수(0~1) 반환."""
    h = _normalize(header)
    if not h:
        return 0.0, ""

    # 1단계: 완전 일치
    for a in aliases:
        if h == _normalize(a):
            return 1.0, a

    # 2단계: 포함 관계
    for a in aliases:
        an = _normalize(a)
        if an and (an in h or h in an):
            return 0.87, a

    # 3단계: 퍼지 유사도
    best_score, best_alias = 0.0, ""
    for a in aliases:
        an = _normalize(a)
        if not an:
            continue
        ratio = difflib.SequenceMatcher(None, h, an).ratio()
        if ratio > best_score:
            best_score, best_alias = ratio, a

    return (best_score, best_alias) if best_score >= SCHEMA_MIN_SCORE else (0.0, "")


def detect(df: pd.DataFrame, aliases: Dict[str, List[str]]) -> SchemaResult:
    """
    DataFrame에서 헤더 행을 찾고, 컬럼을 내부 키로 매핑합니다.

    Args:
        df      : header=None 으로 읽은 원본 DataFrame
        aliases : config.py의 *_COLUMNS 딕셔너리

    Returns:
        SchemaResult
    """
    # 첫 번째 aliases 항목으로 헤더 행 탐색
    anchor_aliases = next(iter(aliases.values()), ["강좌명"])

    header_row = 0
    for i in range(min(HEADER_SCAN_ROWS, len(df))):
        row = df.iloc[i]
        non_null = sum(1 for v in row if pd.notna(v) and str(v).strip())
        if non_null < MIN_HEADER_NONBLANK:
            continue
        for cell in row:
            score, _ = _score_header(str(cell) if pd.notna(cell) else "", anchor_aliases)
            if score >= SCHEMA_WARN_SCORE:
                header_row = i
                break
        else:
            continue
        break

    headers = [str(v) if pd.notna(v) else "" for v in df.iloc[header_row]]

    col_map: Dict[str, str] = {}
    confidence: Dict[str, float] = {}
    warnings: List[str] = []

    for key, alias_list in aliases.items():
        best_score, best_header = 0.0, None
        for h in headers:
            s, _ = _score_header(h, alias_list)
            if s > best_score:
                best_score, best_header = s, h

        confidence[key] = best_score
        if best_score >= SCHEMA_MIN_SCORE and best_header is not None:
            col_map[key] = best_header
            if best_score < SCHEMA_WARN_SCORE:
                warnings.append(
                    f"'{key}' 열을 '{best_header}'로 추정 (신뢰도 {best_score:.0%}) — 확인 권장"
                )
        else:
            confidence[key] = 0.0

    return SchemaResult(
        header_row=header_row,
        col_map=col_map,
        confidence=confidence,
        warnings=warnings,
    )


def apply(df_raw: pd.DataFrame, schema: SchemaResult) -> pd.DataFrame:
    """
    SchemaResult를 바탕으로 DataFrame을 정리된 형태로 변환합니다.
    헤더 행 이후 데이터만 남기고, 컬럼을 내부 키로 리네이밍합니다.
    """
    df = df_raw.copy()
    # 헤더 행의 실제 값을 컬럼명으로 지정
    df.columns = [str(v) if pd.notna(v) else f"_col{i}" for i, v in enumerate(df_raw.iloc[schema.header_row])]
    df = df.iloc[schema.header_row + 1:].reset_index(drop=True)

    # 실제 컬럼명 → 내부 키로 리네이밍
    reverse_map = {v: k for k, v in schema.col_map.items()}
    df = df.rename(columns=reverse_map)

    # 매핑 안 된 내부 키는 None 컬럼으로 추가
    for key in schema.col_map:
        if key not in df.columns:
            df[key] = None

    return df
