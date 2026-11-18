---
layout: default
title: 서비스 동작 구조
---

# 서비스 동작 구조

브라우저 프론트엔드와 로컬 AI 백엔드의 동작 구조를 한눈에 보여주는 다이어그램입니다.

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
  <text x="35" y="80" font-size="12" fill="#7a7267">my-agent / index.html (공개 배포)</text>

  <!-- 프론트 박스들 -->
  <rect x="40" y="105" width="240" height="50" rx="6" fill="#ffffff" stroke="#b0a89b" stroke-width="1.2"/>
  <text x="160" y="128" font-size="13" font-weight="600" text-anchor="middle" fill="#2b2824">사용자 문장 입력</text>
  <text x="160" y="145" font-size="11" text-anchor="middle" fill="#8c8273">Enter 제출 (예: "I am gonna read")</text>

  <rect x="40" y="185" width="240" height="55" rx="6" fill="#f4efe6" stroke="#c4bcaf" stroke-width="1.2"/>
  <text x="160" y="208" font-size="13" font-weight="600" text-anchor="middle" fill="#2b2824">1차: 브라우저 정규식 판정</text>
  <text x="160" y="226" font-size="11" text-anchor="middle" fill="#d9532f">즉시(0초) 기본 피드백 표시</text>

  <rect x="40" y="270" width="240" height="55" rx="6" fill="#fff4f0" stroke="#f0b6a6" stroke-width="1.5"/>
  <text x="160" y="293" font-size="13" font-weight="bold" text-anchor="middle" fill="#d9532f">피드백 갱신 & 하이라이트</text>
  <text x="160" y="311" font-size="11" text-anchor="middle" fill="#7a7267">AI 분석 결과로 시제/어휘 피드백 갱신</text>

  <line x1="160" y1="155" x2="160" y2="185" stroke="#8c8273" stroke-width="1.5" marker-end="url(#arrow)" />

  <!-- 연결 화살표: 요청 -->
  <path d="M 280 212 L 350 212" stroke="#d9532f" stroke-width="2" marker-end="url(#arrow-orange)" />
  <text x="315" y="202" font-size="11" font-weight="bold" fill="#d9532f" text-anchor="middle">fetch</text>
  <text x="315" y="228" font-size="10" fill="#7a7267" text-anchor="middle">:8000</text>

  <!-- 영역 2: 로컬 백엔드 -->
  <rect x="350" y="30" width="490" height="320" rx="10" fill="#f7f6f2" stroke="#c8c2b7" stroke-width="1.5" />
  <text x="365" y="60" font-size="15" font-weight="bold" fill="#2b2824">2. 내 로컬 PC (writing-server)</text>
  <text x="365" y="80" font-size="12" fill="#7a7267">비공개 독립 저장소 · API 키 보관 (.env)</text>

  <!-- 백엔드 박스들 -->
  <rect x="370" y="105" width="210" height="60" rx="6" fill="#ffffff" stroke="#b0a89b" stroke-width="1.2"/>
  <text x="475" y="130" font-size="13" font-weight="600" text-anchor="middle" fill="#2b2824">API 서버 (main.py)</text>
  <text x="475" y="148" font-size="11" text-anchor="middle" fill="#7a7267">POST /api/assess</text>

  <rect x="370" y="195" width="210" height="70" rx="6" fill="#ffffff" stroke="#b0a89b" stroke-width="1.2"/>
  <text x="475" y="220" font-size="13" font-weight="600" text-anchor="middle" fill="#2b2824">평가 엔진 (evaluator.py)</text>
  <text x="475" y="238" font-size="11" text-anchor="middle" fill="#d9532f">Lesson 2 지시문 + 5 JSON 출력</text>
  <text x="475" y="253" font-size="10" text-anchor="middle" fill="#7a7267">불필요 ➔ 틀림 ➔ 누락 우선순위</text>

  <!-- Gemini AI 박스 -->
  <rect x="630" y="195" width="190" height="70" rx="6" fill="#eef5fc" stroke="#a6c8e8" stroke-width="1.5"/>
  <text x="725" y="225" font-size="13" font-weight="bold" text-anchor="middle" fill="#185abc">Gemini 3.8 Flash</text>
  <text x="725" y="245" font-size="11" text-anchor="middle" fill="#5f6368">정답 비공개 & 정밀 판정</text>

  <!-- SQLite DB 박스 -->
  <rect x="370" y="285" width="210" height="45" rx="6" fill="#edf7ed" stroke="#b6ddb6" stroke-width="1.2"/>
  <text x="475" y="306" font-size="12" font-weight="600" text-anchor="middle" fill="#2e7d32">SQLite DB (agent.db)</text>
  <text x="475" y="321" font-size="10" text-anchor="middle" fill="#558b2f">Lesson 6 세이브 / 오답 기록</text>

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
1. **사용자 제출**: Enter를 누르면 **1차로 브라우저 정규식(0ms)**이 먼저 피드백을 즉시 띄웁니다.
2. **AI 정밀 분석**: 동시에 로컬 PC 백엔드(`http://127.0.0.1:8000`)로 요청이 전달되어 **Gemini 3.8 Flash**가 시제 및 어휘의 차이를 분석합니다.
3. **피드백 갱신**: 분석된 구체적 피드백과 오류 단어 구간(`range`)으로 화면을 매끄럽게 업데이트합니다.
4. **무중단 폴백**: 로컬 서버가 꺼져 있어도 에러 없이 기존 브라우저 피드백이 그대로 작동합니다.
