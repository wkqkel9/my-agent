---
layout: default
title: 서비스 동작 구조
---

# 서비스 동작 구조 (Architecture)

이 문서는 `typing` 영작 연습 및 안내 서비스의 프론트엔드와 AI 백엔드 간의 전체 동작 흐름, 데이터 처리 원칙, 폴백(Fallback) 구조를 설명합니다.

---

## 1. 전체 아키텍처 다이어그램

```mermaid
flowchart TD
    subgraph Client ["브라우저 (my-agent / GitHub Pages)"]
        User["사용자 입력"] --> Enter["Enter 제출"]
        Enter --> LocalEval["1차: 브라우저 정규식 판정 (0ms)"]
        LocalEval --> DisplayLocal["즉시 피드백 표시 / 하이라이트"]
        DisplayLocal --> CallBackend{"로컬 AI 백엔드 호출 (fetch)"}
    end

    subgraph Backend ["로컬 PC 백엔드 (writing-server :8000)"]
        CallBackend -->|"서버 실행 중"| API["/api/assess"]
        API --> Evaluator["프롬프트 조립 (Lesson 2)"]
        Evaluator --> Gemini["Gemini 3.8 Flash API"]
        Gemini --> JSONOutput["구조적 JSON 응답 (Lesson 5)"]
        JSONOutput --> DB[("SQLite agent.db (Lesson 6)")]
        JSONOutput --> ReturnAI["AI 피드백 반환"]
    end

    ReturnAI -->|"피드백 업데이트"| UpdateFeedback["AI 정밀 피드백 갱신 (시제·어휘 구체화)"]
    CallBackend -->|"서버 꺼짐 (오류/타임아웃)"| Fallback["기존 정규식 피드백 유지 (무중단)"]
```

---

## 2. 모듈별 역할 및 분리 원칙

```mermaid
graph LR
    subgraph PublicRepo ["my-agent (공개 저장소 / GitHub Pages)"]
        Index["index.html (웹 UI)"]
        Chatbot["chatbot.js (규칙 FAQ 챗봇)"]
        Docs["Docs (PLANNING / lesson)"]
    end

    subgraph PrivateRepo ["writing-server (로컬 전용 백엔드)"]
        Main["main.py (HTTP API 서버)"]
        Eval["evaluator.py (Gemini AI 평가 엔진)"]
        Database["db.py (SQLite 이력 보관)"]
        Secret[".env (비밀 API 키 보관)"]
    end

    Index <-->|"JSON API 통신 (:8000)"| Main
    Eval --- Secret
    Main --- Database
```

* **보안 및 키 분리 (Lesson 2)**:
  * GitHub Pages로 배포되는 `my-agent` 저장소에는 **절대로 API 키나 비밀값을 두지 않습니다.**
  * Gemini API 키는 로컬의 `writing-server/.env`에만 안전하게 보관됩니다.
* **비동기 이중 판정 (하이브리드 & 무중단 폴백)**:
  * 엔터 즉시 브라우저 정규식으로 기본 피드백(또는 정답 패스)을 0초 만에 띄워 사용자 경험을 유지합니다.
  * 로컬 AI 백엔드가 실행 중이면 백그라운드에서 Gemini의 정밀 평가 결과(정확한 시제/어휘 차이 및 하이라이트)를 받아 피드백을 자연스럽게 갱신합니다.
  * 로컬 서버가 꺼져 있거나 타임아웃(1.5초)이 발생해도 에러 창 없이 정규식 피드백이 그대로 유지됩니다.

---

## 3. 영작 평가 순서 및 우선순위 (기획 규칙)

AI 프롬프트와 로컬 판정기는 모두 다음 우선순위 규칙을 엄격하게 준수합니다:

```mermaid
flowchart TD
    A["사용자 문장 입력"] --> B{"1. 불필요한 표현이 있는가?<br>(문제에 없는 뜻/단어 추가)"}
    B -->|"Yes"| B1["불필요한 표현 안내 (extra)<br>※ 철자/문법 오류가 있어도 제거 먼저 안내"]
    B -->|"No"| C{"2. 틀린 표현이 있는가?<br>(시제, 문법, 품사, 철자 오타)"}
    C -->|"Yes"| C1["틀린 표현 / 철자 수정 방향 안내 (error/typo)<br>※ 절대 정답 문장을 공개하지 않음"]
    C -->|"No"| D{"3. 빠진 표현이 있는가?<br>(주어, 목적어, 필수 수식구 누락)"}
    D -->|"Yes"| D1["빠진 표현 안내 (incomplete)<br>※ 누락된 의미 성분 추가 유도"]
    D -->|"No"| E["정답 처리 (correct) ➔ 다음 문장 진행"]
```

---

## 4. 데이터 저장 및 복습 흐름 (Lesson 6)

```mermaid
sequenceDiagram
    autonumber
    actor User as 사용자
    participant UI as index.html
    participant Server as writing-server
    participant AI as Gemini 3.8 Flash
    participant DB as SQLite (agent.db)

    User->>UI: 문장 입력 후 Enter
    UI->>UI: 1차 로컬 판정 결과 즉시 렌더링
    UI->>Server: POST /api/assess {text, round, session_id}
    Server->>AI: 지시문 + 문제 문맥 전달
    AI-->>Server: 구조적 JSON 응답 반환
    Server->>DB: 제출 문장, 오류 종류, 피드백 기록
    Server-->>UI: 최종 AI 판정 JSON 반환
    UI->>UI: 정밀 힌트 및 오류 위치(range) 하이라이트 갱신
```

* 사용자의 제출 답안과 AI 피드백 내역은 로컬 PC의 `writing-server/data/agent.db`에 영구 보관되어 추후 오답 분석 및 학습 복습에 활용됩니다.
