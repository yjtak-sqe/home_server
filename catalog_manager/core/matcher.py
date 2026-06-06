"""
core/matcher.py — 기획자료 ↔ 카탈로그 비교 엔진, URL 검증
"""
import re

import pandas as pd

from core.utils import (
    normalize_name, normalize_fee, extract_date_range, extract_lect_code,
    fuzzy_ratio, clean_instructor,
    get_lines, norm_day, norm_time, norm_date,
)
from config import FUZZY_MATCH_THRESHOLD, BASE_URL, STORE_CODE


# ── 기획자료 ↔ 카탈로그 매칭 ─────────────────────────────────────────────

def match_catalog_to_planning(
    planning_df: pd.DataFrame,
    catalog_dict: dict,
    default_dates: dict,
) -> list[dict]:
    """
    카탈로그의 각 행을 기획자료와 매칭하고 불일치 항목을 반환합니다.

    Returns:
        list of {
            sheet, cat_row, plan_row, match_type,
            mismatches: [(field, cat_val, plan_val)],
            fuzzy_score, cat_name_norm, aggregated_plan
        }
    """
    results = []

    # 기획자료를 정규화된 강좌명으로 인덱싱
    plan_index: dict[str, list] = {}
    for _, row in planning_df.iterrows():
        key = normalize_name(str(row["course_name"]))
        plan_index.setdefault(key, []).append(row)

    for sheet_name, cat_df in catalog_dict.items():
        for _, cat_row in cat_df.iterrows():
            cat_name_norm = normalize_name(
                str(cat_row.get("course_name", "")).replace("\n", " ")
            )

            # ── 1. 정확 매칭 시도 ──
            plan_rows = plan_index.get(cat_name_norm, [])
            matched_plan = None
            match_type = "no_match"
            best_score = 0.0

            if plan_rows:
                matched_plan = plan_rows[0]
                match_type = "exact"
            else:
                # ── 2. 퍼지 매칭 시도 ──
                for norm_key, prows in plan_index.items():
                    score = fuzzy_ratio(cat_name_norm, norm_key)
                    if score > best_score:
                        best_score = score
                        if score >= FUZZY_MATCH_THRESHOLD:
                            matched_plan = prows[0]
                            plan_rows = prows
                            match_type = "fuzzy"

            # ── 3. 불일치 항목 수집 ──
            mismatches = []
            agg = {"days": [], "times": [], "dates": [], "instructors": []}

            if matched_plan is not None:
                mismatches, agg = _compare(cat_row, plan_rows, default_dates)

            results.append({
                "sheet":           sheet_name,
                "cat_row":         cat_row,
                "plan_row":        matched_plan,
                "match_type":      match_type,
                "mismatches":      mismatches,
                "fuzzy_score":     best_score,
                "cat_name_norm":   cat_name_norm,
                "aggregated_plan": agg,
            })

    return results


def _compare(cat_row, plan_rows: list, default_dates: dict) -> tuple[list, dict]:
    """단일 카탈로그 행과 기획자료 행들을 비교해 불일치 목록을 반환."""
    mismatches = []

    cat_days   = get_lines(cat_row.get("day"))
    cat_times  = get_lines(cat_row.get("time"))
    cat_dates  = get_lines(cat_row.get("date"))
    cat_insts  = get_lines(cat_row.get("instructor"))

    plan_days, plan_times, plan_dates, plan_insts = [], [], [], []

    for pr in plan_rows:
        p_days = get_lines(pr.get("day"))
        plan_days.extend(p_days)
        plan_times.extend(get_lines(pr.get("time")))
        plan_insts.extend(get_lines(pr.get("instructor")))

        dr = extract_date_range(str(pr.get("course_name", "")))
        if dr:
            plan_dates.append(dr)
        else:
            first_day = norm_day(p_days[0]) if p_days else ""
            plan_dates.append(default_dates.get(first_day, ""))

    # 갯수 불일치 (요일/시간/일자 개행 수가 다를 때)
    counts = [len(x) for x in [cat_days, cat_times, cat_dates] if x]
    if len(set(counts)) > 1:
        mismatches.append((
            "갯수 불일치",
            f"요({len(cat_days)})/시({len(cat_times)})/일({len(cat_dates)})",
            "각 열의 개행(항목) 갯수 동일 필요",
        ))

    # 휴강 서식 확인
    for c_date in cat_dates:
        if ("휴강" in c_date or "*" in c_date) and not re.search(r"\s\*.+휴강", c_date):
            mismatches.append(("휴강서식 오류", c_date, "한칸 띄우고 *[일자]휴강 형식 필요"))

    # 요일
    c_days_s = {norm_day(x) for x in cat_days if norm_day(x)}
    p_days_s  = {norm_day(x) for x in plan_days if norm_day(x)}
    if c_days_s != p_days_s and p_days_s:
        mismatches.append(("요일", " / ".join(cat_days), " / ".join(plan_days)))

    # 강좌시간
    c_times_s = {norm_time(x) for x in cat_times if norm_time(x)}
    p_times_s  = {norm_time(x) for x in plan_times if norm_time(x)}
    if c_times_s != p_times_s and p_times_s:
        mismatches.append(("강좌시간", " / ".join(cat_times), " / ".join(plan_times)))

    # 강좌일자
    c_dates_s = {norm_date(x) for x in cat_dates if norm_date(x)}
    p_dates_s  = {norm_date(x) for x in plan_dates if norm_date(x)}
    if c_dates_s != p_dates_s and p_dates_s:
        mismatches.append(("강좌일자", " / ".join(cat_dates), " / ".join(plan_dates)))

    # 강좌비
    cf = normalize_fee(str(cat_row.get("fee_raw", "") or ""))
    pf = normalize_fee(plan_rows[0].get("fee")) if plan_rows else None
    if cf is not None and pf is not None and cf != pf:
        mismatches.append(("강좌비", f"{cf:,}", f"{pf:,}"))

    # 재료비
    mat = plan_rows[0].get("material") if plan_rows else None
    if pd.notna(mat) and str(mat).strip() not in ("nan", "", "NaN", "None"):
        mat_s = str(mat).strip()
        fee_raw_s = str(cat_row.get("fee_raw", "") or "")
        mat_words = re.findall(r"[가-힣a-zA-Z]+", mat_s)
        if mat_words and not all(w in fee_raw_s for w in mat_words[:2]):
            mismatches.append(("재료비", fee_raw_s, mat_s))

    # 강사명
    c_inst_s = {clean_instructor(x) for x in cat_insts if x}
    p_inst_s  = {clean_instructor(x) for x in plan_insts if x}
    if c_inst_s and p_inst_s and c_inst_s != p_inst_s:
        if not all(any(ci in pi or pi in ci for pi in p_inst_s) for ci in c_inst_s):
            mismatches.append(("강사명", " / ".join(cat_insts), " / ".join(plan_insts)))

    agg = {
        "days": plan_days,
        "times": plan_times,
        "dates": plan_dates,
        "instructors": plan_insts,
    }
    return mismatches, agg


# ── URL 검증 ─────────────────────────────────────────────────────────────

def check_landing_urls(
    catalog_dict: dict,
    landing_df: pd.DataFrame,
    year: str,
    smst_code: str,
) -> list[dict]:
    """
    카탈로그의 랜딩 URL이 올바른지 검증합니다.

    Returns:
        list of {sheet, course, url, lect_code, status, issues}
    """
    results = []
    lect_codes_set = set(landing_df["lect_code"].astype(str).str.strip().tolist())

    for sheet_name, cat_df in catalog_dict.items():
        for _, cat_row in cat_df.iterrows():
            url_raw = str(cat_row.get("landing_url", "") or "")
            urls = [u.strip() for u in url_raw.split("\n") if u.strip().startswith("http")]
            day_lines = get_lines(cat_row.get("day"))
            course = str(cat_row.get("course_name", "")).replace("\n", " ")[:50]

            if not urls:
                results.append({
                    "sheet": sheet_name, "course": course,
                    "url": "(없음)", "lect_code": None,
                    "status": "url_missing", "issues": ["랜딩 URL 없음"],
                })
                continue

            global_issues = []
            if day_lines and len(urls) != len(day_lines):
                global_issues.append(
                    f"랜딩주소 갯수 불일치(요일 {len(day_lines)}개 vs URL {len(urls)}개)"
                )

            for url in urls:
                lect_code = extract_lect_code(url)
                issues = list(global_issues)

                yr_m = re.search(r"yearCode=(\d+)", url)
                if yr_m and yr_m.group(1) != str(year):
                    issues.append(f"연도불일치(URL:{yr_m.group(1)}≠{year})")

                sm_m = re.search(r"smstCode=([A-Za-z0-9]+)", url)
                if sm_m and sm_m.group(1) != smst_code:
                    issues.append(f"학기코드불일치(URL:{sm_m.group(1)}≠{smst_code})")

                if lect_code:
                    if lect_code not in lect_codes_set:
                        issues.append(f'lectCode "{lect_code}" 랜딩주소 파일에 없음')
                else:
                    issues.append("lectCode 파싱 실패")

                results.append({
                    "sheet": sheet_name, "course": course,
                    "url": url, "lect_code": lect_code,
                    "status": "ok" if not issues else "mismatch",
                    "issues": issues,
                })

    return results
