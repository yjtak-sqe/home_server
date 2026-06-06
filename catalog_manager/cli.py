"""
cli.py — 커맨드라인 인터페이스

사용 예시:
  # 검토 실행 후 결과 파일 저장
  python main.py --cli run --folder ./raw_data --year 2026 --smst S2 --out ./output

  # 새 카탈로그 생성
  python main.py --cli build --folder ./raw_data --year 2026 --smst S2 --out ./output/catalog.xlsx
"""
import argparse
import os
import sys
from datetime import datetime

from core.utils    import find_file
from core.loaders  import load_planning, load_catalog, load_landing
from core.matcher  import match_catalog_to_planning, check_landing_urls
from core          import exporters
from config        import FILE_KEYWORDS, DEFAULT_DATES, APP_VERSION


def _log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level:^7}] {msg}")


def cmd_run(args):
    """기획자료 ↔ 카탈로그 비교 검토를 실행하고 결과 파일을 저장합니다."""
    folder = args.folder
    year   = args.year
    smst   = args.smst
    out    = args.out or folder

    default_dates = dict(zip(
        ["월", "화", "수", "목", "금", "토", "일"],
        args.dates.split(",") if args.dates else list(DEFAULT_DATES.values()),
    ))

    # 파일 탐색
    plan_path = find_file(folder, FILE_KEYWORDS["planning"])
    cat_path  = find_file(folder, FILE_KEYWORDS["catalog"])
    land_path = find_file(folder, FILE_KEYWORDS["landing"])

    for name, path in [("기획자료", plan_path), ("카탈로그", cat_path), ("랜딩주소", land_path)]:
        if not path:
            _log(f"'{name}' 파일을 찾을 수 없습니다. 폴더를 확인하세요: {folder}", "ERROR")
            sys.exit(1)
        _log(f"{name}: {os.path.basename(path)}")

    # 로딩
    _log("기획자료 로딩...")
    planning_df, pw = load_planning(plan_path)
    _log(f"기획자료: {len(planning_df)}개")
    for w in pw: _log(w, "WARN")

    _log("카탈로그 로딩...")
    catalog_dict, cw = load_catalog(cat_path)
    total = sum(len(v) for v in catalog_dict.values())
    _log(f"카탈로그: {len(catalog_dict)}시트, {total}개")
    for w in cw: _log(w, "WARN")

    _log("랜딩주소 로딩...")
    landing_df, lw = load_landing(land_path)
    _log(f"랜딩주소: {len(landing_df)}개")
    for w in lw: _log(w, "WARN")

    # 비교
    _log("비교 중...")
    comparison = match_catalog_to_planning(planning_df, catalog_dict, default_dates)
    mm = sum(1 for r in comparison if r["mismatches"])
    fz = sum(1 for r in comparison if r["match_type"] == "fuzzy")
    nm = sum(1 for r in comparison if r["match_type"] == "no_match")
    _log(f"비교 완료 — 불일치 {mm} / 유사매칭 {fz} / 미매칭 {nm}")

    _log("URL 검토 중...")
    url_results = check_landing_urls(catalog_dict, landing_df, year, smst)
    ue = sum(1 for r in url_results if r["status"] != "ok")
    _log(f"URL 검토 완료 — 오류 {ue}건")

    # 저장
    os.makedirs(out, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    cat_out = os.path.join(out, f"카탈로그_교정_{ts}.xlsx")
    exporters.export_corrected_catalog(cat_path, comparison, url_results, cat_out)
    _log(f"교정 카탈로그 저장: {cat_out}", "OK")

    if fz:
        fz_out = os.path.join(out, f"유사강좌명_검토_{ts}.xlsx")
        exporters.export_fuzzy_review(comparison, fz_out)
        _log(f"유사강좌명 저장: {fz_out}", "OK")

    if ue:
        url_out = os.path.join(out, f"URL오류목록_{ts}.xlsx")
        exporters.export_url_errors(url_results, url_out)
        _log(f"URL오류목록 저장: {url_out}", "OK")

    csv_out = os.path.join(out, f"비교결과_{ts}.csv")
    exporters.export_comparison_csv(comparison, csv_out)
    _log(f"비교결과 CSV 저장: {csv_out}", "OK")

    _log(f"모든 결과가 '{out}'에 저장되었습니다.")


def cmd_build(args):
    """
    카탈로그_공란 + 랜딩주소를 기반으로 새 카탈로그를 생성합니다.
    기획자료(--planning)는 선택 사항입니다.
      - 제공되면: 요일·시간·강사명·강좌비도 함께 채웁니다.
      - 없으면  : 랜딩주소 파일 기준으로 URL 열만 채웁니다.
    """
    folder = args.folder
    year   = args.year
    smst   = args.smst
    ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
    out    = args.out or os.path.join(folder, f"카탈로그_완성본_{ts}.xlsx")

    default_dates = dict(zip(
        ["월", "화", "수", "목", "금", "토", "일"],
        args.dates.split(",") if args.dates else list(DEFAULT_DATES.values()),
    ))

    tmpl_path = find_file(folder, FILE_KEYWORDS["template"])
    land_path = find_file(folder, FILE_KEYWORDS["landing"])

    if not tmpl_path:
        _log("카탈로그_공란 파일을 찾을 수 없습니다.", "ERROR"); sys.exit(1)
    if not land_path:
        _log("랜딩주소 파일을 찾을 수 없습니다.", "ERROR"); sys.exit(1)

    _log("랜딩주소 로딩...")
    landing_df, lw = load_landing(land_path)
    _log(f"랜딩주소: {len(landing_df)}개")
    for w in lw: _log(w, "WARN")

    # 기획자료 — 선택 사항
    plan_path  = getattr(args, "planning", None) or find_file(folder, FILE_KEYWORDS["planning"])
    planning_df = None
    if plan_path:
        _log("기획자료 로딩...")
        planning_df, pw = load_planning(plan_path)
        _log(f"기획자료: {len(planning_df)}개 (요일·시간 등 추가 채움)")
        for w in pw: _log(w, "WARN")
    else:
        _log("기획자료 없음 — 랜딩주소 기준으로 URL만 채웁니다.", "WARN")

    _log("새 카탈로그 생성 중...")
    exporters.export_catalog_from_scratch(
        landing_df, tmpl_path, year, smst, out, default_dates,
        planning_df=planning_df,
    )
    _log(f"완료: {out}", "OK")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="catalog-checker",
        description=f"카탈로그 교정 시스템 v{APP_VERSION}",
    )
    parser.add_argument("--version", action="version", version=APP_VERSION)

    sub = parser.add_subparsers(dest="command")

    # run
    run_p = sub.add_parser("run", help="기획자료 ↔ 카탈로그 비교 검토")
    run_p.add_argument("--folder", required=True, help="raw_data 폴더 경로")
    run_p.add_argument("--year",   required=True, help="연도 (예: 2026)")
    run_p.add_argument("--smst",   required=True, help="학기코드 (S1/S2/W1/W2)")
    run_p.add_argument("--out",    help="결과 저장 폴더 (기본: --folder)")
    run_p.add_argument("--dates",  help="요일별 기본일자 (월,화,... 콤마 구분 7개)")

    # build
    bld_p = sub.add_parser("build", help="새 카탈로그 생성 (카탈로그_공란 + 랜딩주소)")
    bld_p.add_argument("--folder",   required=True, help="raw_data 폴더 경로")
    bld_p.add_argument("--year",     required=True, help="연도 (예: 2026)")
    bld_p.add_argument("--smst",     required=True, help="학기코드 (S1/S2/W1/W2)")
    bld_p.add_argument("--out",      help="저장 파일 경로 (.xlsx)")
    bld_p.add_argument("--dates",    help="요일별 기본일자 (콤마 구분 7개)")
    bld_p.add_argument("--planning", help="기획자료 파일 경로 (선택 — 제공 시 요일·시간 등도 채움)")

    return parser


def main(argv=None):
    parser = build_parser()
    args   = parser.parse_args(argv)

    if args.command == "run":
        cmd_run(args)
    elif args.command == "build":
        cmd_build(args)
    else:
        parser.print_help()
