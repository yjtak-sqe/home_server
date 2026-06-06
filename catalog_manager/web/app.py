"""
web/app.py — 카탈로그 교정 시스템 웹 서버 (FastAPI)

기존 데스크톱 GUI(gui/)와 동일한 core 로직을 웹으로 제공합니다.
브라우저에서 Excel 파일을 업로드하면 검토/생성 결과를 화면에 표시하고
교정 파일을 내려받을 수 있습니다.
"""
from __future__ import annotations

import os
import sys
import shutil
import tempfile
import traceback

# 프로젝트 루트(catalog_manager)를 import 경로에 추가 — core/, config 임포트용
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from config import APP_NAME, APP_VERSION
from web import service

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(HERE, "static")
TEMPLATE_DIR = os.path.join(HERE, "templates")

app = FastAPI(title=APP_NAME, version=APP_VERSION)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def _startup():
    os.makedirs(service.JOBS_DIR, exist_ok=True)
    service.cleanup_old_jobs()


# ── 업로드 헬퍼 ───────────────────────────────────────────────────────────

_ALLOWED_EXT = {".xlsx", ".xls"}


def _save_upload(upload: UploadFile | None, dest_dir: str, role: str, required: bool) -> str | None:
    """업로드 파일을 검증 후 저장하고 경로를 반환합니다."""
    if upload is None or not upload.filename:
        if required:
            raise HTTPException(400, f"'{role}' 파일을 업로드해 주세요.")
        return None

    ext = os.path.splitext(upload.filename)[1].lower()
    if ext not in _ALLOWED_EXT:
        raise HTTPException(400, f"'{role}'은(는) Excel(.xlsx/.xls) 파일만 가능합니다. (받은 파일: {upload.filename})")

    safe_name = f"{role}{ext}"
    path = os.path.join(dest_dir, safe_name)
    with open(path, "wb") as f:
        shutil.copyfileobj(upload.file, f)
    upload.file.close()
    return path


def _require_xlsx(path: str | None, role: str):
    """openpyxl로 열어야 하는 파일(.xls 불가)을 검증합니다."""
    if path and path.lower().endswith(".xls"):
        raise HTTPException(400, f"'{role}'은(는) .xlsx 형식이어야 합니다. (.xls 는 지원하지 않습니다)")


# ── 페이지 ────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(TEMPLATE_DIR, "index.html"), encoding="utf-8") as f:
        html = f.read()
    html = html.replace("{{APP_NAME}}", APP_NAME).replace("{{APP_VERSION}}", APP_VERSION)
    return HTMLResponse(html)


@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


@app.get("/api/meta")
def meta():
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "smst_options": service.smst_options(),
        "default_dates": service.default_dates(),
    }


# ── 검토 ──────────────────────────────────────────────────────────────────

@app.post("/api/review")
async def api_review(
    year: str = Form(...),
    smst: str = Form(...),
    dates: str | None = Form(None),
    planning: UploadFile | None = File(None),
    catalog: UploadFile | None = File(None),
    landing: UploadFile | None = File(None),
):
    if not year.strip():
        raise HTTPException(400, "연도를 입력해 주세요.")
    if not smst.strip():
        raise HTTPException(400, "학기코드를 선택해 주세요.")

    with tempfile.TemporaryDirectory() as tmp:
        plan_path = _save_upload(planning, tmp, "planning", required=True)
        cat_path = _save_upload(catalog, tmp, "catalog", required=True)
        land_path = _save_upload(landing, tmp, "landing", required=True)
        _require_xlsx(cat_path, "카탈로그")

        try:
            result = service.run_review(plan_path, cat_path, land_path, year.strip(), smst.strip(), dates)
        except HTTPException:
            raise
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            raise HTTPException(500, f"검토 처리 중 오류: {e}")

    return JSONResponse(result)


# ── 새 카탈로그 생성 ──────────────────────────────────────────────────────

@app.post("/api/build")
async def api_build(
    year: str = Form(...),
    smst: str = Form(...),
    dates: str | None = Form(None),
    template: UploadFile | None = File(None),
    landing: UploadFile | None = File(None),
    planning: UploadFile | None = File(None),
):
    if not year.strip():
        raise HTTPException(400, "연도를 입력해 주세요.")
    if not smst.strip():
        raise HTTPException(400, "학기코드를 선택해 주세요.")

    with tempfile.TemporaryDirectory() as tmp:
        tmpl_path = _save_upload(template, tmp, "template", required=True)
        land_path = _save_upload(landing, tmp, "landing", required=True)
        plan_path = _save_upload(planning, tmp, "planning", required=False)
        _require_xlsx(tmpl_path, "카탈로그_공란")

        try:
            result = service.run_build(tmpl_path, land_path, year.strip(), smst.strip(), dates, planning_path=plan_path)
        except HTTPException:
            raise
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            raise HTTPException(500, f"카탈로그 생성 중 오류: {e}")

    return JSONResponse(result)


# ── 다운로드 ──────────────────────────────────────────────────────────────

@app.get("/api/download/{job_id}/{filename}")
def download(job_id: str, filename: str):
    safe_name = os.path.basename(filename)
    try:
        out_dir = service.job_out_dir(job_id)
    except ValueError:
        raise HTTPException(400, "잘못된 작업 ID입니다.")
    path = os.path.join(out_dir, safe_name)
    if not os.path.isfile(path):
        raise HTTPException(404, "파일을 찾을 수 없습니다. 결과가 만료되었을 수 있습니다.")
    return FileResponse(path, filename=safe_name)
