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
