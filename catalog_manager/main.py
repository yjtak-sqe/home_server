"""
main.py — 진입점

GUI 모드 (기본):
  python main.py

CLI 모드:
  python main.py --cli run  --folder ./raw_data --year 2026 --smst S2 --out ./output
  python main.py --cli build --folder ./raw_data --year 2026 --smst S2 --out ./output/catalog.xlsx
"""
import sys
import os

# 프로젝트 루트를 sys.path에 추가 (PyInstaller 번들 포함)
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _run_gui():
    from gui.app import App
    app = App()
    app.mainloop()


def _run_cli(argv):
    from cli import main as cli_main
    cli_main(argv)


def main():
    # '--cli' 플래그가 있으면 이후 인자를 cli.py 로 넘김
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        _run_cli(sys.argv[2:])
    else:
        _run_gui()


if __name__ == "__main__":
    main()
