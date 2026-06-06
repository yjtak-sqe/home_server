"""
gui/widgets.py — 재사용 가능한 커스텀 위젯 컴포넌트
"""
import tkinter as tk
from tkinter import ttk
from gui.theme import C, FONT_SMALL, FONT_BODY, FONT_HEAD


# ── 기본 유틸 ─────────────────────────────────────────────────────────────

def _bind_hover(widget, normal: str, hover: str, attr: str = "bg"):
    """마우스 진입/이탈 시 배경색 변경."""
    widget.bind("<Enter>",  lambda e: widget.configure(**{attr: hover}))
    widget.bind("<Leave>",  lambda e: widget.configure(**{attr: normal}))


# ── 커스텀 버튼 ───────────────────────────────────────────────────────────

class FlatButton(tk.Button):
    """Flat 스타일 버튼 (hover 효과 포함)."""

    def __init__(self, parent, text, command=None,
                 bg=None, fg=C["text"], hover_bg=None,
                 font=FONT_BODY, padx=14, pady=7, **kw):
        _bg   = bg       or C["accent"]
        _hbg  = hover_bg or C["accent_l"]
        super().__init__(
            parent, text=text, command=command,
            bg=_bg, fg=fg, activebackground=_hbg, activeforeground=fg,
            font=font, relief="flat", cursor="hand2",
            padx=padx, pady=pady, bd=0, **kw,
        )
        _bind_hover(self, _bg, _hbg)


class GhostButton(tk.Button):
    """윤곽선 없는 텍스트 스타일 버튼."""

    def __init__(self, parent, text, command=None,
                 fg=C["text2"], hover_fg=C["text"],
                 font=FONT_SMALL, **kw):
        super().__init__(
            parent, text=text, command=command,
            bg=C["sidebar"], fg=fg, activebackground=C["sidebar"],
            activeforeground=hover_fg, font=font, relief="flat",
            cursor="hand2", bd=0, **kw,
        )
        self.bind("<Enter>", lambda e: self.configure(fg=hover_fg))
        self.bind("<Leave>", lambda e: self.configure(fg=fg))


# ── 통계 카드 ─────────────────────────────────────────────────────────────

class StatCard(tk.Frame):
    """숫자 + 레이블로 구성된 요약 카드."""

    def __init__(self, parent, label: str, value: str = "—",
                 color: str = C["accent"], **kw):
        super().__init__(parent, bg=C["card"], **kw)
        self.configure(padx=20, pady=14)

        self._val_var = tk.StringVar(value=value)
        tk.Label(self, textvariable=self._val_var,
                 font=("Malgun Gothic", 22, "bold"),
                 bg=C["card"], fg=color).pack(anchor="w")
        tk.Label(self, text=label,
                 font=FONT_SMALL, bg=C["card"], fg=C["text2"]).pack(anchor="w")

    def set(self, value: str):
        self._val_var.set(value)


# ── 섹션 레이블 ───────────────────────────────────────────────────────────

class SectionLabel(tk.Label):
    def __init__(self, parent, text, **kw):
        super().__init__(
            parent, text=text.upper(),
            font=("Malgun Gothic", 8, "bold"),
            bg=kw.pop("bg", C["sidebar"]),
            fg=C["text3"], **kw,
        )


# ── 파일 상태 행 ──────────────────────────────────────────────────────────

class FileStatusRow(tk.Frame):
    """파일 이름 + 상태 표시 한 줄 컴포넌트."""

    def __init__(self, parent, label: str, **kw):
        bg = kw.pop("bg", C["sidebar"])
        super().__init__(parent, bg=bg, **kw)
        tk.Label(self, text=label, font=FONT_SMALL,
                 bg=bg, fg=C["text3"], width=10, anchor="w").pack(side="left")
        self._status = tk.Label(self, text="탐색 중...",
                                font=FONT_SMALL, bg=bg, fg=C["warning"])
        self._status.pack(side="left", fill="x", expand=True)

    def set_ok(self, filename: str):
        self._status.configure(text=filename[:26], fg=C["success"])

    def set_missing(self):
        self._status.configure(text="없음", fg=C["error"])

    def set_pending(self):
        self._status.configure(text="탐색 중...", fg=C["warning"])


# ── 입력 필드 ─────────────────────────────────────────────────────────────

class DarkEntry(tk.Entry):
    def __init__(self, parent, textvariable=None, **kw):
        super().__init__(
            parent, textvariable=textvariable,
            bg=C["input_bg"], fg=C["input_fg"],
            insertbackground=C["accent_l"],
            relief="flat", font=FONT_SMALL,
            highlightthickness=1,
            highlightbackground=C["border"],
            highlightcolor=C["accent"],
            **kw,
        )


# ── 다크 Treeview + 스크롤바 ─────────────────────────────────────────────

class DarkTreeview(tk.Frame):
    """Dark 스타일 Treeview와 스크롤바를 묶은 컴포넌트."""

    def __init__(self, parent, columns: tuple, col_widths: dict | None = None, **kw):
        bg = kw.pop("bg", C["surface"])
        super().__init__(parent, bg=bg, **kw)

        self.tree = ttk.Treeview(
            self, columns=columns, show="headings",
            style="Dark.Treeview", selectmode="browse",
        )
        for col in columns:
            w = (col_widths or {}).get(col, 120)
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=60, anchor="w")

        vsb = ttk.Scrollbar(self, orient="vertical",
                            command=self.tree.yview,
                            style="Dark.Vertical.TScrollbar")
        hsb = ttk.Scrollbar(self, orient="horizontal",
                            command=self.tree.xview,
                            style="Dark.Horizontal.TScrollbar")
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)

        # 행 태그
        self.tree.tag_configure("odd",  background=C["row_odd"])
        self.tree.tag_configure("even", background=C["row_even"])
        self.tree.tag_configure("mm",   background=C["row_mm"],  foreground=C["mm_text"])
        self.tree.tag_configure("fz",   background=C["row_fz"],  foreground=C["fz_text"])
        self.tree.tag_configure("nm",   foreground=C["text3"])
        self.tree.tag_configure("ok",   foreground=C["ok_text"])
        self.tree.tag_configure("er",   foreground=C["er_text"])

    def clear(self):
        self.tree.delete(*self.tree.get_children())

    def insert(self, values: tuple, tag: str = "odd"):
        self.tree.insert("", "end", values=values, tags=(tag,))


# ── 구분선 ────────────────────────────────────────────────────────────────

class Divider(tk.Frame):
    def __init__(self, parent, **kw):
        bg = kw.pop("bg", C["sidebar"])
        super().__init__(parent, bg=C["border"], height=1, **kw)


# ── 로그 영역 ─────────────────────────────────────────────────────────────

class LogBox(tk.Text):
    def __init__(self, parent, **kw):
        super().__init__(
            parent,
            bg=C["surface"], fg=C["text2"],
            font=FONT_MONO, wrap="word",
            relief="flat", state="disabled",
            insertbackground=C["accent_l"],
            selectbackground=C["row_sel"],
            **kw,
        )

    def append(self, msg: str, level: str = "info"):
        color_map = {
            "info":    C["text2"],
            "success": C["success"],
            "warning": C["warning"],
            "error":   C["error"],
        }
        tag = f"lvl_{level}"
        self.configure(state="normal")
        self.tag_configure(tag, foreground=color_map.get(level, C["text2"]))
        self.insert("end", msg + "\n", tag)
        self.see("end")
        self.configure(state="disabled")

    def clear(self):
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")
