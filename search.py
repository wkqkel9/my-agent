from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "grammar_guide.txt"
TOKEN_RE = re.compile(r"[0-9a-zA-Z가-힣]+")


@dataclass(frozen=True)
class SearchIndex:
    notes: tuple[str, ...]
    term_counts: tuple[Counter, ...]
    document_frequency: Counter
    average_length: float


def load_notes(path=DATA_PATH):
    notes = []
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line:
            notes.append(line)
    return notes


def _normalize(text):
    return " ".join(TOKEN_RE.findall(text.lower()))


def _terms(text):
    words = TOKEN_RE.findall(text.lower())
    terms = list(words)
    for word in words:
        if len(word) >= 2:
            terms.extend(f"c2:{word[index:index + 2]}" for index in range(len(word) - 1))
        if len(word) >= 3:
            terms.extend(f"c3:{word[index:index + 3]}" for index in range(len(word) - 2))
    return terms


def prepare_index(path=DATA_PATH):
    notes = load_notes(path)
    counts = tuple(Counter(_terms(note)) for note in notes)
    document_frequency = Counter()
    for item in counts:
        document_frequency.update(item.keys())
    average_length = sum(map(len, counts)) / len(counts) if counts else 0.0
    return SearchIndex(tuple(notes), counts, document_frequency, average_length)


def _bm25(query_terms, counts, document_frequency, document_count, average_length):
    if not query_terms or not counts or not average_length:
        return 0.0
    score = 0.0
    document_length = sum(counts.values())
    for term in set(query_terms):
        frequency = counts.get(term, 0)
        if not frequency:
            continue
        frequency_in_documents = document_frequency.get(term, 0)
        inverse_frequency = math.log(1 + (document_count - frequency_in_documents + 0.5) / (frequency_in_documents + 0.5))
        denominator = frequency + 1.5 * (1 - 0.75 + 0.75 * document_length / average_length)
        score += inverse_frequency * frequency * 2.5 / denominator
    return score


def search(question, index=None, top_k=3):
    if index is None:
        index = prepare_index()
    query_terms = _terms(question)
    normalized_question = _normalize(question)
    document_count = len(index.notes)
    raw = []
    for note, counts in zip(index.notes, index.term_counts):
        lexical = _bm25(
            query_terms,
            counts,
            index.document_frequency,
            document_count,
            index.average_length,
        )
        similarity = SequenceMatcher(None, normalized_question, _normalize(note)).ratio()
        raw.append((lexical, similarity, note))
    maximum_lexical = max((lexical for lexical, _, _ in raw), default=0.0)
    scored = []
    for lexical, similarity, note in raw:
        lexical_score = lexical / maximum_lexical if maximum_lexical else 0.0
        score = min(1.0, lexical_score * 0.9 + similarity * 0.1)
        scored.append((score, note))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[:max(0, top_k)]


def build_rag_prompt(question, results):
    lines = ["아래 자료만 보고 답해 줘. 자료에 없는 내용은 없다고 말해 줘.", "", "[찾은 자료]"]
    for rank, (_, note) in enumerate(results, 1):
        lines.append(f"{rank}. {note}")
    lines.extend(["", f"질문: {question}"])
    return "\n".join(lines)


def run_search():
    index = prepare_index()
    print("가벼운 문법 검색을 시작합니다. 끝내려면 '그만'을 입력하세요.")
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
