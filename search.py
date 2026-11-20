from pathlib import Path

from compare import cosine_similarity
from embed import embed

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "grammar_guide.txt"


def load_notes(path=DATA_PATH):
    notes = []
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line:
            notes.append(line)
    return notes


def prepare_index(path=DATA_PATH):
    notes = load_notes(path)
    return [(note, embed(note)) for note in notes]


def search(question, index=None, top_k=3):
    if index is None:
        index = prepare_index()
    q_vec = embed(question)
    scored = [
        (cosine_similarity(q_vec, note_vec), note)
        for note, note_vec in index
    ]
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[:top_k]


def build_rag_prompt(question, results):
    lines = ["아래 자료만 보고 답해 줘. 자료에 없는 내용은 없다고 말해 줘.", "", "[찾은 자료]"]
    for rank, (_, note) in enumerate(results, 1):
        lines.append(f"{rank}. {note}")
    lines.extend(["", f"질문: {question}"])
    return "\n".join(lines)


def run_search():
    print("로컬 임베딩 모델을 불러오는 중입니다...")
    index = prepare_index()
    print("뜻으로 찾기를 시작합니다. 끝내려면 '그만'을 입력하세요.")
    while True:
        question = input("질문: ").strip()
        if question == "그만":
            print("뜻으로 찾기를 마칩니다.")
            break
        if not question:
            continue
        results = search(question, index=index, top_k=3)
        print("\n[가까운 자료 3개]")
        for rank, (score, note) in enumerate(results, 1):
            print(f"{rank}위 ({score:.3f}) · {note}")
        print("\n--- AI에게 보낼 질문 ---")
        print(build_rag_prompt(question, results))
        print("------------------------\n")


if __name__ == "__main__":
    run_search()
