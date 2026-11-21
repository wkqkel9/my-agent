// app/js/writing.js - 실전 영작 스피드 훈련 & AI 피드백 엔진
(() => {
  // 1. 상태 변수 & AI 흐름 (Gemini가 매 문제를 실시간 생성 — 로컬 드릴 배열 없음)

  // 2. 상태 변수
  let currentDrill = null;
  let currentLevel = localStorage.getItem('drill_level') || 'easy';
  let dailyGoal = parseInt(localStorage.getItem('daily_goal') || '50', 10);
  let timerLimit = parseInt(localStorage.getItem('timer_limit') || '45', 10);
  let sessionSolved = 0;
  let sessionCorrect = 0;
  let sessionTimeTotal = 0;
  let currentStreak = 0;
  let wrongNotes = JSON.parse(localStorage.getItem('wrong_notes') || '[]');
  let favoriteNotes = JSON.parse(localStorage.getItem('favorite_notes') || '[]');
  let guestPracticeCount = parseInt(localStorage.getItem('guest_practice_count') || '0', 10);
  let isGuestContinue = false;

  let timerInterval = null;
  let remainingSeconds = timerLimit;
  let timerRunning = false;
  let isWaitingNext = false;
  let startTime = 0;

  let learnedExpressions = [];

  // DOM Elements
  const categoryBadge = document.querySelector('#categoryBadge');
  const koreanPrompt = document.querySelector('#koreanPrompt');
  const clock = document.querySelector('#clock');
  const clockSeconds = document.querySelector('#clockSeconds');
  const expandInput = document.querySelector('#expandInput');
  const expandForm = document.querySelector('#expandForm');
  const expandStatus = document.querySelector('#expandStatus');
  const feedbackContainer = document.querySelector('#feedbackContainer');
  const feedbackTitle = document.querySelector('#feedbackTitle');
  const resultBadge = document.querySelector('#resultBadge');
  const correctedSentence = document.querySelector('#correctedSentence');
  const feedbackReason = document.querySelector('#feedbackReason');
  const btnToggleFavorite = document.querySelector('#btnToggleFavorite');
  const btnNextDrill = document.querySelector('#btnNextDrill');

  const progressText = document.querySelector('#progressText');
  const progressPercent = document.querySelector('#progressPercent');
  const drillProgressBar = document.querySelector('#drillProgressBar');
  const streakBadge = document.querySelector('#streakBadge');
  const nudgeBanner = document.querySelector('#nudgeBanner');
  const nudgeText = document.querySelector('#nudgeText');
  const wrongCountBadge = document.querySelector('#wrongCountBadge');

  const btnOpenWrong = document.querySelector('#btnOpenWrong');
  const btnFinishSession = document.querySelector('#btnFinishSession');
  const summaryModal = document.querySelector('#summaryModal');
  const btnCloseSummary = document.querySelector('#btnCloseSummary');
  const btnSummaryContinue = document.querySelector('#btnSummaryContinue');
  const wrongModal = document.querySelector('#wrongModal');
  const btnCloseWrong = document.querySelector('#btnCloseWrong');
  const btnClearWrong = document.querySelector('#btnClearWrong');
  const btnRetryWrong = document.querySelector('#btnRetryWrong');

  const practiceGate = document.querySelector('#practiceGate');
  const practiceContent = document.querySelector('#practiceContent');
  const continueTrialBtn = document.querySelector('#continueTrialBtn');

  // 3. 초기화 및 이벤트 리스너 설정
  async function init() {
    if (practiceGate) practiceGate.hidden = true;
    if (practiceContent) practiceContent.hidden = false;
    updateBadges();
    setupControls();
    await fetchAndRenderQuestion();
  }

  // AI로 문제 받아오기 (Gemini → Groq 순, 실패 시 에러 표시)
  async function fetchAndRenderQuestion(reviewExpression = null) {
    koreanPrompt.textContent = '⏳ AI가 새 문제를 생성하는 중...';
    categoryBadge.textContent = '...';
    feedbackContainer.hidden = true;
    expandInput.value = '';
    expandStatus.textContent = '입력창을 눌러 시작 · Enter로 즉시 채점';
    isWaitingNext = false;
    stopTimer();
    clockSeconds.textContent = String(timerLimit);
    clock.dataset.phase = 'normal';

    try {
      const res = await fetch('/api/generate_question', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          level: currentLevel,
          review_expression: reviewExpression || null
        })
      });
      if (res.ok) {
        const q = await res.json();
        if (q.korean) {
          currentDrill = q;
          applyDrillToUI(currentDrill);
          updateProgress();
          return;
        }
      }
      const err = await res.json().catch(() => ({}));
      koreanPrompt.textContent = `❌ 문제 생성 실패: ${err.error || '서버 오류'}`;
      expandStatus.textContent = '.env에 GROQ_API_KEY 또는 GEMINI_API_KEY를 설정해 주세요.';
    } catch (e) {
      koreanPrompt.innerHTML = '❌ 연결이 일시적으로 지연되었습니다. <a href="#" id="btnRetryQuestion" style="color:var(--orange); text-decoration:underline; font-size:15px; margin-left:6px;">다시 시도 🔄</a>';
      expandStatus.textContent = '클릭하여 다시 문제를 받아오세요.';
      document.querySelector('#btnRetryQuestion')?.addEventListener('click', (ev) => {
        ev.preventDefault();
        fetchAndRenderQuestion();
      });
    }
  }

  function applyDrillToUI(drill) {
    categoryBadge.textContent = drill.category || '실전 영작 💼';
    koreanPrompt.textContent = drill.korean || '';
    expandInput.value = '';
    feedbackContainer.hidden = true;
    expandStatus.textContent = '입력창을 눌러 시작 · Enter로 즉시 채점';
    isWaitingNext = false;
    const isFav = favoriteNotes.some(f => f.korean === drill.korean);
    btnToggleFavorite.classList.toggle('active', isFav);
    btnToggleFavorite.textContent = isFav ? '⭐ 즐겨찾기 완료' : '⭐ 즐겨찾기에 보관';
    stopTimer();
    clockSeconds.textContent = String(timerLimit);
    clock.dataset.phase = 'normal';
  }

  function setupControls() {
    // 난이도 버튼들
    document.querySelectorAll('#levelGroup button').forEach(btn => {
      const lvl = btn.dataset.level;
      if (lvl === currentLevel) btn.classList.add('active');
      else btn.classList.remove('active');
      btn.addEventListener('click', () => {
        document.querySelectorAll('#levelGroup button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentLevel = lvl;
        localStorage.setItem('drill_level', lvl);
        fetchAndRenderQuestion();
      });
    });

    // 목표량 버튼들
    document.querySelectorAll('#goalGroup button').forEach(btn => {
      const g = parseInt(btn.dataset.goal, 10);
      if (g === dailyGoal) btn.classList.add('active');
      else btn.classList.remove('active');
      btn.addEventListener('click', () => {
        document.querySelectorAll('#goalGroup button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        dailyGoal = g;
        localStorage.setItem('daily_goal', String(g));
        updateProgress();
      });
    });

    // 타이머 버튼들
    document.querySelectorAll('#timerGroup button').forEach(btn => {
      const t = parseInt(btn.dataset.time, 10);
      if (t === timerLimit) btn.classList.add('active');
      else btn.classList.remove('active');
      btn.addEventListener('click', () => {
        document.querySelectorAll('#timerGroup button').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        timerLimit = t;
        localStorage.setItem('timer_limit', String(t));
        if (!timerRunning) {
          remainingSeconds = t;
          clockSeconds.textContent = String(t);
        }
      });
    });

    // 입력창 포커스 시 타이머 가동
    expandInput.addEventListener('focus', () => {
      if (!timerRunning && !isWaitingNext) startTimer();
    });

    // 폼 제출 (Enter)
    expandForm.addEventListener('submit', e => {
      e.preventDefault();
      handleSubmit();
    });

    expandInput.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    });

    // 다음 문제 버튼
    btnNextDrill.addEventListener('click', () => nextDrill());

    // 즐겨찾기 토글
    btnToggleFavorite.addEventListener('click', toggleFavorite);

    // 오답노트 & 요약 모달 트리거
    btnOpenWrong.addEventListener('click', openWrongModal);
    btnCloseWrong.addEventListener('click', () => wrongModal.hidden = true);
    btnClearWrong.addEventListener('click', clearWrongNotes);
    btnRetryWrong.addEventListener('click', retryWrongNotes);

    btnFinishSession.addEventListener('click', openSummaryModal);
    btnCloseSummary.addEventListener('click', () => summaryModal.hidden = true);
    btnSummaryContinue.addEventListener('click', () => {
      summaryModal.hidden = true;
      nextDrill();
    });

    if (continueTrialBtn) {
      continueTrialBtn.addEventListener('click', () => {
        isGuestContinue = true;
        if (practiceGate) practiceGate.hidden = true;
        if (practiceContent) practiceContent.hidden = false;
        expandInput.focus();
      });
    }
  }

  // 4. 타이머 관리
  function startTimer() {
    stopTimer();
    remainingSeconds = timerLimit;
    timerRunning = true;
    startTime = Date.now();
    clock.dataset.running = 'true';
    clock.dataset.phase = 'normal';
    clockSeconds.textContent = String(remainingSeconds);

    timerInterval = setInterval(() => {
      remainingSeconds--;
      clockSeconds.textContent = String(Math.max(0, remainingSeconds));
      if (remainingSeconds <= 10) clock.dataset.phase = 'urgent';
      else if (remainingSeconds <= 20) clock.dataset.phase = 'warning';
      else clock.dataset.phase = 'normal';

      if (remainingSeconds <= 0) {
        stopTimer();
        expandStatus.textContent = '⏱️ 시간이 종료되었어요! 작성한 답안을 Enter를 눌러 확인해 보세요.';
      }
    }, 1000);
  }

  function stopTimer() {
    clearInterval(timerInterval);
    timerRunning = false;
    clock.dataset.running = 'false';
  }

  // 5. 문제 렌더링
  // 6. 답안 제출 및 평가 (Local & Server 하이브리드)
  async function handleSubmit() {
    if (isWaitingNext) {
      nextDrill();
      return;
    }

    const text = expandInput.value.trim();
    if (!text) {
      expandStatus.textContent = '문장을 먼저 입력해 주세요!';
      expandInput.focus();
      return;
    }

    stopTimer();
    const timeSpent = Math.max(1, Math.round((Date.now() - startTime) / 1000));
    expandStatus.textContent = '⚡ 실시간 3대 기준으로 분석 중...';

    // 평가 요청 (AI 서버 우선 ➔ 최소 폴백)
    let evalResult = null;
    try {
      const res = await fetch('/api/assess', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          korean: currentDrill.korean,
          target_expression: currentDrill.target_expression,
          reference_answer: currentDrill.reference_answer || '',
          category: currentDrill.category || '',
          user_text: text,
          time_spent: timeSpent
        })
      });
      if (res.ok) {
        evalResult = await res.json();
      }
    } catch (e) {
      console.log('Server assess offline, falling back to local heuristic evaluator');
    }

    if (!evalResult) {
      evalResult = localEvaluate(text, currentDrill);
    }

    renderFeedback(evalResult, text, timeSpent);
  }

  // 로컬 즉각 스마트 평가 엔진 (오프라인/GitHub Pages 지원)
  function localEvaluate(userText, drill) {
    const norm = userText.toLowerCase();
    const missedNuances = [];

    if (drill.nuance_checks) {
      for (const [kw, explanation] of Object.entries(drill.nuance_checks)) {
        if (!norm.includes(kw.toLowerCase())) {
          missedNuances.push(explanation);
        }
      }
    }

    let matchedChunks = 0;
    const groups = drill.acceptable_chunks || [];
    for (const group of groups) {
      if (group.some(chunk => norm.includes(chunk.toLowerCase()))) {
        matchedChunks++;
      }
    }

    const ratio = groups.length ? matchedChunks / groups.length : 0;
    let isCorrect = false;
    let reason = '';

    if (ratio >= 0.75 && missedNuances.length === 0) {
      isCorrect = true;
      reason = '완벽합니다! 실전 인터뷰에서 바로 쓸 수 있는 훌륭하고 자연스러운 문장이에요.';
    } else if (missedNuances.length > 0) {
      isCorrect = false;
      reason = missedNuances.join(' ');
    } else {
      isCorrect = false;
      reason = `핵심 표현이 다소 아쉽습니다. '${drill.hint || drill.target_expression}'을 참고해 보세요.`;
    }

    return {
      is_correct: isCorrect,
      corrected_sentence: drill.reference_answer,
      short_reason: reason,
      missed_nuance: missedNuances[0] || null,
      paraphrasing: drill.paraphrasing || []
    };
  }

  // 피드백 카드 렌더링
  function renderFeedback(res, userText, timeSpent) {
    feedbackContainer.hidden = false;
    isWaitingNext = true;

    sessionSolved++;
    sessionTimeTotal += timeSpent;
    guestPracticeCount++;
    localStorage.setItem('guest_practice_count', String(guestPracticeCount));

    if (res.is_correct) {
      sessionCorrect++;
      currentStreak++;
      feedbackTitle.textContent = '✅ 정답 & 훌륭한 표현!';
      feedbackTitle.style.color = '#27ae60';
      resultBadge.textContent = 'EXCELLENT';
      resultBadge.style.color = '#27ae60';
    } else {
      currentStreak = 0;
      feedbackTitle.textContent = '💡 교정 피드백 & 뉘앙스 주의';
      feedbackTitle.style.color = '#e67e22';
      resultBadge.textContent = res.missed_nuance ? 'NUANCE MISSED' : 'CHECK NEEDED';
      resultBadge.style.color = '#c0392b';

      // 오답 노트에 추가
      addWrongNote({
        id: currentDrill.id,
        category: currentDrill.category,
        korean: currentDrill.korean,
        userText: userText,
        corrected: res.corrected_sentence,
        reason: res.short_reason
      });
    }

    correctedSentence.textContent = res.corrected_sentence || currentDrill.reference_answer;
    feedbackReason.textContent = res.short_reason;

    if (currentDrill.target_expression && !learnedExpressions.includes(currentDrill.target_expression)) {
      learnedExpressions.push(currentDrill.target_expression);
    }

    updateProgress();
    expandStatus.textContent = 'Enter를 누르면 다음 문제로 즉시 넘어갑니다 ➔';
    btnNextDrill.focus();

    // 게스트 5회 무료 체험 안내
    const token = localStorage.getItem('jwt');
    if (!token && guestPracticeCount >= 5 && !isGuestContinue) {
      practiceGate.hidden = false;
    }
  }

  // 7. 다음 문제로 이동 (AI에서 새 문제 받아옴)
  function nextDrill() {
    fetchAndRenderQuestion().then(() => expandInput.focus());
  }

  // 8. 동기부여 넛지 및 프로그레스 갱신
  function updateProgress() {
    progressText.textContent = `${sessionSolved} / ${dailyGoal}`;
    const pct = Math.min(100, Math.round((sessionSolved / dailyGoal) * 100));
    progressPercent.textContent = `${pct}%`;
    drillProgressBar.style.width = `${pct}%`;
    streakBadge.textContent = `🔥 오늘 연속 ${currentStreak}개 성공!`;

    // 유도 넛지 메시지
    let msg = '첫 번째 문장을 영작하고 오늘의 훈련을 시작하세요! 🚀';
    if (sessionSolved === 0) {
      msg = '첫 문장을 영작하고 뇌의 영어 근육을 깨워보세요! 🚀';
    } else if (sessionSolved < 5) {
      msg = '좋은 출발이에요! 타임어택 속도를 조금씩 올려볼까요? ⚡';
    } else if (sessionSolved === 5) {
      msg = '5개 돌파! 핵심 표현이 입에 붙기 시작했어요 🔥';
    } else if (sessionSolved < dailyGoal / 2) {
      msg = `꾸준히 잘 달리고 있어요! 오늘 목표까지 ${dailyGoal - sessionSolved}개 남았어요 💪`;
    } else if (sessionSolved === Math.floor(dailyGoal / 2)) {
      msg = '절반 돌파! 이미 절반이나 해냈어요, 계속 가봅시다! 🏃';
    } else if (sessionSolved < dailyGoal) {
      const left = dailyGoal - sessionSolved;
      msg = left <= 5 ? `목표까지 딱 ${left}개! 오늘 완주가 코앞이에요 🎯` : `거의 다 왔어요! ${left}개만 더 채워볼까요? ✨`;
    } else if (sessionSolved === dailyGoal) {
      msg = '🎉 축하합니다! 오늘 목표 달성 완료! 보너스로 딱 1문제 더 도전해볼까요? ⭐';
    } else {
      msg = `대단해요! 목표를 초과 달성 중이에요 (+${sessionSolved - dailyGoal}개) 👑`;
    }
    nudgeText.textContent = msg;
    updateBadges();
  }

  function updateBadges() {
    wrongCountBadge.textContent = String(wrongNotes.length);
  }

  // 9. 즐겨찾기 토글
  async function toggleFavorite() {
    if (!currentDrill) return;
    const idx = favoriteNotes.findIndex(f => f.korean === currentDrill.korean);
    let isFav = false;
    if (idx >= 0) {
      favoriteNotes.splice(idx, 1);
      btnToggleFavorite.classList.remove('active');
      btnToggleFavorite.textContent = '⭐ 즐겨찾기에 보관';
      isFav = false;
    } else {
      favoriteNotes.push({
        id: currentDrill.id,
        category: currentDrill.category,
        korean: currentDrill.korean,
        expression: currentDrill.target_expression,
        reference: currentDrill.reference_answer
      });
      btnToggleFavorite.classList.add('active');
      btnToggleFavorite.textContent = '⭐ 즐겨찾기 완료';
      isFav = true;
    }
    localStorage.setItem('favorite_notes', JSON.stringify(favoriteNotes));
  }

  // 10. 오답 노트 관리
  function addWrongNote(note) {
    if (!wrongNotes.some(w => w.korean === note.korean)) {
      wrongNotes.unshift(note);
      if (wrongNotes.length > 50) wrongNotes.pop();
      localStorage.setItem('wrong_notes', JSON.stringify(wrongNotes));
      updateBadges();
    }
  }

  function openWrongModal() {
    const container = document.querySelector('#wrongListContainer');
    container.innerHTML = '';
    if (wrongNotes.length === 0) {
      container.innerHTML = '<div style="color:var(--muted); text-align:center; padding:24px;">아직 오답 기록이 없어요! 아주 잘하고 계십니다 👏</div>';
    } else {
      wrongNotes.forEach((w, idx) => {
        const item = document.createElement('div');
        item.className = 'summary-item';
        item.style.borderLeftColor = '#e74c3c';
        item.innerHTML = `
          <div style="font-size:11px; color:#e74c3c; font-weight:700;">${escapeHtml(w.category || '')}</div>
          <div style="font-weight:700; color:var(--ink); margin:2px 0;">${escapeHtml(w.korean)}</div>
          <div style="font-size:12px; color:var(--muted); text-decoration:line-through;">내 답안: ${escapeHtml(w.userText)}</div>
          <div style="font-size:13px; color:#27ae60; font-weight:600;">모범: ${escapeHtml(w.corrected)}</div>
          <div style="font-size:11px; color:#666; margin-top:2px;">이유: ${escapeHtml(w.reason)}</div>
        `;
        container.appendChild(item);
      });
    }
    wrongModal.hidden = false;
  }

  function clearWrongNotes() {
    if (confirm('오답 노트를 초기화하시겠습니까?')) {
      wrongNotes = [];
      localStorage.removeItem('wrong_notes');
      updateBadges();
      wrongModal.hidden = true;
    }
  }

  function retryWrongNotes() {
    if (wrongNotes.length === 0) {
      alert('다시 풀 오답이 없습니다.');
      return;
    }
    wrongModal.hidden = true;
    const targetWrong = wrongNotes[0];
    currentDrill = {
      category: `[오답 복습] ${targetWrong.category || ''}`,
      korean: targetWrong.korean,
      target_expression: '오답 복습 표현',
      reference_answer: targetWrong.corrected,
      hint: targetWrong.reason
    };
    applyDrillToUI(currentDrill);
    expandInput.focus();
  }

  // 11. 세션 종료 요약 모달
  function openSummaryModal() {
    document.querySelector('#sumTotalSolved').textContent = `${sessionSolved}개`;
    const acc = sessionSolved ? Math.round((sessionCorrect / sessionSolved) * 100) : 0;
    document.querySelector('#sumAccuracy').textContent = `${acc}%`;
    const avg = sessionSolved ? Math.round(sessionTimeTotal / sessionSolved) : 0;
    document.querySelector('#sumAvgSpeed').textContent = `${avg}초`;

    const keyList = document.querySelector('#sumKeyExpressions');
    keyList.innerHTML = '';
    const uniqueExp = [...new Set(learnedExpressions)].filter(Boolean);
    if (uniqueExp.length === 0) {
      keyList.innerHTML = '<div style="color:var(--muted); font-size:12px;">아직 완료한 문장이 없습니다.</div>';
    } else {
      uniqueExp.slice(0, 5).forEach(exp => {
        const item = document.createElement('div');
        item.className = 'summary-item';
        item.textContent = `✓ ${exp}`;
        keyList.appendChild(item);
      });
    }

    summaryModal.hidden = false;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // 실행
  window.addEventListener('DOMContentLoaded', init);
})();
