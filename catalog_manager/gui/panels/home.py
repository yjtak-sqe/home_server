"""
gui/panels/home.py — 파일 선택 · 설정 · 실행 패널
"""
import os
import tkinter as tk
from tkinter import filedialog
from datetime import datetime

from gui.theme import C, FONT_HEAD, FONT_BODY, FONT_SMALL
from gui.widgets import (
    FlatButton, DarkEntry, FileStatusRow, StatCard,
    SectionLabel, Divider, LogBox,
)
from config import SMST_OPTIONS, DEFAULT_DATES, FILE_KEYWORDS
from core.utils import find_file


class HomePanel(tk.Frame):
    """
    좌측: 파일 감지·설정 / 우측: 로그 출력
    """

    def __init__(self, parent, on_run, on_build, **kw):
        super().__init__(parent, bg=C["surface"], **kw)
        self._on_run   = on_run
        self._on_build = on_build

        self._folder_var = tk.StringVar(
            value=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "raw_data")
        )
        self._year_var = tk.StringVar(value=str(datetime.now().year))
        self._smst_var = tk.StringVar(value="S1")
        self.default_dates: dict[str, tk.StringVar] = {}

        self._file_rows: dict[str, FileStatusRow] = {}

        self._build()

    # ── 레이아웃 구성 ─────────────────────────────────────────────────────

    def _build(self):
        # 좌/우 분할
        left = tk.Frame(self, bg=C["surface"])
        left.pack(side="left", fill="y", padx=(28, 16), pady=28)

        right = tk.Frame(self, bg=C["surface"])
        right.pack(side="left", fill="both", expand=True, padx=(0, 28), pady=28)

        self._build_left(left)
        self._build_right(right)

    def _build_left(self, p):
        # ── 폴더 선택 ──
        tk.Label(p, text="데이터 폴더", font=FONT_HEAD,
                 bg=C["surface"], fg=C["text"]).pack(anchor="w")
        tk.Label(p, text="기획자료 / 카탈로그 / 랜딩주소 파일이 있는 폴더를 선택하세요.",
                 font=FONT_SMALL, bg=C["surface"], fg=C["text2"]).pack(anchor="w", pady=(2, 10))

        folder_row = tk.Frame(p, bg=C["surface"])
        folder_row.pack(fill="x", pady=(0, 6))
        DarkEntry(folder_row, textvariable=self._folder_var, width=36).pack(side="left", fill="x", expand=True)
        FlatButton(folder_row, "  폴더 선택  ", command=self._browse,
                   bg=C["card2"], hover_bg=C["border"], font=FONT_SMALL, padx=10, pady=5
                   ).pack(side="left", padx=(6, 0))

        self._folder_var.trace_add("write", lambda *_: self._detect_files())

        # ── 감지된 파일 ──
        Divider(p).pack(fill="x", pady=(10, 8))
        SectionLabel(p, "감지된 파일", bg=C["surface"]).pack(anchor="w", pady=(0, 6))

        for key, label in [("planning", "기획자료"), ("catalog", "카탈로그"),
                            ("landing", "랜딩주소"), ("template", "카탈로그_공란")]:
            row = FileStatusRow(p, label, bg=C["surface"])
            row.pack(fill="x", pady=2)
            self._file_rows[key] = row

        # ── 검토 설정 ──
        Divider(p).pack(fill="x", pady=(14, 8))
        SectionLabel(p, "검토 설정", bg=C["surface"]).pack(anchor="w", pady=(0, 8))

        row_year = tk.Frame(p, bg=C["surface"])
        row_year.pack(fill="x", pady=3)
        tk.Label(row_year, text="연도 (yearCode)", font=FONT_SMALL,
                 bg=C["surface"], fg=C["text2"], width=16, anchor="w").pack(side="left")
        DarkEntry(row_year, textvariable=self._year_var, width=8).pack(side="left")

        row_smst = tk.Frame(p, bg=C["surface"])
        row_smst.pack(fill="x", pady=3)
        tk.Label(row_smst, text="학기 (smstCode)", font=FONT_SMALL,
                 bg=C["surface"], fg=C["text2"], width=16, anchor="w").pack(side="left")

        for code, name in SMST_OPTIONS.items():
            tk.Radiobutton(
                row_smst, text=f"{code}", variable=self._smst_var, value=code,
                bg=C["surface"], fg=C["text2"], selectcolor=C["accent"],
                activebackground=C["surface"], font=FONT_SMALL,
            ).pack(side="left", padx=4)

        # ── 기본 요일별 일자 ──
        Divider(p).pack(fill="x", pady=(14, 8))
        SectionLabel(p, "학기 요일별 기본 일자", bg=C["surface"]).pack(anchor="w", pady=(0, 8))

        grid = tk.Frame(p, bg=C["surface"])
        grid.pack(fill="x")
        days = list(DEFAULT_DATES.keys())
        for i, day in enumerate(days):
            col = (i % 2) * 3
            row = i // 2
            tk.Label(grid, text=f"[{day}]", font=FONT_SMALL,
                     bg=C["surface"], fg=C["text3"], anchor="w", width=4
                     ).grid(row=row, column=col, sticky="w", pady=2)
            var = tk.StringVar(value=DEFAULT_DATES[day])
            self.default_dates[day] = var
            DarkEntry(grid, textvariable=var, width=13
                      ).grid(row=row, column=col + 1, sticky="w", padx=(2, 12), pady=2)

        # ── 실행 버튼 ──
        Divider(p).pack(fill="x", pady=(14, 10))

        FlatButton(p, "▶   검토 시작", command=self._run,
                   bg=C["success"], hover_bg="#4ACD7A", fg="#FFFFFF",
                   font=("Malgun Gothic", 11, "bold"), padx=16, pady=10,
                   ).pack(fill="x", pady=(0, 6))

        FlatButton(p, "📋  새 카탈로그 만들기", command=self._build,
                   bg=C["accent"], hover_bg=C["accent_l"],
                   font=FONT_BODY, padx=14, pady=8,
                   ).pack(fill="x")

    def _build_right(self, p):
        tk.Label(p, text="실행 로그", font=FONT_HEAD,
                 bg=C["surface"], fg=C["text"]).pack(anchor="w")
        tk.Label(p, text="검토 진행 상황과 경고가 표시됩니다.",
                 font=FONT_SMALL, bg=C["surface"], fg=C["text2"]).pack(anchor="w", pady=(2, 10))

        self.log = LogBox(p)
        self.log.pack(fill="both", expand=True)

    # ── 액션 ─────────────────────────────────────────────────────────────

    def _browse(self):
        folder = filedialog.askdirectory(title="데이터 폴더 선택")
        if folder:
            self._folder_var.set(folder)

    def _detect_files(self):
        folder = self._folder_var.get()
        for key, row in self._file_rows.items():
            path = find_file(folder, FILE_KEYWORDS[key])
            if path:
                row.set_ok(os.path.basename(path))
            else:
                row.set_missing()

    def _run(self):
        self._on_run(
            folder=self._folder_var.get(),
            year=self._year_var.get().strip(),
            smst=self._smst_var.get().strip(),
            default_dates={d: v.get().strip() for d, v in self.default_dates.items()},
        )

    def _build(self):
        self._on_build(
            folder=self._folder_var.get(),
            year=self._year_var.get().strip(),
            smst=self._smst_var.get().strip(),
            default_dates={d: v.get().strip() for d, v in self.default_dates.items()},
        )

    # ── 외부 인터페이스 ───────────────────────────────────────────────────

    def log_info(self, msg: str):    self.log.append(f"[INFO]  {msg}", "info")
    def log_ok(self, msg: str):      self.log.append(f"[OK]    {msg}", "success")
    def log_warn(self, msg: str):    self.log.append(f"[WARN]  {msg}", "warning")
    def log_error(self, msg: str):   self.log.append(f"[ERROR] {msg}", "error")

    def detect_files(self):
        self._detect_files()
