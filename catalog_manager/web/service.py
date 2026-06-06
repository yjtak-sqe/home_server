"""
web/service.py — 웹 인터페이스용 서비스 레이어

기존 core/ 모듈(loaders·matcher·exporters)을 그대로 재사용하여
업로드된 파일을 처리하고, UI가 바로 렌더링할 수 있는 구조화된 결과를 돌려줍니다.

GUI(gui/)·CLI(cli.py)와 동일한 로직을 공유하므로 검증 규칙이 분기되지 않습니다.
"""
from __future__ import annotations

import os
import shutil
import uuid
import time
from datetime import datetime

from core.loaders import load_planning, load_catalog, load_landing
from core.matcher import match_catalog_to_planning, check_landing_urls
from core import exporters
from config import DEFAULT_DATES, SMST_OPTIONS

# 작업 산출물 저장 위치 (도커에서는 볼륨으로 마운트)
JOBS_DIR = os.environ.get("CATALOG_DATA_DIR", os.path.join(os.path.dirname(__file__), "_jobs"))
# 이 시간(초)보다 오래된 작업 폴더는 자동 정리
JOB_TTL_SECONDS = int(os.environ.get("CATALOG_JOB_TTL", str(24 * 3600)))

_DAY_ORDER = ["월", "화", "수", "목", "금", "토", "일"]


# ── 작업 폴더 관리 ────────────────────────────────────────────────────────

def _new_job() -> tuple[str, str]:
    """새 작업 ID와 폴더(in/out 하위 포함)를 생성합니다."""
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]
    base = os.path.join(JOBS_DIR, job_id)
    os.makedirs(os.path.join(base, "in"), exist_ok=True)
    os.makedirs(os.path.join(base, "out"), exist_ok=True)
    return job_id, base


def job_out_dir(job_id: str) -> str:
    return os.path.join(JOBS_DIR, _safe_job_id(job_id), "out")


def _safe_job_id(job_id: str) -> str:
    """경로 조작 방지 — 작업 ID에 허용 문자만 남깁니다."""
    cleaned = os.path.basename(str(job_id))
    if not cleaned or cleaned in (".", ".."):
        raise ValueError("잘못된 작업 ID입니다.")
    return cleaned


def cleanup_old_jobs() -> int:
    """TTL이 지난 작업 폴더를 삭제하고 삭제 개수를 반환합니다."""
    if not os.path.isdir(JOBS_DIR):
        return 0
    now = time.time()
    removed = 0
    for name in os.listdir(JOBS_DIR):
        path = os.path.join(JOBS_DIR, name)
        try:
            if os.path.isdir(path) and now - os.path.getmtime(path) > JOB_TTL_SECONDS:
                shutil.rmtree(path, ignore_errors=True)
                removed += 1
        except OSError:
            continue
    return removed


# ── 입력 파싱 ─────────────────────────────────────────────────────────────

def build_default_dates(dates_text: str | None) -> dict:
    """
    '월,화,...' 7개 콤마 구분 문자열 → 요일별 일자 dict.
    비어 있으면 config.DEFAULT_DATES 사용. 일부만 채워져도 안전하게 처리.
    """
    if not dates_text or not dates_text.strip():
        return dict(DEFAULT_DATES)
    parts = [p.strip() for p in dates_text.split(",")]
    result = dict(DEFAULT_DATES)
    for day, value in zip(_DAY_ORDER, parts):
        if value:
            result[day] = value
    return result


def smst_options() -> dict:
    return dict(SMST_OPTIONS)


def default_dates() -> dict:
    return dict(DEFAULT_DATES)


# ── 검토 (run) ────────────────────────────────────────────────────────────

def run_review(
    planning_path: str,
    catalog_path: str,
    landing_path: str,
    year: str,
    smst: str,
    dates_text: str | None,
) -> dict:
    """
    기획자료 ↔ 카탈로그 비교 + URL 검증을 수행하고,
    결과 파일을 생성한 뒤 UI용 구조화 데이터를 반환합니다.
    """
    job_id, base = _new_job()
    out = os.path.join(base, "out")
    dates = build_default_dates(dates_text)
    logs: list[str] = []

    def log(msg: str, level: str = "INFO"):
        logs.append(f"[{level}] {msg}")

    # ── 로딩 ──
    planning_df, pw = load_planning(planning_path)
    log(f"기획자료 {len(planning_df)}개 로드")
    logs += [f"[WARN] {w}" for w in pw]

    catalog_dict, cw = load_catalog(catalog_path)
    total_cat = sum(len(v) for v in catalog_dict.values())
    log(f"카탈로그 {len(catalog_dict)}시트 / {total_cat}개 로드")
    logs += [f"[WARN] {w}" for w in cw]

    landing_df, lw = load_landing(landing_path)
    log(f"랜딩주소 {len(landing_df)}개 로드")
    logs += [f"[WARN] {w}" for w in lw]

    # ── 비교 / URL 검증 ──
    comparison = match_catalog_to_planning(planning_df, catalog_dict, dates)
    url_results = check_landing_urls(catalog_dict, landing_df, year, smst)

    # ── 결과 파일 생성 ──
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    files: dict[str, str] = {}

    corrected = os.path.join(out, f"카탈로그_교정_{ts}.xlsx")
    exporters.export_corrected_catalog(catalog_path, comparison, url_results, corrected)
    files["corrected"] = os.path.basename(corrected)

    fuzzy_count = sum(1 for r in comparison if r["match_type"] == "fuzzy")
    if fuzzy_count:
        fuzzy_file = os.path.join(out, f"유사강좌명_검토_{ts}.xlsx")
        exporters.export_fuzzy_review(comparison, fuzzy_file)
        files["fuzzy"] = os.path.basename(fuzzy_file)

    url_err_count = sum(1 for r in url_results if r["status"] != "ok")
    if url_err_count:
        url_file = os.path.join(out, f"URL오류목록_{ts}.xlsx")
        exporters.export_url_errors(url_results, url_file)
        files["url_errors"] = os.path.basename(url_file)

    csv_file = os.path.join(out, f"비교결과_{ts}.csv")
    exporters.export_comparison_csv(comparison, csv_file)
    files["csv"] = os.path.basename(csv_file)

    # ── UI용 구조화 ──
    comp_rows = [_comparison_row(r) for r in comparison]
    url_rows = [_url_row(r) for r in url_results]
    fuzzy_rows = [r for r in comp_rows if r["match_type"] == "fuzzy"]

    stats = {
        "total": len(comparison),
        "mismatch": sum(1 for r in comparison if r["mismatches"]),
        "fuzzy": fuzzy_count,
        "no_match": sum(1 for r in comparison if r["match_type"] == "no_match"),
        "ok": sum(
            1 for r in comparison
            if r["match_type"] == "exact" and not r["mismatches"]
        ),
    }
    url_stats = {
        "total": len(url_results),
        "ok": sum(1 for r in url_results if r["status"] == "ok"),
        "missing": sum(1 for r in url_results if r["status"] == "url_missing"),
        "error": sum(1 for r in url_results if r["status"] == "mismatch"),
    }

    return {
        "job_id": job_id,
        "stats": stats,
        "url_stats": url_stats,
        "comparison": comp_rows,
        "urls": url_rows,
        "fuzzy": fuzzy_rows,
        "files": files,
        "logs": logs,
    }


def _comparison_row(res: dict) -> dict:
    cat_name = str(res["cat_row"].get("course_name", "")).replace("\n", " ").strip()
    plan_name = (
        str(res["plan_row"]["course_name"]).replace("\n", " ").strip()
        if res["plan_row"] is not None else ""
    )
    return {
        "sheet": res["sheet"],
        "course": cat_name,
        "plan_name": plan_name,
        "match_type": res["match_type"],
        "fuzzy_score": round(res["fuzzy_score"], 3),
        "mismatches": [
            {"field": f, "catalog": str(c), "planning": str(p)}
            for (f, c, p) in res["mismatches"]
        ],
    }


def _url_row(res: dict) -> dict:
    return {
        "sheet": res["sheet"],
        "course": res["course"],
        "url": res["url"],
        "lect_code": res.get("lect_code") or "",
        "status": res["status"],
        "issues": res["issues"],
    }


# ── 새 카탈로그 생성 (build) ──────────────────────────────────────────────

def run_build(
    template_path: str,
    landing_path: str,
    year: str,
    smst: str,
    dates_text: str | None,
    planning_path: str | None = None,
) -> dict:
    """
    카탈로그_공란 + 랜딩주소로 새 카탈로그를 생성합니다.
    기획자료(planning_path)는 선택 사항입니다.
    """
    job_id, base = _new_job()
    out = os.path.join(base, "out")
    dates = build_default_dates(dates_text)
    logs: list[str] = []

    landing_df, lw = load_landing(landing_path)
    logs.append(f"[INFO] 랜딩주소 {len(landing_df)}개 로드")
    logs += [f"[WARN] {w}" for w in lw]

    planning_df = None
    if planning_path:
        planning_df, pw = load_planning(planning_path)
        logs.append(f"[INFO] 기획자료 {len(planning_df)}개 로드 (요일·시간 등 추가 채움)")
        logs += [f"[WARN] {w}" for w in pw]
    else:
        logs.append("[WARN] 기획자료 없음 — 랜딩주소 기준으로 URL 열만 채웁니다.")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(out, f"카탈로그_완성본_{ts}.xlsx")
    exporters.export_catalog_from_scratch(
        landing_df, template_path, year, smst, output_path, dates,
        planning_df=planning_df,
    )
    logs.append("[OK] 새 카탈로그 생성 완료")

    return {
        "job_id": job_id,
        "files": {"catalog": os.path.basename(output_path)},
        "logs": logs,
        "landing_count": len(landing_df),
        "used_planning": planning_path is not None,
    }
