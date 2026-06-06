"""
gui/panels/urls.py — 랜딩 URL 검토 패널
"""
import tkinter as tk
from tkinter import messagebox

from gui.theme import C, FONT_HEAD, FONT_SMALL
from gui.widgets import StatCard, DarkTreeview


class UrlsPanel(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=C["surface"], **kw)
        self._results: list[dict] = []
        self._filter_var = tk.StringVar(value="전체")
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=C["surface"])
        hdr.pack(fill="x", padx=24, pady=(22, 10))
        tk.Label(hdr, text="랜딩 URL 검토",
                 font=FONT_HEAD, bg=C["surface"], fg=C["text"]).pack(side="left")

        card_row = tk.Frame(self, bg=C["surface"])
        card_row.pack(fill="x", padx=24, pady=(0, 16))

        self._cards = {}
        for key, label, color in [
            ("total",   "전체 URL",  C["text2"]),
            ("ok",      "정상",      C["success"]),
            ("missing", "URL 없음",  C["warning"]),
            ("error",   "오류",      C["error"]),
        ]:
            card = StatCard(card_row, label=label, color=color)
            card.pack(side="left", padx=(0, 8), pady=4, ipadx=4)
            self._cards[key] = card

        fbar = tk.Frame(self, bg=C["card"])
        fbar.pack(fill="x", padx=24, pady=(0, 2))
        tk.Label(fbar, text="필터", font=FONT_SMALL,
                 bg=C["card"], fg=C["text3"], padx=10).pack(side="left")
        for opt in ["전체", "오류만"]:
            tk.Radiobutton(
                fbar, text=opt, variable=self._filter_var, value=opt,
                command=self._refresh, font=FONT_SMALL,
                bg=C["card"], fg=C["text"], selectcolor=C["accent"],
                activebackground=C["card"], padx=10, pady=6,
            ).pack(side="left")

        cols = ("시트", "강좌명", "lectCode", "상태", "이슈")
        widths = {"시트": 140, "강좌명": 220, "lectCode": 100, "상태": 100, "이슈": 320}
        self._tv = DarkTreeview(self, cols, col_widths=widths)
        self._tv.pack(fill="both", expand=True, padx=24, pady=(2, 24))

    def set_results(self, results: list[dict]):
        self._results = results
        total   = len(results)
        ok      = sum(1 for r in results if r["status"] == "ok")
        missing = sum(1 for r in results if r["status"] == "url_missing")
        error   = total - ok - missing

        self._cards["total"].set(str(total))
        self._cards["ok"].set(str(ok))
        self._cards["missing"].set(str(missing))
        self._cards["error"].set(str(error))
        self._refresh()

    def _refresh(self):
        self._tv.clear()
        filt = self._filter_var.get()
        for r in self._results:
            if filt == "오류만" and r["status"] == "ok":
                continue
            tag = "ok" if r["status"] == "ok" else "er"
            self._tv.insert((
                r["sheet"][:22],
                r["course"][:45],
                r.get("lect_code", "") or "",
                r["status"],
                " | ".join(r["issues"]) if r["issues"] else "—",
            ), tag=tag)
