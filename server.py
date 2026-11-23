from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os, urllib.error, urllib.request
import re
import random
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote, unquote, urlparse, parse_qs

import bot
import search as semantic_search
from training_commands import CATEGORIES, LEVELS as CEFR_LEVELS, SYSTEM_PROMPT, TOOLS, resolve_tool_call

ROOT = Path(__file__).resolve().parent
SEARCH_INDEX = None
CURRICULUM_PATH = ROOT / "data" / "curriculum.json"


def _load_curriculum():
    raw = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))
    expressions = []
    for day in raw["days"]:
        for expression_id, phrase, meaning in day["expressions"]:
            expressions.append({
                "id": expression_id,
                "day": day["day"],
                "theme": day["theme"],
                "grammar_focus": day.get("grammar_focus", ""),
                "sentence_roles": day.get("sentence_roles", []),
                "phrase": phrase,
                "meaning": meaning,
            })
    return expressions


CURRICULUM = _load_curriculum()
CURRICULUM_BY_ID = {item["id"]: item for item in CURRICULUM}
CEFR_GUIDES = {
    "A2": "Use 6 to 9 clear words. Describe one event with a simple past sentence.",
    "B1": "Use 10 to 14 words. Connect one situation and one action with a basic linker such as because, when, or so.",
    "B1+": "Use 12 to 18 words. Use two connected ideas and naturally include a subordinate clause or the requested grammar.",
    "B2": "Use 16 to 22 words. Make a concise STAR-style sentence with a precise connector, cause, action, or result.",
    "B2+": "Use 20 to 28 words. Explain a nuanced professional choice, result, or trade-off without sounding overly formal.",
}

def _load_env_file():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))

_load_env_file()

# ----- Authentication helpers -----
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")

def _supabase(path: str, method="GET", token=None, payload=None, extra_headers=None):
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError("Supabase 설정이 없습니다. SUPABASE_URL과 SUPABASE_ANON_KEY를 지정하세요.")
    headers = {"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if extra_headers:
        headers.update(extra_headers)
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(f"{SUPABASE_URL}{path}", data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        try: detail = json.loads(error.read())
        except Exception: detail = {}
        raise ValueError(detail.get("msg") or detail.get("message") or detail.get("error_description") or "Supabase 요청이 거절됐습니다.") from error

def _auth_user(self):
    auth = self.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        try:
            user = _supabase("/auth/v1/user", token=token)
            return user.get("id")
        except Exception:
            return None
    return None

def _username_email(username: str) -> str:
    username = username.strip().lower()
    if not re.fullmatch(r"[a-z0-9_.-]{3,32}", username):
        raise ValueError("아이디는 영문 소문자, 숫자, 밑줄, 점, 하이픈으로 3~32자 입력하세요.")
    auth_domain = urlparse(SUPABASE_URL).hostname
    if not auth_domain:
        raise RuntimeError("Supabase URL 설정이 없습니다.")
    return f"{username}@{auth_domain}"




def _call_chat_completion(payload, decode):
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    providers = []
    if groq_key:
        providers.append(("https://api.groq.com/openai/v1/chat/completions", groq_key, "openai/gpt-oss-120b"))

    if openai_key:
        providers.append(("https://api.openai.com/v1/chat/completions", openai_key, "gpt-4o-mini"))

    if not providers:
        return None

    for endpoint, api_key, model in providers:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "typing-Agent/1.0 (Mozilla/5.0)"
        }
        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps({**payload, "model": model}).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return decode(res_data["choices"][0]["message"])
        except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
            print(f"LLM API call failed ({model}): {type(error).__name__}")
            continue

    return None


def _call_llm_json(system_prompt: str, user_prompt: str, prefer: str = "groq"):
    return _call_chat_completion({
        "messages": [
            {"role": "system", "content": system_prompt + "\nYou must format your entire response as a valid JSON object."},
            {"role": "user", "content": user_prompt + "\nReturn strictly JSON."},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }, lambda message: json.loads(message["content"]))


def _call_training_command(text):
    return _call_chat_completion({
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "tools": TOOLS,
        "tool_choice": "auto",
        "parallel_tool_calls": False,
        "temperature": 0,
    }, lambda message: resolve_tool_call(message, text))


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
            self._send_json(HTTPStatus.OK, {"ok": True, "supabase_configured": bool(SUPABASE_URL and SUPABASE_ANON_KEY)})
            return
        if req_path == "/api/drill_history":
            self._handle_drill_history_get()
            return

        if req_path == "/":
            self.path = "/index.html"
        elif req_path.startswith("/data/") or req_path.startswith("/."):
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/training_command":
            try:
                text = self._read_json().get("text")
                if not isinstance(text, str) or not text.strip() or len(text) > 500:
                    raise ValueError("Invalid command text")
            except (ValueError, TypeError, AttributeError):
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "올바른 요청을 입력해 주세요."})
                return
            result = _call_training_command(text.strip())
            if result is None:
                self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "지금은 연습 명령을 해석할 수 없어요. 잠시 후 다시 시도해 주세요."})
            else:
                self._send_json(HTTPStatus.OK, result)
            return
        if parsed.path == "/api/focused_review":
            self._handle_focused_review()
            return
        if parsed.path == "/api/login":
            self._handle_login()
            return
        if parsed.path == "/api/refresh":
            self._handle_refresh()
            return
        if parsed.path == "/api/signup":
            self._handle_signup()
            return
        if parsed.path == "/api/logout":
            self._handle_logout()
            return
        if parsed.path == "/api/menu":
            self._handle_menu()
            return
        if parsed.path == "/api/chat":
            self._handle_chat()
            return
        if parsed.path == "/api/search":
            self._handle_search()
            return
        if parsed.path == "/api/assess":
            self._handle_assess()
            return
        if parsed.path == "/api/generate_question":
            self._handle_generate_question()
            return
        if parsed.path == "/api/drill_favorite":
            self._handle_drill_favorite()
            return
        if parsed.path == "/api/drill_history":
            self._handle_drill_history_get()
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
            lines = [
                "[typing] 영작 Agent",
                "- 소개·영작·필사·Docs: 정적 프론트엔드",
                "- FAQ 대화: data/faq.txt",
                "- 권한 사용 기록: Supabase",
            ]
            self._send_json(HTTPStatus.OK, {"choice": "1", "message": "\n".join(lines)})
            return

        if choice == "2":
            self._send_json(
                HTTPStatus.OK,
                {
                    "choice": "2",
                    "message": "이름 또는 별명을 입력하세요. (입력하지 않거나 건너뛰면 '사용자'로 시작합니다)",
                },
            )
            return

        if choice == "3":
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
        self._send_json(HTTPStatus.OK, {"answer": answer, "ended": False, "name": name})

    def _handle_signup(self):
        try:
            data = self._read_json()
            username = str(data.get("username", ""))
            email = _username_email(username)
            password = str(data.get("pwd", ""))
            if not password: raise ValueError
        except ValueError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error) or "아이디와 비밀번호를 입력하세요."}); return
        except Exception:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "아이디와 비밀번호를 입력하세요."}); return
        try:
            result = _supabase("/auth/v1/signup", method="POST", payload={"email": email, "password": password, "data": {"username": username.strip().lower()}})
        except (RuntimeError, ValueError) as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error)}); return
        self._send_json(HTTPStatus.CREATED, {"message": "가입 요청을 완료했습니다. Supabase 이메일 확인 설정에 따라 바로 로그인할 수 있습니다.", "session": result.get("session")})

    def _handle_login(self):
        try:
            data = self._read_json(); username = str(data.get("username", "")); email = _username_email(username); password = str(data.get("pwd", ""))
            if not password: raise ValueError
        except ValueError as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(error) or "아이디와 비밀번호를 입력하세요."}); return
        except Exception:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "아이디와 비밀번호를 입력하세요."}); return
        try:
            result = _supabase("/auth/v1/token?grant_type=password", method="POST", payload={"email": email, "password": password})
        except (RuntimeError, ValueError) as error:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": str(error)}); return
        self._send_json(HTTPStatus.OK, {"token": result.get("access_token"), "refresh_token": result.get("refresh_token"), "expires_at": result.get("expires_at")})

    def _handle_logout(self):
        auth = self.headers.get("Authorization", "")
        token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
        try:
            if token: _supabase("/auth/v1/logout", method="POST", token=token)
            self._send_json(HTTPStatus.OK, {"message": "Logged out"})
        except Exception as error:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(error)})

    def _handle_refresh(self):
        try:
            refresh_token = str(self._read_json().get("refresh_token", ""))
            if not refresh_token: raise ValueError("세션이 만료됐습니다. 다시 로그인하세요.")
            result = _supabase("/auth/v1/token?grant_type=refresh_token", method="POST", payload={"refresh_token": refresh_token})
        except (RuntimeError, ValueError) as error:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": str(error)}); return
        self._send_json(HTTPStatus.OK, {"token": result.get("access_token"), "refresh_token": result.get("refresh_token"), "expires_at": result.get("expires_at")})

    def _uses_supabase_training(self, user_id):
        """All learning data lives in the verified user's Supabase account."""
        return bool(SUPABASE_URL and SUPABASE_ANON_KEY and user_id and user_id == _auth_user(self))

    def _remote_rows(self, path, user_id):
        return _supabase(path, token=self._bearer_token())

    def _get_learner_profile(self, user_id):
        if not self._uses_supabase_training(user_id):
            raise PermissionError("로그인이 필요합니다.")
        rows = self._remote_rows(
            "/rest/v1/learner_profiles?select=*&user_id=eq." + quote(user_id) + "&limit=1", user_id
        )
        if rows:
            return rows[0]
        profile = {"user_id": user_id, "cefr_level": "B1", "success_streak": 0, "struggle_streak": 0}
        _supabase("/rest/v1/learner_profiles", method="POST", token=self._bearer_token(), payload=profile,
                  extra_headers={"Prefer": "return=minimal"})
        return profile

    def _pick_cefr_level(self, user_id, sequence):
        profile = self._get_learner_profile(user_id)
        base_index = CEFR_LEVELS.index(profile["cefr_level"])
        if sequence and sequence % 5 == 0 and base_index > 0:
            return CEFR_LEVELS[base_index - 1]
        if sequence and sequence % 4 == 0 and base_index < len(CEFR_LEVELS) - 1:
            return CEFR_LEVELS[base_index + 1]
        return CEFR_LEVELS[base_index]

    def _update_learner_level(self, user_id, question_level, outcome):
        profile = self._get_learner_profile(user_id)
        base_index = CEFR_LEVELS.index(profile["cefr_level"])
        question_index = CEFR_LEVELS.index(question_level) if question_level in CEFR_LEVELS else base_index
        success_streak = profile["success_streak"]
        struggle_streak = profile["struggle_streak"]

        if outcome == "correct":
            success_streak += 1
            struggle_streak = 0
            if question_index >= base_index and success_streak >= 2 and base_index < len(CEFR_LEVELS) - 1:
                base_index += 1
                success_streak = 0
        elif outcome == "incorrect":
            success_streak = 0
            struggle_streak += 1
            if question_index <= base_index and struggle_streak >= 2 and base_index > 0:
                base_index -= 1
                struggle_streak = 0
        else:
            success_streak = 0
            struggle_streak = 0

        if not self._uses_supabase_training(user_id):
            raise PermissionError("로그인이 필요합니다.")
        _supabase("/rest/v1/learner_profiles?on_conflict=user_id", method="POST", token=self._bearer_token(), payload={
            "user_id": user_id, "cefr_level": CEFR_LEVELS[base_index], "success_streak": success_streak,
            "struggle_streak": struggle_streak, "updated_at": datetime.now().isoformat(),
        }, extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"})

    def _pick_training_expression(self, user_id):
        now = datetime.now()
        if not self._uses_supabase_training(user_id):
            raise PermissionError("로그인이 필요합니다.")
        history = self._remote_rows("/rest/v1/drill_history?select=id&limit=10000", user_id)
        progress_rows = self._remote_rows("/rest/v1/expression_progress?select=*", user_id)
        sequence = len(history)
        states = {row["expression_id"]: row for row in progress_rows}

        due = []
        for expression_id, state in states.items():
            if expression_id not in CURRICULUM_BY_ID:
                continue
            sequence_due = state.get("next_due_sequence")
            time_due = state.get("next_due_at")
            if (sequence_due is not None and sequence_due <= sequence) or (time_due and time_due <= now.isoformat()):
                priority = {"incorrect": 0, "partial": 1, "review": 2, "mastered": 3}.get(state["stage"], 4)
                due.append((priority, state.get("last_seen_sequence") or 0, CURRICULUM_BY_ID[expression_id], state))
        if due:
            _, _, expression, state = min(due, key=lambda item: (item[0], item[1]))
            reason = {
                "incorrect": "오답 복습",
                "partial": "부분 정답 복습",
                "review": "간격 복습",
                "mastered": "유지 복습",
            }.get(state["stage"], "복습")
            return expression, "review", reason, sequence

        for day in range(1, 11):
            candidates = [item for item in CURRICULUM if item["day"] == day and item["id"] not in states]
            if candidates:
                return random.choice(candidates), "new", "새 핵심 표현", sequence

        expression = random.choice(CURRICULUM)
        return expression, "review", "유지 복습", sequence

    def _recent_training_context(self, user_id):
        if not self._uses_supabase_training(user_id):
            raise PermissionError("로그인이 필요합니다.")
        rows = self._remote_rows(
            "/rest/v1/drill_history?select=category,question_type&order=created_at.desc&limit=5", user_id
        )
        return [row.get("category") for row in rows if row.get("category")], [row.get("question_type") for row in rows if row.get("question_type")]

    def _handle_focused_review(self):
        import review_graph

        user_id = _auth_user(self)
        if not user_id:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "로그인하면 내 학습 기록으로 맞춤 복습을 추천받을 수 있어요."})
            return
        try:
            payload = self._read_json()
            if not isinstance(payload, dict):
                raise ValueError("Invalid review request")
        except (ValueError, TypeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "복습 요청을 확인해 주세요."})
            return

        if "thread_id" in payload:
            thread_id, approved = payload["thread_id"], payload.get("approved")
            if not isinstance(thread_id, str) or len(thread_id) != 32 or type(approved) is not bool:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "복습 결정을 확인해 주세요."})
                return
            result = review_graph.decide(user_id, thread_id, approved)
            if result is None:
                self._send_json(HTTPStatus.GONE, {"error": "이 추천은 만료됐어요. 맞춤 복습을 다시 요청해 주세요."})
                return
            self._send_json(HTTPStatus.OK, result)
            return

        try:
            rows = self._remote_rows(
                "/rest/v1/drill_history?select=expression_id,outcome,is_correct"
                "&user_id=eq." + quote(user_id, safe="") + "&order=created_at.desc&limit=30", user_id,
            )
        except (OSError, RuntimeError, ValueError):
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "학습 기록을 불러오지 못했어요. 잠시 후 다시 요청해 주세요."})
            return
        attempts = [
            {"expression_id": row["expression_id"],
             "outcome": row.get("outcome") or ("correct" if row.get("is_correct") is True else "incorrect")}
            for row in rows if row.get("expression_id") in CURRICULUM_BY_ID
        ]
        plan = review_graph.propose(user_id, attempts)
        if plan:
            plan["expression"] = CURRICULUM_BY_ID[plan["expression_id"]]["phrase"]
        self._send_json(HTTPStatus.OK, {"plan": plan})

    def _handle_generate_question(self):
        try:
            req_data = self._read_json()
        except Exception:
            req_data = {}
        requested_level = req_data.get("cefr_level", "auto")
        requested_topic = req_data.get("topic", "auto")
        previous_question = req_data.get("previous_question", "")
        focus_questions = req_data.get("focus_questions", [])
        if not isinstance(previous_question, str) or len(previous_question) > 500:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "이전 문제 형식이 올바르지 않습니다."})
            return
        if (not isinstance(focus_questions, list) or len(focus_questions) > 3
                or any(not isinstance(question, str) or len(question) > 500 for question in focus_questions)):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "복습 문제 형식을 확인해 주세요."})
            return
        if requested_level not in ["auto", *CEFR_LEVELS] or requested_topic not in ["auto", *CATEGORIES]:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "지원하지 않는 난이도 또는 주제입니다."})
            return
        user_id = _auth_user(self)
        focus_id = req_data.get("focus_expression_id")
        if focus_id is not None:
            if not user_id:
                self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "맞춤 복습을 계속하려면 로그인해 주세요."})
                return
            if not isinstance(focus_id, str) or focus_id not in CURRICULUM_BY_ID:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "복습할 표현을 확인해 주세요."})
                return
        if not user_id:
            expression = random.choice(CURRICULUM)
            training_mode = "trial"
            review_reason = "체험 문제"
            sequence = 0
            cefr_level = "B1"
            recent_categories, recent_types = [], []
        else:
            expression, training_mode, review_reason, sequence = self._pick_training_expression(user_id)
            cefr_level = self._pick_cefr_level(user_id, sequence)
            recent_categories, recent_types = self._recent_training_context(user_id)

        if focus_id is not None:
            expression = CURRICULUM_BY_ID[focus_id]
            training_mode, review_reason = "review", "약한 표현 집중 복습"
        if requested_level != "auto":
            cefr_level = requested_level
        interview_categories = ["사내 갈등 💼", "서버 장애 💻", "팀 프로젝트 🤝", "취업 면접 📋"]
        category_pool = interview_categories if training_mode == "new" else CATEGORIES
        available_categories = [item for item in category_pool if item not in recent_categories] or category_pool
        chosen_category = random.choice(available_categories)
        if requested_topic != "auto":
            chosen_category = requested_topic
        question_types = ["사건 설명", "비교", "가정 질문", "선택 이유", "요청", "의견", "회고", "설득"]
        day_types = expression["sentence_roles"] or question_types
        available_types = [item for item in day_types if item not in recent_types] or day_types
        question_type = random.choice(available_types)
        context_instruction = (
            "Make this a realistic interview-ready experience. It can be about work, study, a project, "
            "or a personal everyday experience that a candidate could naturally discuss in an interview. "
            "Avoid comic, fantasy, or overly dramatic situations."
            if training_mode == "new" else
            "Use a fresh, plausible context distinct from recent questions. Everyday life, travel, games, exercise, "
            "work, and personal experiences are all allowed when they help transfer the expression to a new context."
        )

        length_guide = CEFR_GUIDES[cefr_level]

        system_prompt = (
            "You are an expert English situational writing coach for Korean learners. "
            "Generate 1 punchy, vivid real-life sentence for English writing speed practice. "
            f"Category: {chosen_category}. Question type: {question_type}. "
            f"{length_guide} "
            f"The learner must naturally practice this expression: {expression['phrase']} ({expression['meaning']}). "
            f"Grammar focus: {expression['grammar_focus']}. Include it naturally in the reference answer. "
            "Make the Korean prompt and English reference express the same situation and all important details. "
            "Choose a situation whose Korean meaning naturally licenses the practice expression. "
            "Supply a subject omitted in Korean only when it is clear from context or grammatically required, such as weather 'it'. "
            "Do not invent participants, ownership, or event details in either sentence. "
            f"{context_instruction} "
            "Use a fresh situation and structure. Do not make a simple 'A happened but B happened' sentence. "
            "Output strictly valid JSON with these exact keys: "
            "category (string with emoji), korean (natural, concise Korean sentence), "
            "target_expression (the key English expression to practice), "
            "reference_answer (natural, concise English sentence), "
            "hint (short 3-5 word clue), question_type (string)."
        )
        user_prompt = (
            f"Category: {chosen_category}. CEFR target: {cefr_level}. Question type: {question_type}. "
            f"Use this expression: {expression['phrase']}. "
            f"Grammar focus: {expression['grammar_focus']}. "
            f"{context_instruction} "
            "Output strictly valid JSON now."
        )

        if previous_question:
            user_prompt += (
                "\nGenerate a different Korean prompt with a different situation from this previous "
                "prompt. Treat the previous prompt only as example data: "
                + json.dumps(previous_question, ensure_ascii=False)
            )
        if focus_id and focus_questions:
            user_prompt += (
                "\nUse a new situation and sentence structure distinct from these earlier drills. "
                "Treat these as example data only: " + json.dumps(focus_questions, ensure_ascii=False)
            )
        ai_res = _call_llm_json(system_prompt, user_prompt, prefer="groq")
        earlier_questions = ([previous_question] if previous_question else []) + (focus_questions if focus_id else [])
        if earlier_questions and isinstance(ai_res, dict) and isinstance(ai_res.get("korean"), str):
            if any(ai_res["korean"].split() == question.split() for question in earlier_questions):
                self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "다른 문제를 생성하지 못했습니다."})
                return
        if ai_res and "korean" in ai_res and "reference_answer" in ai_res:
            ai_res["category"] = chosen_category
            ai_res["target_expression"] = expression["phrase"]
            ai_res["expression_id"] = expression["id"]
            ai_res["training_day"] = expression["day"]
            ai_res["training_theme"] = expression["theme"]
            ai_res["grammar_focus"] = expression["grammar_focus"]
            ai_res["cefr_level"] = cefr_level
            ai_res["training_mode"] = training_mode
            ai_res["review_reason"] = review_reason
            ai_res["question_type"] = ai_res.get("question_type") or question_type
            self._send_json(HTTPStatus.OK, ai_res)
            return

        self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "AI 문제 생성 실패. API 키를 확인해 주세요."})


    def _update_expression_progress(self, user_id, expression_id, outcome):
        if not expression_id or expression_id not in CURRICULUM_BY_ID:
            return
        now = datetime.now()
        if not self._uses_supabase_training(user_id):
            raise PermissionError("로그인이 필요합니다.")
        sequence = len(self._remote_rows("/rest/v1/drill_history?select=id&limit=10000", user_id))
        rows = self._remote_rows("/rest/v1/expression_progress?select=*&expression_id=eq." + quote(expression_id) + "&limit=1", user_id)
        state = rows[0] if rows else {"correct_count": 0, "partial_count": 0, "incorrect_count": 0}
        correct_count = state["correct_count"] + (1 if outcome == "correct" else 0)
        partial_count = state["partial_count"] + (1 if outcome == "partial" else 0)
        incorrect_count = state["incorrect_count"] + (1 if outcome == "incorrect" else 0)
        if outcome == "incorrect":
            stage = "incorrect"
            next_sequence = sequence + random.randint(3, 5)
            next_due_at = None
        elif outcome == "partial":
            stage = "partial"
            next_sequence = sequence + random.randint(6, 10)
            next_due_at = None
        elif correct_count >= 3:
            stage = "mastered"
            next_sequence = None
            next_due_at = (now + timedelta(days=3)).isoformat()
        elif correct_count == 2:
            stage = "review"
            next_sequence = None
            next_due_at = (now + timedelta(days=1)).isoformat()
        else:
            stage = "review"
            next_sequence = sequence + 12
            next_due_at = None
        values = {
            "user_id": user_id, "expression_id": expression_id, "stage": stage,
            "correct_count": correct_count, "partial_count": partial_count, "incorrect_count": incorrect_count,
            "next_due_sequence": next_sequence, "next_due_at": next_due_at,
            "last_seen_sequence": sequence, "updated_at": now.isoformat(),
        }
        _supabase("/rest/v1/expression_progress?on_conflict=user_id,expression_id", method="POST", token=self._bearer_token(),
                  payload=values, extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"})

    def _handle_assess(self):
        try:
            payload = self._read_json()
        except Exception:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON"})
            return

        korean = payload.get("korean", "")
        target_expression = payload.get("target_expression", "")
        reference_answer = payload.get("reference_answer", "")
        category = payload.get("category", "")
        user_text = str(payload.get("user_text", "")).strip()
        time_spent = int(payload.get("time_spent", 0))
        user_id = _auth_user(self)
        expression_id = payload.get("expression_id", "")
        training_mode = payload.get("training_mode", "")
        question_type = payload.get("question_type", "")
        cefr_level = payload.get("cefr_level", "B1")

        # AI 평가
        system_prompt = (
            "You are a supportive, sharp native English coach. "
            "Grade against the Korean prompt. Accept equivalent vocabulary and sentence structures. "
            "The reference answer is illustrative. Mention the target expression only as an optional suggestion. "
            "Use correct when all important meanings are conveyed and errors do not impair comprehension. "
            "Use partial when the main situation is conveyed but an important detail such as intensity, negation, "
            "or timing is missing, or an error obscures part of the meaning. "
            "Use incorrect when the main situation changes or cannot be understood. "
            "For 갑자기 비가 쏟아졌다, 'It suddenly began to pour' is correct, "
            "'It suddenly rained' is partial, and 'It suddenly stopped raining' is incorrect. "
            "Set is_correct to true only when result is correct. "
            "Ignore lowercase at the start of a sentence when grading. Never flag it in feedback or lower the result for it. "
            "Preserve the learner's valid wording and structure in the correction. Never add facts absent from the Korean prompt. "
            "Give one to three concise Korean feedback points. Identify actual errors with specific before and after wording. "
            "Label natural alternatives as optional and never lower the grade for style alone. "
            "For a partial result, explain what the learner conveyed and what important meaning was missing.\n"
            "Output strictly valid JSON with keys: "
            "is_correct (boolean), corrected_sentence (string), feedback_points (array of 1-3 short Korean strings), "
            "missed_nuance (string or null), result (correct, partial, or incorrect)."
        )
        user_prompt = (
            f"Korean Prompt: {korean}\n"
            f"Target Expression: {target_expression}\n"
            f"Reference Answer: {reference_answer}\n"
            f"Candidate Answer: {user_text}"
        )

        ai_eval = _call_llm_json(system_prompt, user_prompt, prefer="groq")
        if ai_eval and "corrected_sentence" in ai_eval:
            is_correct = bool(ai_eval.get("is_correct"))
            corrected_sentence = ai_eval.get("corrected_sentence", reference_answer)
            feedback_points = ai_eval.get("feedback_points")
            if not isinstance(feedback_points, list):
                feedback_points = [ai_eval.get("reason") or ai_eval.get("short_reason", "")]
            feedback_points = [str(point).strip() for point in feedback_points if str(point).strip()][:3]
            short_reason = "\n".join(feedback_points)
            missed_nuance = ai_eval.get("missed_nuance")
            outcome = ai_eval.get("result")
            paraphrasing = []
        else:
            # API 없을 때 최소 폴백 (단어 수 기반)
            word_count = len(user_text.split())
            is_correct = word_count >= 5
            corrected_sentence = reference_answer or user_text
            short_reason = "AI 평가 서버에 연결할 수 없습니다. API 키를 확인해 주세요." if not reference_answer else \
                           f"참고 답안: {reference_answer}"
            feedback_points = [short_reason]
            missed_nuance = None
            outcome = "correct" if is_correct else "partial"
            paraphrasing = []

        if outcome not in ("correct", "partial", "incorrect"):
            outcome = "correct" if is_correct else ("partial" if missed_nuance else "incorrect")
        is_correct = outcome == "correct"

        if user_id:
            try:
                record = {
                    "user_id": user_id, "category": category, "korean": korean, "user_text": user_text,
                    "is_correct": is_correct, "time_spent": time_spent, "expression_id": expression_id,
                    "training_mode": training_mode, "question_type": question_type,
                    "target_expression": target_expression,
                    "corrected_sentence": corrected_sentence,
                    "feedback_points": feedback_points,
                    "missed_nuance": missed_nuance,
                    "outcome": outcome,
                }
                _supabase("/rest/v1/drill_history", method="POST", token=self._bearer_token(), payload=record,
                          extra_headers={"Prefer": "return=minimal"})
                self._update_expression_progress(user_id, expression_id, outcome)
                self._update_learner_level(user_id, cefr_level, outcome)
            except Exception as db_err:
                print("Failed to save drill history to db:", db_err)

        self._send_json(HTTPStatus.OK, {
            "is_correct": is_correct,
            "corrected_sentence": corrected_sentence,
            "short_reason": short_reason,
            "feedback_points": feedback_points,
            "missed_nuance": missed_nuance,
            "paraphrasing": paraphrasing,
            "target_expression": target_expression,
            "outcome": outcome,
        })

    def _handle_drill_favorite(self):
        try:
            payload = self._read_json()
            history_id = payload.get("id")
            favorite = 1 if payload.get("favorite") else 0
            user_id = _auth_user(self)
            if not user_id:
                self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "로그인이 필요합니다."})
                return
            _supabase(
                "/rest/v1/drill_history?id=eq." + quote(str(history_id)) + "&user_id=eq." + quote(user_id),
                method="PATCH",
                token=self._bearer_token(),
                payload={"favorite": bool(favorite)},
                extra_headers={"Prefer": "return=minimal"},
            )
            self._send_json(HTTPStatus.OK, {"ok": True})
        except Exception as e:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(e)})

    def _handle_drill_history_get(self):
        user_id = _auth_user(self)
        if not user_id:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "로그인이 필요합니다."})
            return
        try:
            path = "/rest/v1/drill_history?select=*&user_id=eq." + quote(user_id) + "&order=created_at.desc&limit=50"
            rows = self._remote_rows(path, user_id)
            self._send_json(HTTPStatus.OK, {"history": rows})
        except Exception as e:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(e)})

    def _bearer_token(self):
        auth = self.headers.get("Authorization", "")
        return auth[7:].strip() if auth.lower().startswith("bearer ") else ""


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
