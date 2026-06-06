"""
gui/app.py — 메인 애플리케이션 윈도우

구조:
  ├── Sidebar (네비게이션)
  └── MainArea
        ├── TopBar (제목 + 상태)
        ├── ContentStack (패널 전환)
        └── BottomBar (진행상황)
"""
import os
import threading
import traceback
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
from datetime import datetime

import gui.theme as theme
from gui.theme import C, FONT_SMALL, FONT_BODY
from gui.panels.home    import HomePanel
from gui.panels.results import ResultsPanel
from gui.panels.urls    import UrlsPanel
from gui.panels.fuzzy   import FuzzyPanel
from config import APP_NAME, APP_VERSION, FILE_KEYWORDS
from core.utils    import find_file
from core.loaders  import load_planning, load_catalog, load_landing
from core.matcher  import match_catalog_to_planning, check_landing_urls
from core import exporters


# ── 사이드바 아이템 정의 ──────────────────────────────────────────────────

NAV_ITEMS = [
    ("home",    "🏠", "검 토"),
    ("results", "📊", "비교결과"),
    ("urls",    "🔗", "URL 검토"),
    ("fuzzy",   "🔍", "유사강좌명"),
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}  v{APP_VERSION}")
        self.geometry("1300x860")
        self.minsize(1080, 700)
        self.configure(bg=C["bg"])

        theme.apply(self)
        self._active_nav = tk.StringVar(value="home")
        self._status_var = tk.StringVar(value="파일 경로를 선택한 후 검토를 시작하세요.")

        self.comparison_results: list[dict] = []
        self.url_results: list[dict]        = []
        self.catalog_path_found: str = None

        self._build()
        self._panels["home"].detect_files()

    # ── 전체 레이아웃 ─────────────────────────────────────────────────────

    def _build(self):
        sidebar = tk.Frame(self, bg=C["sidebar"], width=178)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        main = tk.Frame(self, bg=C["surface"])
        main.pack(side="left", fill="both", expand=True)

        self._build_sidebar(sidebar)
        self._build_main(main)

    # ── 사이드바 ──────────────────────────────────────────────────────────

    def _build_sidebar(self, sidebar):
        # 로고 영역
        logo = tk.Frame(sidebar, bg=C["sidebar"])
        logo.pack(fill="x", pady=(28, 0))
        tk.Label(logo, text="📋", font=("Segoe UI Emoji", 28),
                 bg=C["sidebar"], fg=C["accent"]).pack()
        tk.Label(logo, text="카탈로그\n교정 시스템",
                 font=("Malgun Gothic", 11, "bold"),
                 bg=C["sidebar"], fg=C["text"],
                 justify="center").pack(pady=(4, 0))
        tk.Label(logo, text=f"v{APP_VERSION}",
                 font=("Malgun Gothic", 8),
                 bg=C["sidebar"], fg=C["text3"]).pack(pady=(2, 20))

        # 구분선
        tk.Frame(sidebar, bg=C["border"], height=1).pack(fill="x", padx=16)

        # 내비게이션 버튼
        self._nav_buttons: dict[str, tk.Frame] = {}
        for key, icon, label in NAV_ITEMS:
            btn = self._make_nav_btn(sidebar, key, icon, label)
            btn.pack(fill="x", pady=1, padx=8)
            self._nav_buttons[key] = btn

        # 하단 내보내기 버튼들
        tk.Frame(sidebar, bg=C["border"], height=1).pack(fill="x", padx=16, pady=(20, 8))
        tk.Label(sidebar, text="내보내기", font=("Malgun Gothic", 8, "bold"),
                 bg=C["sidebar"], fg=C["text3"]).pack(anchor="w", padx=16, pady=(0, 6))

        for text, cmd in [
            ("📥  교정 카탈로그", self._export_corrected),
            ("📑  새 카탈로그",    self._export_new),
        ]:
            btn = tk.Button(sidebar, text=text, command=cmd,
                            bg=C["sidebar"], fg=C["text2"],
                            activebackground=C["nav_hover"],
                            activeforeground=C["text"],
                            font=FONT_SMALL, relief="flat",
                            cursor="hand2", padx=12, pady=7, anchor="w")
            btn.pack(fill="x", padx=8, pady=1)
            btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=C["nav_hover"]))
            btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=C["sidebar"]))

    def _make_nav_btn(self, parent, key: str, icon: str, label: str) -> tk.Frame:
        frame = tk.Frame(parent, bg=C["sidebar"], cursor="hand2")

        def _click():
            self._switch_panel(key)

        inner = tk.Frame(frame, bg=C["sidebar"])
        inner.pack(fill="x", padx=4, pady=4)

        tk.Label(inner, text=icon, font=("Segoe UI Emoji", 13),
                 bg=C["sidebar"], fg=C["text2"]).pack(side="left", padx=(8, 6))
        lbl = tk.Label(inner, text=label, font=FONT_BODY,
                       bg=C["sidebar"], fg=C["text2"])
        lbl.pack(side="left")

        # 클릭 / hover 바인딩
        for w in [frame, inner] + inner.winfo_children():
            w.bind("<Button-1>", lambda e: _click())
            w.bind("<Enter>",    lambda e, f=frame, i=inner, l=lbl: (
                f.configure(bg=C["nav_hover"]),
                i.configure(bg=C["nav_hover"]),
                [c.configure(bg=C["nav_hover"]) for c in i.winfo_children()],
            ))
            w.bind("<Leave>",    lambda e, f=frame, i=inner, l=lbl, k=key: (
                self._update_nav_style(k)
            ))

        return frame

    def _update_nav_style(self, key: str):
        """선택된 버튼은 accent 색, 나머지는 일반 색으로."""
        is_sel = (key == self._active_nav.get())
        bg = C["nav_sel"] if is_sel else C["sidebar"]
        fg = C["accent_l"] if is_sel else C["text2"]
        frame = self._nav_buttons.get(key)
        if not frame:
            return
        for w in frame.winfo_descendants():
            try:
                w.configure(bg=bg)
                if isinstance(w, tk.Label):
                    w.configure(fg=fg)
            except tk.TclError:
                pass
        frame.configure(bg=bg)

    # ── 메인 영역 ─────────────────────────────────────────────────────────

    def _build_main(self, main):
        # TopBar
        top = tk.Frame(main, bg=C["card"], height=48)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text=APP_NAME, font=("Malgun Gothic", 12, "bold"),
                 bg=C["card"], fg=C["text"]).pack(side="left", padx=20)
        tk.Label(top, textvariable=self._status_var,
                 font=FONT_SMALL, bg=C["card"], fg=C["text3"]).pack(side="right", padx=20)

        # 패널 스택
        stack = tk.Frame(main, bg=C["surface"])
        stack.pack(fill="both", expand=True)

        self._panels: dict[str, tk.Frame] = {
            "home":    HomePanel(stack, on_run=self._run, on_build=self._run_build_catalog),
            "results": ResultsPanel(stack),
            "urls":    UrlsPanel(stack),
            "fuzzy":   FuzzyPanel(stack),
        }
        for panel in self._panels.values():
            panel.place(relx=0, rely=0, relwidth=1, relheight=1)

        # ProgressBar (bottom)
        self._progress = ttk.Progressbar(main, style="Accent.Horizontal.TProgressbar",
                                         mode="indeterminate", length=200)
        # pack은 실행 시에만 표시

        self._switch_panel("home")

    def _switch_panel(self, key: str):
        self._active_nav.set(key)
        for k in self._nav_buttons:
            self._update_nav_style(k)
        self._panels[key].lift()

    # ── 검토 실행 ─────────────────────────────────────────────────────────

    def _run(self, folder, year, smst, default_dates):
        threading.Thread(
            target=self._run_bg,
            args=(folder, year, smst, default_dates),
            daemon=True,
        ).start()

    def _run_bg(self, folder, year, smst, default_dates):
        home = self._panels["home"]
        self._set_status("실행 중...")
        self._start_progress()

        try:
            plan_path = find_file(folder, FILE_KEYWORDS["planning"])
            cat_path  = find_file(folder, FILE_KEYWORDS["catalog"])
            land_path = find_file(folder, FILE_KEYWORDS["landing"])

            missing = [n for n, p in [("기획자료", plan_path), ("카탈로그", cat_path), ("랜딩주소", land_path)] if not p]
            if missing:
                self.after(0, messagebox.showerror, "파일 없음", f"찾을 수 없음: {', '.join(missing)}")
                self._set_status("오류 — 파일을 찾을 수 없습니다.")
                return

            self.catalog_path_found = cat_path

            self._set_status("기획자료 로딩...")
            planning_df, pw = load_planning(plan_path)
            self.after(0, home.log_ok,   f"기획자료: {len(planning_df)}개")
            for w in pw:
                self.after(0, home.log_warn, w)

            self._set_status("카탈로그 로딩...")
            catalog_dict, cw = load_catalog(cat_path)
            total = sum(len(v) for v in catalog_dict.values())
            self.after(0, home.log_ok, f"카탈로그: {len(catalog_dict)}시트, {total}개")
            for w in cw:
                self.after(0, home.log_warn, w)

            self._set_status("랜딩주소 로딩...")
            landing_df, lw = load_landing(land_path)
            self.after(0, home.log_ok,  f"랜딩주소: {len(landing_df)}개")
            for w in lw:
                self.after(0, home.log_warn, w)

            self._set_status("비교 중...")
            self.comparison_results = match_catalog_to_planning(planning_df, catalog_dict, default_dates)
            mm = sum(1 for r in self.comparison_results if r["mismatches"])
            fz = sum(1 for r in self.comparison_results if r["match_type"] == "fuzzy")
            nm = sum(1 for r in self.comparison_results if r["match_type"] == "no_match")
            self.after(0, home.log_ok, f"비교 완료 — 불일치 {mm}건 / 유사 {fz}건 / 미매칭 {nm}건")

            self._set_status("URL 검토 중...")
            self.url_results = check_landing_urls(catalog_dict, landing_df, year, smst)
            ue = sum(1 for r in self.url_results if r["status"] != "ok")
            self.after(0, home.log_ok, f"URL 검토 완료 — 오류 {ue}건")

            self.after(0, self._on_run_complete, mm, ue)

        except Exception as e:
            err = traceback.format_exc()
            self.after(0, home.log_error, f"{e}\n{err}")
            self._set_status(f"오류: {e}")
            self.after(0, messagebox.showerror, "오류", str(e))
        finally:
            self._stop_progress()

    def _on_run_complete(self, mm: int, ue: int):
        self._panels["results"].set_results(self.comparison_results)
        self._panels["urls"].set_results(self.url_results)
        self._panels["fuzzy"].set_results(self.comparison_results)
        self._set_status(f"완료  |  불일치 {mm}건  |  URL 오류 {ue}건")
        self._switch_panel("results")

    # ── 새 카탈로그 생성 ──────────────────────────────────────────────────

    def _run_build_catalog(self, folder, year, smst, default_dates):
        tmpl_path = find_file(folder, FILE_KEYWORDS["template"])
        land_path = find_file(folder, FILE_KEYWORDS["landing"])

        if not tmpl_path:
            messagebox.showerror("오류", "카탈로그_공란 파일을 찾을 수 없습니다.")
            return
        if not land_path:
            messagebox.showerror("오류", "랜딩주소 파일을 찾을 수 없습니다.")
            return

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = filedialog.asksaveasfilename(
            title="새 카탈로그 저장",
            defaultextension=".xlsx",
            initialfile=f"카탈로그_완성본_{ts}.xlsx",
            filetypes=[("Excel", "*.xlsx")],
        )
        if not out:
            return

        # 기획자료는 선택 사항 — 있으면 요일·시간 등 추가 필드도 채움
        plan_path = find_file(folder, FILE_KEYWORDS["planning"])

        threading.Thread(
            target=self._build_catalog_bg,
            args=(plan_path, tmpl_path, land_path, year, smst, default_dates, out),
            daemon=True,
        ).start()

    def _build_catalog_bg(self, plan_path, tmpl_path, land_path, year, smst, default_dates, out):
        home = self._panels["home"]
        self._set_status("새 카탈로그 생성 중...")
        self._start_progress()
        try:
            import pandas as pd

            landing_df, lw = load_landing(land_path)
            self.after(0, home.log_ok, f"랜딩주소: {len(landing_df)}개")
            for w in lw:
                self.after(0, home.log_warn, w)

            planning_df = None
            if plan_path:
                planning_df, pw = load_planning(plan_path)
                self.after(0, home.log_ok, f"기획자료: {len(planning_df)}개 (요일·시간 등 추가 채움)")
                for w in pw:
                    self.after(0, home.log_warn, w)
            else:
                self.after(0, home.log_info, "기획자료 없음 — 랜딩주소 기준으로 URL만 채웁니다.")

            exporters.export_catalog_from_scratch(
                landing_df, tmpl_path, year, smst, out, default_dates,
                planning_df=planning_df,
            )
            self.after(0, home.log_ok, f"새 카탈로그 생성 완료: {out}")
            self._set_status("새 카탈로그 생성 완료")
            self.after(0, messagebox.showinfo, "완료", f"저장 완료:\n{out}")
        except Exception as e:
            err = traceback.format_exc()
            self.after(0, home.log_error, f"{e}\n{err}")
            self._set_status(f"오류: {e}")
            self.after(0, messagebox.showerror, "오류", str(e))
        finally:
            self._stop_progress()

    # ── 내보내기 ──────────────────────────────────────────────────────────

    def _export_corrected(self):
        if not self.comparison_results:
            messagebox.showwarning("알림", "먼저 검토를 실행하세요.")
            return
        out_dir = filedialog.askdirectory(title="저장 폴더 선택")
        if not out_dir:
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            path = os.path.join(out_dir, f"카탈로그_교정_{ts}.xlsx")
            exporters.export_corrected_catalog(
                self.catalog_path_found, self.comparison_results, self.url_results, path
            )
            fz_cnt = sum(1 for r in self.comparison_results if r["match_type"] == "fuzzy")
            if fz_cnt:
                fz_path = os.path.join(out_dir, f"유사강좌명_검토_{ts}.xlsx")
                exporters.export_fuzzy_review(self.comparison_results, fz_path)
            ue = [r for r in self.url_results if r["status"] != "ok"]
            if ue:
                url_path = os.path.join(out_dir, f"URL오류목록_{ts}.xlsx")
                exporters.export_url_errors(self.url_results, url_path)
            messagebox.showinfo("완료", f"내보내기 완료:\n{out_dir}")
        except Exception as e:
            messagebox.showerror("오류", str(e))

    def _export_new(self):
        """홈 패널의 현재 설정으로 새 카탈로그 생성 트리거."""
        self._switch_panel("home")
        messagebox.showinfo("알림", "'새 카탈로그 만들기' 버튼을 이용하세요.")

    # ── 진행바 / 상태 ─────────────────────────────────────────────────────

    def _set_status(self, msg: str):
        self.after(0, self._status_var.set, msg)

    def _start_progress(self):
        def _show():
            self._progress.pack(fill="x", side="bottom")
            self._progress.start(10)
        self.after(0, _show)

    def _stop_progress(self):
        def _hide():
            self._progress.stop()
            self._progress.pack_forget()
        self.after(0, _hide)
