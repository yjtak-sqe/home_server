"""
build.py — PyInstaller를 이용한 독립 실행 파일(.exe) 빌드 스크립트

사용법:
  pip install pyinstaller
  python build.py

결과물: dist/카탈로그교정시스템/카탈로그교정시스템.exe  (Windows)
         dist/카탈로그교정시스템/카탈로그교정시스템      (macOS/Linux)
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

ROOT      = Path(__file__).parent
DIST_DIR  = ROOT / "dist"
BUILD_DIR = ROOT / "build"
APP_NAME  = "카탈로그교정시스템"

PYINSTALLER_OPTS = [
    "main.py",
    f"--name={APP_NAME}",
    "--onedir",
    "--windowed",
    "--noconfirm",
    f"--distpath={DIST_DIR}",
    f"--workpath={BUILD_DIR}",
    f"--specpath={BUILD_DIR}",
    "--hidden-import=openpyxl.cell._writer",
    "--hidden-import=openpyxl.styles.stylesheet",
    "--hidden-import=pandas._libs.tslibs.timedeltas",
    "--hidden-import=xlrd",
]


def check_pyinstaller():
    try:
        import PyInstaller  # noqa
        return True
    except ImportError:
        return False


def install_pyinstaller():
    print("PyInstaller 설치 중...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])


def build():
    print("=" * 55)
    print(f"  {APP_NAME}  빌드 시작")
    print("=" * 55)

    if not check_pyinstaller():
        install_pyinstaller()

    target = DIST_DIR / APP_NAME
    if target.exists():
        shutil.rmtree(target)
        print(f"이전 빌드 삭제: {target}")

    cmd = [sys.executable, "-m", "PyInstaller"] + PYINSTALLER_OPTS
    result = subprocess.run(cmd, cwd=ROOT)

    if result.returncode != 0:
        print("\n[ERROR] 빌드 실패.")
        sys.exit(1)

    raw_data_dir = target / "raw_data"
    raw_data_dir.mkdir(exist_ok=True)
    (raw_data_dir / ".gitkeep").touch()

    readme = ROOT / "README.md"
    if readme.exists():
        shutil.copy(readme, target / "README.md")

    print("=" * 55)
    print(f"  빌드 완료: {target}")
    print("=" * 55)
    print(f"""
배포 방법:
  1. dist/{APP_NAME}/ 폴더 전체를 배포 대상 PC 에 복사합니다.
  2. raw_data/ 에 기획자료.xlsx / 카탈로그.xlsx / 랜딩주소.xls 를 넣습니다.
  3. {APP_NAME}.exe 를 실행합니다.
""")


if __name__ == "__main__":
    build()
