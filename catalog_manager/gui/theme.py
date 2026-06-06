"""
gui/theme.py — 다크 테마 정의 및 ttk 스타일 초기화
"""
import tkinter as tk
from tkinter import ttk

# ── 색상 팔레트 ───────────────────────────────────────────────────────────
C = {
    "bg":        "#0E1117",   # 앱 최하단 배경
    "sidebar":   "#13161F",   # 사이드바
    "nav_hover": "#1C2030",   # 사이드바 버튼 호버
    "nav_sel":   "#1E2540",   # 사이드바 선택됨
    "surface":   "#181B28",   # 패널 배경
    "card":      "#1E2235",   # 카드 배경
    "card2":     "#252840",   # 카드 조금 더 밝음
    "border":    "#2A2D45",   # 구분선
    "accent":    "#5C73E7",   # 메인 액센트 (인디고)
    "accent_d":  "#3D52C4",   # 액센트 어둡게
    "accent_l":  "#7B8FF0",   # 액센트 밝게
    "success":   "#3CB371",   # 녹색
    "warning":   "#E8A838",   # 주황
    "error":     "#E05555",   # 빨강
    "info":      "#38B2E8",   # 파랑
    "text":      "#E4E6F0",   # 기본 텍스트
    "text2":     "#9DA5C4",   # 서브 텍스트
    "text3":     "#5C6490",   # 뮤트 텍스트
    "row_odd":   "#1B1E2E",   # 테이블 홀수행
    "row_even":  "#181B28",   # 테이블 짝수행
    "row_sel":   "#2E3A6E",   # 테이블 선택행
    "row_mm":    "#1E2040",   # 불일치행
    "row_fz":    "#1E1E10",   # 유사매칭행
    "mm_text":   "#7B8FF0",   # 불일치 텍스트
    "fz_text":   "#E8A838",   # 유사매칭 텍스트
    "ok_text":   "#3CB371",   # 정상 텍스트
    "er_text":   "#E05555",   # 오류 텍스트
    "input_bg":  "#1A1D2E",   # 입력창 배경
    "input_fg":  "#E4E6F0",   # 입력창 텍스트
}

# ── 폰트 ─────────────────────────────────────────────────────────────────
FONT_TITLE  = ("Malgun Gothic", 13, "bold")
FONT_HEAD   = ("Malgun Gothic", 11, "bold")
FONT_BODY   = ("Malgun Gothic", 10)
FONT_SMALL  = ("Malgun Gothic", 9)
FONT_MONO   = ("Consolas", 9)
FONT_NAV    = ("Malgun Gothic", 10, "bold")

# ── ttk 스타일 적용 ────────────────────────────────────────────────────────

def apply(root: tk.Tk):
    """앱 시작 시 한 번 호출하여 전역 ttk 스타일을 적용합니다."""
    style = ttk.Style(root)
    style.theme_use("clam")

    # ── Notebook (탭) ──
    style.configure("TNotebook",
        background=C["surface"], borderwidth=0, tabmargins=[0, 0, 0, 0])
    style.configure("TNotebook.Tab",
        font=FONT_BODY, padding=(18, 8),
        background=C["card"], foreground=C["text2"], borderwidth=0)
    style.map("TNotebook.Tab",
        background=[("selected", C["accent"]), ("active", C["card2"])],
        foreground=[("selected", "#FFFFFF"), ("active", C["text"])])

    # ── Treeview ──
    style.configure("Dark.Treeview",
        background=C["surface"], fieldbackground=C["surface"],
        foreground=C["text"], rowheight=28, font=FONT_SMALL,
        borderwidth=0, relief="flat")
    style.configure("Dark.Treeview.Heading",
        background=C["card2"], foreground=C["text2"],
        font=("Malgun Gothic", 9, "bold"), borderwidth=0, relief="flat")
    style.map("Dark.Treeview",
        background=[("selected", C["row_sel"])],
        foreground=[("selected", "#FFFFFF")])
    style.map("Dark.Treeview.Heading",
        background=[("active", C["border"])])

    # ── Scrollbar ──
    style.configure("Dark.Vertical.TScrollbar",
        background=C["border"], troughcolor=C["surface"],
        arrowcolor=C["text3"], borderwidth=0, relief="flat")
    style.configure("Dark.Horizontal.TScrollbar",
        background=C["border"], troughcolor=C["surface"],
        arrowcolor=C["text3"], borderwidth=0, relief="flat")

    # ── Separator ──
    style.configure("Dark.TSeparator", background=C["border"])

    # ── Progressbar ──
    style.configure("Accent.Horizontal.TProgressbar",
        background=C["accent"], troughcolor=C["card"],
        borderwidth=0, thickness=4)
