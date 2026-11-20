# typing

영어 문장 확장과 따라 쓰기 연습, 그리고 이용 방법을 안내하는 FAQ Agent입니다.

## 구조

```text
index.html          소개 · 영작/필사 데모
app/writing.html    영작 연습 전용 페이지
app/copywriting.html 필사 연습 전용 페이지
app/features.html   회차별 추가 기능 기록
app/js/chatbot.js   웹 챗봇 UI (로컬/Docker 백엔드 연동)
server.py           정적 웹 서빙 + main.py/bot.py 연결 서버
main.py             로컬 Python Agent 메뉴
bot.py              FAQ 규칙 대화
data/faq.txt        검토한 FAQ 규칙
data/grammar_guide.txt  3회차 영문법 검색 자료
data/agent.db       로컬 SQLite 기록 (Git 제외)
planning/writing.md 영작 기능 기획 문서
Dockerfile          컨테이너 실행 정의
docker-compose.yml  로컬/이동 실행 및 data/ 볼륨 연결
```

## 실행 방법

- **Docker로 웹 + 챗봇 한 번에 실행**:
  ```bash
  cp .env.example .env
  # .env에 Supabase URL과 publishable/anon key를 입력합니다.
  docker compose up --build
  ```
  첫 빌드에서 공개 임베딩 모델을 이미지 안에 준비합니다. 실행 후 브라우저에서 [http://127.0.0.1:8000](http://127.0.0.1:8000)으로 접속합니다.

- **터미널 CLI로 실행**:
  ```bash
  python3 main.py
  ```
  메뉴 `2`에서는 FAQ 대화를, 메뉴 `3`에서는 문법 자료의 뜻 검색을 실행할 수 있습니다.

## 3회차 · 뜻으로 찾기

`data/grammar_guide.txt`의 영문법 자료를 로컬 임베딩 모델로 비교해 질문과 뜻이 가까운 원문 세 줄과 점수를 보여 줍니다. 이어서 찾은 원문을 포함한 답변용 질문을 출력하며 모델 API는 호출하지 않습니다.

기능 페이지의 3회차 칸에는 로컬 웹에서 직접 실행해 캡처한 실제 질문, 검색된 원문 세 줄과 점수를 기록했습니다. 로컬 웹에서는 챗봇의 메뉴 `3. 문법 뜻으로 찾기`로 같은 검색을 실행할 수 있습니다.

기능 페이지의 2회차 칸도 로컬 웹에서 FAQ 질문 두 개를 직접 실행해 `bot.py`가 답한 실제 화면을 캡처해 사용합니다.

## 4회차 · Supabase 로그인과 연습 권한

회원가입·로그인은 Supabase Auth에서 처리하고, 사용자별 설정과 영작·필사 권한은 Supabase DB에서 RLS로 제한합니다. 화면에서는 아이디와 비밀번호만 받습니다. 서버는 아이디를 소문자로 정규화하고, Supabase 프로젝트 호스트를 이메일 도메인으로 붙여 내부 이메일(예: `account-a@your-project-ref.supabase.co`)을 만들어 Auth에 전달합니다. 메일을 받을 주소가 아니므로 Supabase 대시보드의 **Authentication → Providers → Email**에서 이메일 확인(Confirm email)을 꺼야 가입 직후 바로 로그인할 수 있습니다. 비밀번호는 Supabase 최소 길이 정책을 따릅니다.

Supabase SQL Editor에서 `supabase/schema.sql`을 실행합니다. 앱에서 테스트 계정 A와 B를 가입한 뒤, SQL 파일 하단의 권한 부여 쿼리에서 아이디와 프로젝트 호스트로 만든 이메일을 지정해 실행합니다. A에는 `writing`, `copywriting` 권한을 주고 B는 권한 행을 만들지 않으면 기본 차단됩니다. 소개 페이지와 챗봇은 계속 공개이며, 영작·필사 연습 위에 권한 안내가 표시됩니다.

계정별 설정은 `/api/preferences`에서 읽고 저장하며 `user_id = auth.uid()` RLS 정책을 따릅니다. 로그아웃 시 브라우저 세션을 지우고, A→B 전환 때 각 계정은 자기 설정 행만 읽습니다.
