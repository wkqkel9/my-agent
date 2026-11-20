# typing

영어 문장 확장과 따라 쓰기 연습, 그리고 이용 방법을 안내하는 FAQ Agent입니다.

## 구조

```text
index.html          소개 · 영작/필사 데모
app/writing.html    영작 연습 전용 페이지
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
