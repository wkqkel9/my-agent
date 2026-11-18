---
layout: default
title: 서비스 동작 구조
---

# 서비스 동작 구조

소개 페이지의 데모와 영작 전용 페이지는 같은 `writing.js`를 사용합니다. 공개 프론트엔드는 GitHub Pages, 평가 서버는 Vercel, 모델 API는 Groq입니다.

<svg viewBox="0 0 860 380" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg" style="background:#fff;border:1px solid #e2ded5;border-radius:12px;padding:16px;box-shadow:0 4px 12px rgba(0,0,0,0.03);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#8c8273"/>
    </marker>
    <marker id="arrow-orange" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill="#d9532f"/>
    </marker>
  </defs>

  <!-- 영역 1: 프론트엔드 -->
  <rect x="20" y="30" width="280" height="320" rx="10" fill="#fcfbf9" stroke="#d5cfc5" stroke-width="1.5" />
  <text x="35" y="60" font-size="15" font-weight="bold" fill="#2b2824">1. 프론트엔드 (GitHub Pages)</text>
  <text x="35" y="80" font-size="12" fill="#7a7267">index.html · writing.html / writing.js</text>

  <!-- 프론트 박스들 -->
  <rect x="40" y="105" width="240" height="50" rx="6" fill="#ffffff" stroke="#b0a89b" stroke-width="1.2"/>
  <text x="160" y="128" font-size="13" font-weight="600" text-anchor="middle" fill="#2b2824">사용자 문장 입력</text>
  <text x="160" y="145" font-size="11" text-anchor="middle" fill="#8c8273">Enter 제출 (예: "I am gonna read")</text>

  <rect x="40" y="185" width="240" height="55" rx="6" fill="#f4efe6" stroke="#c4bcaf" stroke-width="1.2"/>
  <text x="160" y="208" font-size="13" font-weight="600" text-anchor="middle" fill="#2b2824">등록 정답 · AI 결과 재사용</text>
  <text x="160" y="226" font-size="11" text-anchor="middle" fill="#d9532f">그 외 입력만 AI 평가 요청</text>

  <rect x="40" y="270" width="240" height="55" rx="6" fill="#fff4f0" stroke="#f0b6a6" stroke-width="1.5"/>
  <text x="160" y="293" font-size="13" font-weight="bold" text-anchor="middle" fill="#d9532f">피드백 표시 &amp; 하이라이트</text>
  <text x="160" y="311" font-size="11" text-anchor="middle" fill="#7a7267">AI 결과 도착 시 오류 한 항목만 안내</text>

  <line x1="160" y1="155" x2="160" y2="185" stroke="#8c8273" stroke-width="1.5" marker-end="url(#arrow)" />

  <!-- 연결 화살표: 요청 -->
  <path d="M 280 212 L 350 212" stroke="#d9532f" stroke-width="2" marker-end="url(#arrow-orange)" />
  <text x="315" y="202" font-size="11" font-weight="bold" fill="#d9532f" text-anchor="middle">fetch</text>
  <text x="315" y="228" font-size="10" fill="#7a7267" text-anchor="middle">HTTPS</text>

  <!-- 영역 2: Vercel 평가 서버 -->
  <rect x="350" y="30" width="490" height="320" rx="10" fill="#f7f6f2" stroke="#c8c2b7" stroke-width="1.5" />
  <text x="365" y="60" font-size="15" font-weight="bold" fill="#2b2824">2. Vercel 평가 서버 (writing-server)</text>
  <text x="365" y="80" font-size="12" fill="#7a7267">별도 저장소 · API 키는 서버 환경변수</text>

  <!-- 백엔드 박스들 -->
  <rect x="370" y="105" width="210" height="60" rx="6" fill="#ffffff" stroke="#b0a89b" stroke-width="1.2"/>
  <text x="475" y="130" font-size="13" font-weight="600" text-anchor="middle" fill="#2b2824">API 서버 (api/index.py)</text>
  <text x="475" y="148" font-size="11" text-anchor="middle" fill="#7a7267">POST /api/assess</text>

  <rect x="370" y="195" width="210" height="70" rx="6" fill="#ffffff" stroke="#b0a89b" stroke-width="1.2"/>
  <text x="475" y="220" font-size="13" font-weight="600" text-anchor="middle" fill="#2b2824">평가 엔진 (evaluator.py)</text>
  <text x="475" y="238" font-size="11" text-anchor="middle" fill="#d9532f">낮은 추론 · 구조화 JSON 출력</text>
  <text x="475" y="253" font-size="10" text-anchor="middle" fill="#7a7267">불필요 ➔ 틀림 ➔ 누락 우선순위</text>

  <!-- Groq API 박스 -->
  <rect x="630" y="195" width="190" height="70" rx="6" fill="#eef5fc" stroke="#a6c8e8" stroke-width="1.5"/>
  <text x="725" y="225" font-size="13" font-weight="bold" text-anchor="middle" fill="#185abc">Groq · GPT-OSS 120B</text>
  <text x="725" y="245" font-size="11" text-anchor="middle" fill="#5f6368">정답 비공개 · AI 판정</text>

  <!-- 출력 검증 박스 -->
  <rect x="370" y="285" width="210" height="45" rx="6" fill="#edf7ed" stroke="#b6ddb6" stroke-width="1.2"/>
  <text x="475" y="306" font-size="12" font-weight="600" text-anchor="middle" fill="#2e7d32">출력 형식 · 힌트 검증</text>
  <text x="475" y="321" font-size="10" text-anchor="middle" fill="#558b2f">형식 실패에 한해 AI 재평가 1회</text>

  <!-- 내부 화살표 -->
  <line x1="475" y1="165" x2="475" y2="195" stroke="#8c8273" stroke-width="1.5" marker-end="url(#arrow)" />
  <line x1="580" y1="230" x2="630" y2="230" stroke="#185abc" stroke-width="1.5" marker-end="url(#arrow)" />
  <line x1="475" y1="265" x2="475" y2="285" stroke="#2e7d32" stroke-width="1.5" marker-end="url(#arrow)" />

  <!-- 연결 화살표: 응답 -->
  <path d="M 370 240 C 330 250, 310 275, 280 285" fill="none" stroke="#d9532f" stroke-width="2" stroke-dasharray="4,4" marker-end="url(#arrow-orange)" />
  <text x="325" y="260" font-size="11" font-weight="bold" fill="#d9532f" text-anchor="middle">JSON 반환</text>
</svg>

---

### 동작 요약

1. **사용자 제출**: 소개 데모 또는 [영작 페이지](writing.html)에서 Enter로 제출합니다. 문장마다 60초가 주어집니다.
2. **즉시 처리**: 등록된 정답은 바로 통과합니다. 같은 단계·같은 입력에 검증된 AI 결과가 있으면 현재 페이지 메모리에서 재사용합니다. 수동 오류 판정 규칙은 사용하지 않습니다.
3. **AI 평가**: 나머지 입력은 `https://writing-server.vercel.app/api/assess`로 전달합니다. Vercel의 `api/index.py`와 `evaluator.py`가 Groq의 `openai/gpt-oss-120b`를 낮은 추론 설정으로 호출합니다. API 키는 서버 환경변수로만 관리합니다.
4. **피드백 표시**: 불필요한 표현 → 틀린 표현·철자 → 빠진 표현 순서로 가장 중요한 한 항목을 안내합니다. 오류 입력 구간과 누락된 한글 뜻을 표시하며, 정답·교정문은 공개하지 않습니다. 응답 대기 중 안내는 표시하지 않습니다.
5. **실패·중복 처리**: 출력 형식이 잘못된 경우에만 중간 추론으로 한 차례 AI 재평가합니다. 평가 중 같은 입력의 중복 제출은 무시합니다. 최종 실패 시 재시도를 안내하며 편집·단계 이동·시간 종료 후의 오래된 응답은 표시하지 않습니다.

### 파일과 배포

| 역할 | 파일 / 서비스 |
|---|---|
| 소개·데모 | `index.html` |
| 영작 전용 화면 | `writing.html` |
| 공통 영작 로직·디자인 | `writing.js`, `site.css` |
| 정적 웹·문서 배포 | GitHub Pages, `.github/workflows/pages.yml` |
| 공개 평가 API | Vercel의 `writing-server` 프로젝트 |
| AI 판정 | Groq `openai/gpt-oss-120b` |
| 기능 안내 챗봇 | `ask-once`의 FAQ → `chatbot.js`, 모델 호출 없음 |

로컬 개발용 `main.py`·SQLite 이력 코드는 별도로 남아 있으며, 공개 Vercel API는 SQLite 이력을 저장하지 않습니다.
