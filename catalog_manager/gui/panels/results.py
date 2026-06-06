"""
gui/panels/results.py — 기획자료 ↔ 카탈로그 비교결과 패널
"""
import csv
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

from gui.theme import C, FONT_HEAD, FONT_BODY, FONT_SMALL
from gui.widgets import FlatButton, StatCard, DarkTreeview


class ResultsPanel(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=C["surface"], **kw)
        self._results: list[dict] = []
        self._filter_var = tk.StringVar(value="전체")
        self._build()

    # ── 레이아웃 ─────────────────────────────────────────────────────────

    def _build(self):
        # 상단 헤더
        hdr = tk.Frame(self, bg=C["surface"])
        hdr.pack(fill="x", padx=24, pady=(22, 10))

        tk.Label(hdr, text="기획자료 ↔ 카탈로그 비교결과",
                 font=FONT_HEAD, bg=C["surface"], fg=C["text"]).pack(side="left")
        FlatButton(hdr, "  CSV 내보내기  ", command=self._export_csv,
                   bg=C["card2"], hover_bg=C["border"],
                   font=FONT_SMALL, padx=10, pady=5).pack(side="right")

        # 통계 카드
        card_row = tk.Frame(self, bg=C["surface"])
        card_row.pack(fill="x", padx=24, pady=(0, 16))

        self._cards = {}
        for key, label, color in [
            ("total",    "전체 강좌",     C["text2"]),
            ("mismatch", "불일치",        C["error"]),
            ("fuzzy",    "유사매칭",      C["warning"]),
            ("no_match", "매칭없음",      C["text3"]),
            ("ok",       "정상",          C["success"]),
        ]:
            card = StatCard(card_row, label=label, color=color)
            card.pack(side="left", padx=(0, 8), pady=4, ipadx=4)
            self._cards[key] = card

        # 필터 바
        fbar = tk.Frame(self, bg=C["card"])
        fbar.pack(fill="x", padx=24, pady=(0, 2))
        tk.Label(fbar, text="필터", font=FONT_SMALL,
                 bg=C["card"], fg=C["text3"], padx=10).pack(side="left")

        for opt, color in [
            ("전체",     C["text"]),
            ("불일치만",  C["error"]),
            ("유사매칭",  C["warning"]),
            ("매칭없음",  C["text3"]),
        ]:
            tk.Radiobutton(
                fbar, text=opt, variable=self._filter_var, value=opt,
                command=self._refresh, font=FONT_SMALL,
                bg=C["card"], fg=color, selectcolor=C["accent"],
                activebackground=C["card"], padx=10, pady=6,
            ).pack(side="left")

        # 테이블
        cols = ("시트", "카탈로그 강좌명", "매칭", "불일치 항목", "기획자료 기준값")
        widths = {"시트": 160, "카탈로그 강좌명": 240, "매칭": 90,
                  "불일치 항목": 180, "기획자료 기준값": 240}
        self._tv = DarkTreeview(self, cols, col_widths=widths)
        self._tv.pack(fill="both", expand=True, padx=24, pady=(2, 24))

    # ── 데이터 업데이트 ───────────────────────────────────────────────────

    def set_results(self, results: list[dict]):
        self._results = results
        total   = len(results)
        mm      = sum(1 for r in results if r["mismatches"])
        fz      = sum(1 for r in results if r["match_type"] == "fuzzy")
        nm      = sum(1 for r in results if r["match_type"] == "no_match")
        ok      = total - mm - nm

        self._cards["total"].set(str(total))
        self._cards["mismatch"].set(str(mm))
        self._cards["fuzzy"].set(str(fz))
        self._cards["no_match"].set(str(nm))
        self._cards["ok"].set(str(max(ok, 0)))

        self._refresh()

    def _refresh(self):
        self._tv.clear()
        filt = self._filter_var.get()

        for res in self._results:
            mt   = res["match_type"]
            mm   = res["mismatches"]
            name = str(res["cat_row"].get("course_name", "")).replace("\n", " ")[:60]
            mm_str  = "; ".join(f"{f}" for f, _, _ in mm) if mm else ""
            val_str = "; ".join(f"{f}:{p}" for f, _, p in mm) if mm else ""

            match_label = {"exact": "✓ 정확", "fuzzy": "~ 유사", "no_match": "✗ 없음"}.get(mt, mt)

            if filt == "불일치만" and not mm:
                continue
            if filt == "유사매칭" and mt != "fuzzy":
                continue
            if filt == "매칭없음" and mt != "no_match":
                continue

            tag = "mm" if mm else ("fz" if mt == "fuzzy" else ("nm" if mt == "no_match" else "ok"))
            self._tv.insert(
                (res["sheet"][:22], name, match_label, mm_str[:80], val_str[:80]),
                tag=tag,
            )

    # ── CSV 내보내기 ──────────────────────────────────────────────────────

    def _export_csv(self):
        if not self._results:
            messagebox.showwarning("알림", "먼저 검토를 실행하세요.")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            title="비교결과 CSV 저장",
            defaultextension=".csv",
            initialfile=f"비교결과_{ts}.csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["시트", "카탈로그 강좌명", "매칭유형", "불일치항목", "기획자료 기준값"])
            for res in self._results:
                mm = res["mismatches"]
                writer.writerow([
                    res["sheet"],
                    str(res["cat_row"].get("course_name", "")).replace("\n", " ")[:60],
                    res["match_type"],
                    "; ".join(f for f, _, _ in mm),
                    "; ".join(f"{f}:{p}" for f, _, p in mm),
                ])
        messagebox.showinfo("완료", f"저장 완료:\n{path}")
