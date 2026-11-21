from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os, urllib.error, urllib.request
import re
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

import bot
import search as semantic_search

ROOT = Path(__file__).resolve().parent
SEARCH_INDEX = None

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

# ----- Authentication & Authorization helpers -----
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

def _check_permission(self, user_id: str, feature: str) -> bool:
    auth = self.headers.get("Authorization", "")
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    try:
        rows = _supabase(
            "/rest/v1/permissions?select=allowed&user_id=eq." + quote(user_id) +
            "&feature=eq." + quote(feature) + "&limit=1",
            token=token,
        )
        return bool(rows and rows[0].get("allowed") is True)
    except Exception:
        return False

def _username_email(username: str) -> str:
    username = username.strip().lower()
    if not re.fullmatch(r"[a-z0-9_.-]{3,32}", username):
        raise ValueError("아이디는 영문 소문자, 숫자, 밑줄, 점, 하이픈으로 3~32자 입력하세요.")
    auth_domain = urlparse(SUPABASE_URL).hostname
    if not auth_domain:
        raise RuntimeError("Supabase URL 설정이 없습니다.")
    return f"{username}@{auth_domain}"




def _call_llm_json(system_prompt: str, user_prompt: str, prefer: str = "groq"):
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    # 우선순위에 따른 제공자 목록 구성
    providers = []
    if prefer == "gemini":
        if gemini_key:
            providers.append(("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", gemini_key, "gemini-2.0-flash"))
        if groq_key:
            providers.append(("https://api.groq.com/openai/v1/chat/completions", groq_key, "openai/gpt-oss-120b"))
    else:  # 초고속 채점용 groq 우선
        if groq_key:
            providers.append(("https://api.groq.com/openai/v1/chat/completions", groq_key, "openai/gpt-oss-120b"))
        if gemini_key:
            providers.append(("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", gemini_key, "gemini-2.0-flash"))

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
        # Groq json_object 필수 조건: 프롬프트에 'json' 단어가 반드시 포함되어야 함
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt + "\nYou must format your entire response as a valid JSON object."},
                {"role": "user", "content": user_prompt + "\nReturn strictly JSON."}
            ],
            "temperature": 0.6 if prefer == "gemini" else 0.2,
            "response_format": {"type": "json_object"}
        }

        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                content = res_data["choices"][0]["message"]["content"]
                return json.loads(content)
        except Exception as e:
            print(f"LLM API Call error ({model}):", e)
            continue

    return None


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
        if req_path == "/api/preferences":
            self._handle_preferences_get()
            return
        if req_path == "/api/access-summary":
            self._handle_access_summary()
            return
        if req_path == "/api/access-runs":
            self._handle_access_runs()
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
        if parsed.path == "/api/login":
            self._handle_login()
            return
        if parsed.path == "/api/refresh":
            self._handle_refresh()
            return
        if parsed.path == "/api/signup":
            self._handle_signup()
            return
        if parsed.path == "/api/has_permission":
            self._handle_has_permission()
            return
        if parsed.path == "/api/logout":
            self._handle_logout()
            return
        if parsed.path == "/api/practice-access":
            self._handle_practice_access()
            return
        if parsed.path == "/api/preferences":
            self._handle_preferences_put()
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

    def _handle_has_permission(self):
        user_id = _auth_user(self)
        if not user_id:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "Login required"}); return
        try: feature = str(self._read_json().get("feature", ""))
        except Exception: feature = ""
        self._send_json(HTTPStatus.OK, {"allowed": _check_permission(self, user_id, feature)})

    def _handle_practice_access(self):
        user_id = _auth_user(self)
        if not user_id:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "로그인이 필요합니다."}); return
        try: feature = str(self._read_json().get("feature", ""))
        except Exception: feature = ""
        if feature not in ("writing", "copywriting"):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "잘못된 기능입니다."}); return
        if not _check_permission(self, user_id, feature):
            self._record_access(user_id, feature, "denied")
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "이 연습을 이용할 권한이 없습니다."}); return
        self._record_access(user_id, feature, "ok")
        self._send_json(HTTPStatus.OK, {"allowed": True})

    def _handle_preferences_get(self):
        token = self._bearer_token()
        user_id = _auth_user(self)
        if not user_id:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "로그인이 필요합니다."}); return
        try:
            rows = _supabase("/rest/v1/preferences?select=default_location,location_kind&limit=1", token=token)
        except Exception as error:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(error)}); return
        self._send_json(HTTPStatus.OK, rows[0] if rows else {"default_location":"", "location_kind":""})

    def _handle_access_summary(self):
        user_id = _auth_user(self)
        if not user_id:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "로그인이 필요합니다."})
            return
        token = self._bearer_token()
        try:
            rows = _supabase(
                "/rest/v1/access_runs?select=feature,outcome&user_id=eq." + quote(user_id) + "&limit=10000",
                token=token,
            )
        except Exception as error:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(error)})
            return
        summary = {feature: {"allowed": 0, "denied": 0} for feature in ("writing", "copywriting")}
        for row in rows:
            feature = row.get("feature")
            outcome = row.get("outcome")
            if feature in summary and outcome in ("ok", "denied"):
                summary[feature]["allowed" if outcome == "ok" else "denied"] += 1
        self._send_json(HTTPStatus.OK, {"summary": summary})

    def _handle_access_runs(self):
        user_id = _auth_user(self)
        if not user_id:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "로그인이 필요합니다."})
            return
        try:
            limit = max(1, min(int(urlparse(self.path).query.split("limit=")[-1].split("&")[0]), 100)) if "limit=" in self.path else 30
        except ValueError:
            limit = 30
        token = self._bearer_token()
        try:
            rows = _supabase(
                "/rest/v1/access_runs?select=id,feature,outcome,created_at&user_id=eq." + quote(user_id) +
                "&order=created_at.desc&limit=" + str(limit),
                token=token,
            )
        except Exception as error:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(error)})
            return
        self._send_json(HTTPStatus.OK, {"runs": [
            {"id": row.get("id"), "feature": row.get("feature"), "outcome": row.get("outcome"), "timestamp": row.get("created_at")}
            for row in rows
        ]})

    def _handle_preferences_put(self):
        token = self._bearer_token()
        user_id = _auth_user(self)
        if not user_id:
            self._send_json(HTTPStatus.UNAUTHORIZED, {"error": "로그인이 필요합니다."}); return
        try:
            data = self._read_json()
            location = str(data.get("default_location", "")).strip()[:120]
            kind = str(data.get("location_kind", "")).strip()[:80]
            rows = _supabase("/rest/v1/preferences?on_conflict=user_id", method="POST", token=token,
                payload={"user_id": user_id, "default_location": location, "location_kind": kind},
                extra_headers={"Prefer":"resolution=merge-duplicates,return=representation"})
        except (ValueError, UnicodeDecodeError) as error:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "잘못된 설정 데이터입니다."}); return
        except Exception as error:
            self._send_json(HTTPStatus.BAD_GATEWAY, {"error": str(error)}); return
        self._send_json(HTTPStatus.OK, rows[0] if rows else {"default_location":location, "location_kind":kind})




    def _handle_generate_question(self):
        try:
            req_data = self._read_json()
        except Exception:
            req_data = {}

        category = req_data.get("category")
        review_exp = req_data.get("review_expression")
        level = req_data.get("level", "medium")

        CATEGORIES = [
            "해외여행 ✈️", "게임 버그 🎮", "헬스장 🏋️", "배달 사고 🍕",
            "사내 갈등 💼", "고양이 집사 🐱", "서버 장애 💻", "당근마켓 거래 📦",
            "팀 프로젝트 🤝", "지하철 사고 🚇", "소개팅 😅", "카페 진상 ☕",
            "취업 면접 📋", "운전 초보 🚗", "반려견 산책 🐶"
        ]
        import random
        chosen_category = category or random.choice(CATEGORIES)

        if level == "easy":
            length_guide = (
                "LEVEL: EASY (BEGINNER). Make it very SHORT, simple, and clean (6 to 10 English words in reference_answer). "
                "The Korean sentence must be very concise (8 to 12 words), expressing exactly 1 clear situation and 1 action. "
                "Example: '비가 너무 많이 와서 결국 택시를 탔어요.' -> 'It rained heavily, so I ended up taking a taxi.' "
                "Never write complicated multi-clause sentences."
            )
        elif level == "hard":
            length_guide = (
                "LEVEL: HARD. A professional multi-clause sentence (15 to 22 English words in reference_answer). "
                "Suitable for in-depth STAR interview scenarios."
            )
        else: # medium (default)
            length_guide = (
                "LEVEL: MEDIUM (PUNCHY SPEED DRILL). Keep it concise and clean (10 to 14 English words in reference_answer). "
                "Korean sentence must be a single clean sentence (12 to 16 words) with 1 situation + 1 result. "
                "Example: '보스전을 하던 중에 갑자기 게임이 튕겼습니다.' -> 'While I was in a boss fight, the game suddenly crashed.' "
                "Do NOT add unnecessary rambling clauses."
            )

        system_prompt = (
            "You are an expert English situational writing coach for Korean learners. "
            "Generate 1 punchy, vivid real-life sentence for English writing speed practice. "
            f"Category: {chosen_category}. "
            f"{length_guide} "
            "The Korean sentence must require a practical expression (e.g. ended up ~ing, had trouble ~ing, had to, without discussing beforehand, an issue occurred, couldn't help but). "
            "Output strictly valid JSON with these exact keys: "
            "category (string with emoji), korean (natural, concise Korean sentence), "
            "target_expression (the key English expression to practice), "
            "reference_answer (natural, concise English sentence), "
            "hint (short 3-5 word clue)."
        )
        user_prompt = (
            f"Category: {chosen_category}. Difficulty: {level}. "
            f"{'Use this expression: ' + review_exp if review_exp else 'Pick 1 practical everyday expression.'} "
            "Output strictly valid JSON now."
        )

        ai_res = _call_llm_json(system_prompt, user_prompt, prefer="gemini")
        if ai_res and "korean" in ai_res and "reference_answer" in ai_res:
            ai_res.setdefault("category", chosen_category)
            self._send_json(HTTPStatus.OK, ai_res)
            return

        self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "AI 문제 생성 실패. API 키를 확인해 주세요."})


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
        user_id = _auth_user(self) or payload.get("user_id") or "guest"

        # AI 평가 (Groq 우선 → Gemini 폴백)
        system_prompt = (
            "You are a supportive, sharp native English coach. "
            "Evaluate the user's English sentence based on 3 clear criteria:\n"
            "1. Semantic Nuance: Did the user capture the Korean nuance? (e.g. '결국' -> 'ended up ~ing', '사전에 논의 없이' -> 'without discussing beforehand'). Explain the nuance clearly if missed.\n"
            "2. Grammar Accuracy: Check tense, prepositions, articles, and agreement.\n"
            "3. Natural Phrasing: Point out awkward direct translations and provide natural native phrasing.\n\n"
            "Write the feedback ('reason') in natural Korean. Be clear, constructive, and helpful (do NOT artificially compress it into one line).\n"
            "Output strictly valid JSON with keys: "
            "is_correct (boolean), corrected_sentence (string), reason (helpful Korean explanation), "
            "missed_nuance (string or null)."
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
            short_reason = ai_eval.get("reason") or ai_eval.get("short_reason", "")
            missed_nuance = ai_eval.get("missed_nuance")
            paraphrasing = []
        else:
            # API 없을 때 최소 폴백 (단어 수 기반)
            word_count = len(user_text.split())
            is_correct = word_count >= 5
            corrected_sentence = reference_answer or user_text
            short_reason = "AI 평가 서버에 연결할 수 없습니다. API 키를 확인해 주세요." if not reference_answer else \
                           f"참고 답안: {reference_answer}"
            missed_nuance = None
            paraphrasing = []

        # 기록 저장 (agent.db)
        try:
            db_path = ROOT / "data" / "agent.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            import sqlite3
            from datetime import datetime
            with sqlite3.connect(db_path) as db:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS drill_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT,
                        user_id TEXT,
                        category TEXT,
                        korean TEXT,
                        user_text TEXT,
                        is_correct INTEGER,
                        time_spent INTEGER,
                        favorite INTEGER DEFAULT 0
                    )
                """)
                db.execute(
                    "INSERT INTO drill_history (created_at, user_id, category, korean, user_text, is_correct, time_spent) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (datetime.now().isoformat(timespec="seconds"), user_id, category, korean, user_text, 1 if is_correct else 0, time_spent)
                )
        except Exception as db_err:
            print("Failed to save drill history to db:", db_err)

        self._send_json(HTTPStatus.OK, {
            "is_correct": is_correct,
            "corrected_sentence": corrected_sentence,
            "short_reason": short_reason,
            "missed_nuance": missed_nuance,
            "paraphrasing": paraphrasing,
            "target_expression": target_expression
        })

    def _handle_drill_favorite(self):
        try:
            payload = self._read_json()
            history_id = payload.get("id")
            favorite = 1 if payload.get("favorite") else 0
            db_path = ROOT / "data" / "agent.db"
            import sqlite3
            with sqlite3.connect(db_path) as db:
                db.execute("UPDATE drill_history SET favorite = ? WHERE id = ?", (favorite, history_id))
            self._send_json(HTTPStatus.OK, {"ok": True})
        except Exception as e:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(e)})

    def _handle_drill_history_get(self):
        user_id = _auth_user(self) or "guest"
        db_path = ROOT / "data" / "agent.db"
        if not db_path.exists():
            self._send_json(HTTPStatus.OK, {"history": []})
            return
        try:
            import sqlite3
            with sqlite3.connect(db_path) as db:
                db.row_factory = sqlite3.Row
                cursor = db.execute("SELECT * FROM drill_history ORDER BY id DESC LIMIT 50")
                rows = [dict(r) for r in cursor.fetchall()]
                self._send_json(HTTPStatus.OK, {"history": rows})
        except Exception as e:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(e)})

    def _record_access(self, user_id, feature, outcome):
        token = self._bearer_token()
        if not token:
            return
        try:
            _supabase(
                "/rest/v1/access_runs",
                method="POST",
                token=token,
                payload={"user_id": user_id, "feature": feature, "outcome": outcome},
                extra_headers={"Prefer": "return=minimal"},
            )
        except Exception:
            print("Access run could not be recorded.")

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
