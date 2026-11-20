from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

import bot
import main as cli_main
import search as semantic_search

ROOT = Path(__file__).resolve().parent
SEARCH_INDEX = None


class AgentHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        if self.path.startswith("/api/"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        req_path = unquote(parsed.path)

        if req_path == "/api/health":
            self._send_json(HTTPStatus.OK, {"ok": True})
            return

        if req_path == "/":
            self.path = "/index.html"
        elif req_path.startswith("/data/") or req_path.startswith("/."):
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/menu":
            self._handle_menu()
            return
        if parsed.path == "/api/chat":
            self._handle_chat()
            return
        if parsed.path == "/api/search":
            self._handle_search()
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def _handle_menu(self):
        try:
            data = self._read_json()
        except (ValueError, UnicodeDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON"})
            return

        choice = str(data.get("choice", "")).strip()
        if choice == "1":
            cli_main.record_usage("소개")
            lines = [
                "[typing] 영작 Agent",
                "- 소개·영작·필사·Docs: 정적 프론트엔드",
                "- FAQ 대화: data/faq.txt",
                "- 대화 기록: data/agent.db",
            ]
            self._send_json(HTTPStatus.OK, {"choice": "1", "message": "\n".join(lines)})
            return

        if choice == "2":
            cli_main.record_usage("대화")
            self._send_json(
                HTTPStatus.OK,
                {
                    "choice": "2",
                    "message": "이름 또는 별명을 입력하세요. (입력하지 않거나 건너뛰면 '사용자'로 시작합니다)",
                },
            )
            return

        if choice == "3":
            cli_main.record_usage("뜻으로 찾기")
            self._send_json(
                HTTPStatus.OK,
                {
                    "choice": "3",
                    "message": "영문법 질문을 입력하세요. 문법 자료에서 뜻이 가까운 원문 세 줄을 찾습니다.",
                },
            )
            return

        if choice == "0":
            self._send_json(HTTPStatus.OK, {"choice": "0", "message": "종료합니다."})
            return

        self._send_json(
            HTTPStatus.BAD_REQUEST,
            {"error": "1, 2, 3, 0 중에서 선택하세요."},
        )

    def _handle_search(self):
        global SEARCH_INDEX
        try:
            data = self._read_json()
        except (ValueError, UnicodeDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON"})
            return

        question = str(data.get("question", "")).strip()
        if not question:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "문법 질문을 입력하세요."})
            return

        if question == "그만":
            self._send_json(HTTPStatus.OK, {"message": "뜻으로 찾기를 마칩니다.", "ended": True})
            return

        try:
            if SEARCH_INDEX is None:
                SEARCH_INDEX = semantic_search.prepare_index()
            results = semantic_search.search(question, index=SEARCH_INDEX, top_k=3)
        except Exception as error:
            self._send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": f"문법 검색을 실행하지 못했습니다: {error}"},
            )
            return

        self._send_json(
            HTTPStatus.OK,
            {
                "question": question,
                "results": [
                    {"rank": rank, "score": round(float(score), 3), "text": note}
                    for rank, (score, note) in enumerate(results, 1)
                ],
                "prompt": semantic_search.build_rag_prompt(question, results),
                "ended": False,
            },
        )

    def _handle_chat(self):
        try:
            data = self._read_json()
        except (ValueError, UnicodeDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON"})
            return

        question = str(data.get("question", "")).strip()
        name = str(data.get("name", "")).strip() or "사용자"

        if not question:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "질문을 입력하세요."})
            return

        if question == "그만":
            self._send_json(HTTPStatus.OK, {"answer": "대화를 마칩니다.", "ended": True})
            return

        rules = bot.load_faq()
        answer = bot.find_answer(question, rules)
        now = datetime.now().isoformat(timespec="seconds")
        turns = [(now, name, question), (now, "typing", answer)]
        bot.save_chat(turns)

        self._send_json(HTTPStatus.OK, {"answer": answer, "ended": False, "name": name})


def run():
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), AgentHandler)
    print(f"Serving typing Agent at http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
