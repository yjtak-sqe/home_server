import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
import db

@pytest.fixture(autouse=True)
def tmp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()

def test_empty_returns_empty_dict():
    assert db.get_all_colors() == {}

def test_set_and_get():
    db.set_color("서울특별시", "#ff0000")
    assert db.get_all_colors()["서울특별시"] == "#ff0000"

def test_replace():
    db.set_color("부산광역시", "#ff0000")
    db.set_color("부산광역시", "#0000ff")
    assert db.get_all_colors()["부산광역시"] == "#0000ff"

def test_delete():
    db.set_color("대구광역시", "#ff0000")
    db.delete_color("대구광역시")
    assert "대구광역시" not in db.get_all_colors()

def test_delete_nonexistent_is_noop():
    db.delete_color("없는지역")
