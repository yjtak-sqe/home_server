"""
gui/panels/fuzzy.py — 유사강좌명 수동 확인 패널
"""
import tkinter as tk
from gui.theme import C, FONT_HEAD, FONT_SMALL
from gui.widgets import StatCard, DarkTreeview


class FuzzyPanel(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=C["surface"], **kw)
        self._results: list[dict] = []
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=C["surface"])
        hdr.pack(fill="x", padx=24, pady=(22, 10))
        tk.Label(hdr, text="유사 강좌명 수동 확인",
                 font=FONT_HEAD, bg=C["surface"], fg=C["text"]).pack(side="left")
        tk.Label(hdr,
                 text="강좌명이 정확히 일치하지 않으나 다른 정보로 매칭된 항목입니다. 직접 눈으로 확인하세요.",
                 font=FONT_SMALL, bg=C["surface"], fg=C["warning"]).pack(side="left", padx=16)

        card_row = tk.Frame(self, bg=C["surface"])
        card_row.pack(fill="x", padx=24, pady=(0, 12))
        self._cnt_card = StatCard(card_row, "유사매칭 건수", color=C["warning"])
        self._cnt_card.pack(side="left")

        cols = ("시트", "카탈로그 강좌명", "기획자료 강좌명", "유사도", "요일", "시간", "강사", "기타불일치")
        widths = {
            "시트": 140, "카탈로그 강좌명": 200, "기획자료 강좌명": 200,
            "유사도": 70, "요일": 55, "시간": 55, "강사": 55, "기타불일치": 160,
        }
        self._tv = DarkTreeview(self, cols, col_widths=widths)
        self._tv.pack(fill="both", expand=True, padx=24, pady=(0, 24))

    def set_results(self, results: list[dict]):
        self._results = [r for r in results if r["match_type"] == "fuzzy"]
        self._cnt_card.set(str(len(self._results)))
        self._tv.clear()
        for res in self._results:
            plan = res["plan_row"]
            mm   = res["mismatches"]
            chk  = lambda f: "✓" if not any(m[0] == f for m in mm) else "✗"  # noqa
            self._tv.insert((
                res["sheet"][:22],
                str(res["cat_row"].get("course_name", "")).replace("\n", " ")[:55],
                str(plan["course_name"]).replace("\n", " ")[:55] if plan else "-",
                f"{res['fuzzy_score']:.0%}",
                chk("요일"), chk("강좌시간"), chk("강사명"),
                ", ".join(m[0] for m in mm if m[0] not in ("요일", "강좌시간", "강사명")),
            ), tag="fz")
