import sqlite3
from pathlib import Path

DB_PATH = Path("/data/travel.db")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS region_colors (
                region_id  TEXT PRIMARY KEY,
                color      TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)


def get_all_colors() -> dict[str, str]:
    with get_conn() as conn:
        rows = conn.execute("SELECT region_id, color FROM region_colors").fetchall()
    return {row["region_id"]: row["color"] for row in rows}


def set_color(region_id: str, color: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO region_colors (region_id, color) VALUES (?, ?)",
            (region_id, color),
        )


def delete_color(region_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM region_colors WHERE region_id = ?", (region_id,))
