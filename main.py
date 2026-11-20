from datetime import datetime
from pathlib import Path
import sqlite3

from bot import run_chat
from search import run_search

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "agent.db"

def check_status():
    print("\n[typing] 영작 Agent")
    print("- 소개·영작·필사: 정적 프론트엔드")
    print("- FAQ 대화: data/faq.txt")
    print("- 문법 뜻으로 찾기: data/grammar_guide.txt · search.py")
    print("- 대화 기록: data/agent.db")

def record_usage(feature):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.execute("CREATE TABLE IF NOT EXISTS usage(created_at TEXT, feature TEXT)")
        db.execute("INSERT INTO usage VALUES (?, ?)", (datetime.now().isoformat(timespec="seconds"), feature))

def main():
    while True:
        print("\n--- typing Agent ---")
        print("1. 프로젝트 소개")
        print("2. FAQ 대화")
        print("3. 뜻으로 찾기")
        print("0. 종료")
        choice = input("선택하세요: ").strip()

        if choice == "1":
            record_usage("소개")
            check_status()
        elif choice == "2":
            record_usage("대화")
            run_chat()
        elif choice == "3":
            record_usage("뜻으로 찾기")
            run_search()
        elif choice == "0":
            print("종료합니다.")
            break
        else:
            print("1, 2, 3, 0 중에서 선택하세요.")

if __name__ == "__main__":
    main()
