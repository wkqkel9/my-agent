from datetime import datetime
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent
FAQ_PATH = ROOT / "data" / "faq.txt"
DB_PATH = ROOT / "data" / "agent.db"
DEFAULT_ANSWER = "아직 준비된 답이 없습니다. 질문의 핵심 낱말을 바꿔서 물어보세요."

def load_faq(path=FAQ_PATH):
    rules = []
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "|" not in line:
            continue
        keywords_text, answer = line.split("|", 1)
        keywords = [word.strip().lower() for word in keywords_text.split(",") if word.strip()]
        if keywords and answer.strip():
            rules.append((keywords, answer.strip()))
    return rules

def find_answer(question, rules):
    normalized = question.lower()
    for keywords, answer in rules:
        if any(keyword in normalized for keyword in keywords):
            return answer
    return DEFAULT_ANSWER

def save_chat(turns, db_path=DB_PATH):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS chat(created_at TEXT, who TEXT, message TEXT)")
        db.executemany("INSERT INTO chat VALUES (?, ?, ?)", turns)

def run_chat():
    rules = load_faq()
    name = input("이름 또는 별명: ").strip() or "사용자"
    memory = []
    print("영작 Agent 이용 방법을 물어보세요. 끝내려면 '그만'을 입력하세요.")
    while True:
        question = input(f"{name}: ").strip()
        if question == "그만":
            print("대화를 마칩니다.")
            break
        if not question:
            continue
        answer = find_answer(question, rules)
        now = datetime.now().isoformat(timespec="seconds")
        turns = [(now, name, question), (now, "typing", answer)]
        memory.extend(turns)
        save_chat(turns)
        print(f"typing: {answer}")
    print(f"이번 실행에서 기억한 대화: {len(memory)}줄")
