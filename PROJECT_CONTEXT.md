# 현재 구현 상태

- 공개 화면은 `index.html` 한 페이지다. 메인 기능은 실전 영작 훈련이고, 아래에 서비스 소개와 동작·배포 아키텍처를 보여 준다.
- 2회차 FAQ 자료와 3회차 영문법 검색 자료는 분리되어 있다.
- `settings.py`, `embed.py`, `compare.py`, `search.py`가 로컬 임베딩 검색을 담당한다.
- `main.py`의 메뉴 3에서 `data/grammar_guide.txt`를 검색한다.
- `models/`, `.venv/`, `data/agent.db`는 Git에서 제외한다.
- Docker 빌드는 공개 임베딩 모델을 이미지 안에 준비하며 SQLite가 있는 `data/`만 호스트에 유지한다.
- 웹 챗봇 메뉴 3이 `/api/search`를 통해 같은 `search.py`를 실행한다.
- 기능 페이지의 3회차 칸에 실제 크기 웹 채팅창에서 메뉴 3을 실행한 PNG 캡처를 넣었다. 캡처에는 실제 질문과 가까운 원문 세 줄·점수가 보이며 자동 AI 답은 포함하지 않는다.
- 기능 페이지의 2회차 칸도 실제 크기 웹 채팅창에서 FAQ 질문 두 개를 실행한 PNG 캡처를 사용한다.
- GitHub Pages 워크플로는 자동 배포하지 않고 수동 실행만 허용한다. Python·Docker 전체 기능은 다른 컴퓨터에서도 저장소를 clone해 Render 등의 Web Service로 별도 배포할 수 있다.
