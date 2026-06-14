#!/usr/bin/env python3
"""
ZLAGODA AIS - Entry point.
Usage:
    python main.py
    python main.py /path/to/database.accdb
"""
import sys
import os

# allow imports from project root
sys.path.insert(0, os.path.dirname(__file__))

DEFAULT_DB = os.path.join(os.path.dirname(__file__), "zlagoda.accdb")


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB

    if not os.path.exists(db_path):
        print(f"База даних не знайдена: {db_path}")
        print("Використання: python main.py /шлях/до/файлу.accdb")
        sys.exit(1)

    from app import LoginWindow
    win = LoginWindow(db_path)
    win.mainloop()


if __name__ == "__main__":
    main()
