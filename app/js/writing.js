// app/js/writing.js - 실전 영작 스피드 훈련 & AI 피드백 엔진
(() => {
  // 2. 상태 변수
  let currentDrill = null;
  const timerLimit = 60;
  let sessionSolved = 0;
  let sessionCorrect = 0;
  let sessionTimeTotal = 0;
  let currentStreak = 0;
  let wrongNotes = JSON.parse(localStorage.getItem('wrong_notes') || '[]');
  let favoriteNotes = JSON.parse(localStorage.getItem('favorite_notes') || '[]');

  let timerInterval = null;
  let remainingSeconds = timerLimit;
  let timerRunning = false;
  let isWaitingNext = false;
  let startTime = 0;

  let learnedExpressions = [];
  let controlsReady = false;
  let practiceBusy = false;
  let settings = { mode: 'normal', level: 'auto', topic: 'auto' };
  let reviewQueue = [];
  let reviewIndex = 0;
  const levels = ['A2', 'B1', 'B1+', 'B2', 'B2+'];

  function renderSettings() {
    const label = document.querySelector('#trainingSettings');
    if (label) label.textContent = settings.mode === 'wrong' ? '오답 복습 · 저장된 원래 문제 · 다음 문제도 오답에서 나와요' : `일반 연습 · 난이도 ${settings.level === 'auto' ? '자동' : settings.level} · 주제 ${settings.topic === 'auto' ? '자동' : settings.topic}`;
  }

  function showReviewQuestion() {
    const note = reviewQueue[reviewIndex++ % reviewQueue.length];
    currentDrill = { ...note, training_mode: 'review' };
    applyDrillToUI(currentDrill);
    expandStatus.textContent = `오답 복습 ${((reviewIndex - 1) % reviewQueue.length) + 1}/${reviewQueue.length} · 원래 문제로 다시 풀어요`;
    return true;
  }

  window.applyTrainingCommand = async (action) => {
    if (practiceBusy) return '문제 생성이나 채점이 끝난 뒤 다시 요청해 주세요.';
    if (action.finish_session) {
      if (location.hash.startsWith('#learning-')) location.hash = '';
      openSummaryModal();
      return '오늘 훈련 결과를 열었어요.';
    }
    if (trialRequiresLogin()) {
      showPracticeGate();
      return '체험이 끝났어요. 로그인한 뒤 계속 연습해 주세요.';
    }
    if (action.next_question) {
      if (settings.mode === 'wrong' && reviewQueue.length < 2) {
        return '다른 오답 문제가 없어요. 새 문제를 풀려면 “일반 연습 시작해 줘”라고 말해 주세요.';
      }
      if (location.hash.startsWith('#learning-')) location.hash = '';
      const success = await fetchAndRenderQuestion({ replaceCurrent: true });
      if (!success) return '다른 문제를 준비하지 못했어요. 잠시 후 다시 요청해 주세요.';
      practiceContent?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return settings.mode === 'wrong' ? '다음 오답 문제로 바꿨어요.' : '다른 문제로 바꿨어요.';
    }
    if (settings.mode === 'wrong' && !action.mode && (action.level || action.topic)) {
      return '오답 복습은 저장된 원래 문제로 진행해요. “일반 연습 시작해 줘”로 돌아온 뒤 난이도와 주제를 바꿔 주세요.';
    }
    const next = { ...settings, ...action };
    if (next.mode === 'wrong' && (action.level || action.topic)) {
      return '오답 복습은 원래 문제로 진행해요. “오답노트로 연습해 줘” 또는 “일반 연습 시작해 줘”로 나눠서 요청해 주세요.';
    }
    if (['easier', 'harder'].includes(next.level)) {
      const base = levels.indexOf(settings.level === 'auto' ? (currentDrill?.cefr_level || 'B1') : settings.level);
      next.level = levels[Math.max(0, Math.min(levels.length - 1, base + (next.level === 'easier' ? -1 : 1)))];
    }
    if (next.mode === 'wrong') {
      practiceBusy = true;
      try {
        let notes;
        if (localStorage.getItem('jwt')) {
          const response = await window.apiFetch('/api/drill_history');
          const payload = await response.json();
          if (!response.ok) throw new Error(payload.error || '오답 기록을 불러오지 못했어요.');
          const seen = new Set();
          notes = (payload.history || []).filter(note => {
            // Only the latest attempt for each question determines whether it is wrong.
            if (seen.has(note.korean)) return false;
            seen.add(note.korean);
            return note.outcome ? note.outcome !== 'correct' : ![true, 1, 'true'].includes(note.is_correct);
          });
        } else {
          notes = JSON.parse(localStorage.getItem('wrong_notes') || '[]');
        }
        const queue = notes.filter(n => n.korean && (n.corrected_sentence || n.corrected)).map(n => ({
          korean: n.korean, category: n.category || '오답 복습',
          reference_answer: n.corrected_sentence || n.corrected,
          target_expression: n.target_expression || '', expression_id: n.expression_id || '',
          cefr_level: n.cefr_level || 'B1', question_type: n.question_type || '',
        }));
        if (!queue.length) return '다시 풀 오답이 없어요. 먼저 영작을 연습해 주세요. 현재 문제는 유지할게요.';
        reviewQueue = queue;
        reviewIndex = 0;
      } catch (error) {
        return error.message || '오답 기록을 불러오지 못했어요. 현재 문제는 유지할게요.';
      } finally { practiceBusy = false; }
    }
    settings = next;
    renderSettings();
    if (location.hash.startsWith('#learning-')) location.hash = '';
    const success = await fetchAndRenderQuestion();
    document.querySelector('#practiceContent')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    return success
      ? (settings.mode === 'wrong' ? `오답 ${reviewQueue.length}개로 복습을 시작했어요. 다음 문제도 오답에서 나와요. 난이도와 주제는 원래 문제 그대로예요.` : `난이도 ${settings.level === 'auto' ? '자동' : settings.level}, 주제 ${settings.topic === 'auto' ? '자동' : settings.topic}로 문제를 준비했어요.`)
      : '설정은 적용했지만 문제를 준비하지 못했어요. 잠시 후 “새 문제 줘”로 다시 시도해 주세요.';
  };
  const dailyStatsKey = `training_daily_${new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Seoul' })}`;
  let dailyStats = JSON.parse(localStorage.getItem(dailyStatsKey) || '{"solved":0,"correct":0,"timeTotal":0,"expressions":[]}');
  const trialCountKey = 'typing_trial_count';
  let trialCount = parseInt(localStorage.getItem(trialCountKey) || '0', 10);
  const trialLimit = 10;

  // DOM Elements
  const koreanPrompt = document.querySelector('#koreanPrompt');
  const clock = document.querySelector('#clock');
  const clockSeconds = document.querySelector('#clockSeconds');
  const expandInput = document.querySelector('#expandInput');
  const expandForm = document.querySelector('#expandForm');
  const expandStatus = document.querySelector('#expandStatus');
  const feedbackContainer = document.querySelector('#feedbackContainer');
  const feedbackTitle = document.querySelector('#feedbackTitle');
  const correctedSentence = document.querySelector('#correctedSentence');
  const feedbackReason = document.querySelector('#feedbackReason');
  const btnToggleFavorite = document.querySelector('#btnToggleFavorite');
  const btnNextDrill = document.querySelector('#btnNextDrill');

  const progressText = document.querySelector('#progressText');
  const nudgeBanner = document.querySelector('#nudgeBanner');
  const nudgeText = document.querySelector('#nudgeText');

  const practiceGate = document.querySelector('#practiceGate');
  const practiceContent = document.querySelector('#practiceContent');
  const practiceLogin = document.querySelector('#practiceLogin');
  const practiceGateClose = document.querySelector('#practiceGateClose');
  const btnFinishSession = document.querySelector('#btnFinishSession');
  const summaryModal = document.querySelector('#summaryModal');
  const btnCloseSummary = document.querySelector('#btnCloseSummary');
  const btnSummaryContinue = document.querySelector('#btnSummaryContinue');

  // 3. 초기화 및 이벤트 리스너 설정
  async function init() {
    setupControls();
    const token = localStorage.getItem('jwt');
    if (!token) {
      if (practiceGate) practiceGate.hidden = true;
      if (practiceContent) practiceContent.hidden = false;
      updateProgress();
      await fetchAndRenderQuestion();
      return;
    }
    if (practiceGate) practiceGate.hidden = true;
    if (practiceContent) practiceContent.hidden = false;
    updateProgress();
    await fetchAndRenderQuestion();
  }

  // AI로 문제 받아오기 (실패 시 에러 표시)
  async function fetchAndRenderQuestion({ replaceCurrent = false } = {}) {
    if (practiceBusy) return false;
    if (settings.mode === 'wrong' && reviewQueue.length) return showReviewQuestion();
    practiceBusy = true;
    const previousQuestion = replaceCurrent ? currentDrill?.korean : null;
    if (!previousQuestion) {
      currentDrill = null;
      koreanPrompt.textContent = '⏳ AI가 새 문제를 생성하는 중...';
      feedbackContainer.hidden = true;
      expandInput.value = '';
      expandStatus.textContent = '입력창을 눌러 시작 · Enter로 즉시 채점';
      isWaitingNext = false;
      stopTimer();
      clockSeconds.textContent = String(timerLimit);
      clock.dataset.phase = 'normal';
      clock.style.setProperty('--timer-progress', '100');
      clock.setAttribute('aria-label', `남은 시간 ${timerLimit}초`);
    }

    try {
      const token = localStorage.getItem('jwt');
      const res = await fetch('/api/generate_question', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({
          ...(previousQuestion ? { previous_question: previousQuestion } : {}),
          cefr_level: settings.level,
          topic: settings.topic
        })
      });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (previousQuestion) return false;
        koreanPrompt.textContent = `❌ 문제 생성 실패: ${payload.error || '서버 오류'}`;
        expandStatus.textContent = '잠시 후 다시 시도해 주세요.';
        return;
      }
      if (!payload.korean) {
        if (previousQuestion) return false;
        koreanPrompt.textContent = '❌ 생성된 문제 형식이 올바르지 않습니다.';
        expandStatus.textContent = '다시 시도해 주세요.';
        return;
      }

      currentDrill = payload;
      applyDrillToUI(currentDrill);
      updateProgress();
      return true;
    } catch (e) {
      if (previousQuestion) return false;
      koreanPrompt.innerHTML = '❌ 연결이 일시적으로 지연되었습니다. <a href="#" id="btnRetryQuestion" style="color:var(--orange); text-decoration:underline; font-size:15px; margin-left:6px;">다시 시도 🔄</a>';
      expandStatus.textContent = '클릭하여 다시 문제를 받아오세요.';
      document.querySelector('#btnRetryQuestion')?.addEventListener('click', (ev) => {
        ev.preventDefault();
        fetchAndRenderQuestion();
      });
    } finally { practiceBusy = false; }
  }

  function applyDrillToUI(drill) {
    koreanPrompt.textContent = drill.korean || '';
    expandInput.value = '';
    feedbackContainer.hidden = true;
    expandStatus.textContent = '입력창을 눌러 시작 · Enter로 즉시 채점';
    isWaitingNext = false;
    const isFav = favoriteNotes.some(f => f.korean === drill.korean);
    renderFavoriteButton(isFav);
    stopTimer();
    clockSeconds.textContent = String(timerLimit);
    clock.dataset.phase = 'normal';
    clock.style.setProperty('--timer-progress', '100');
    clock.setAttribute('aria-label', `남은 시간 ${timerLimit}초`);
  }

  function setupControls() {
    if (controlsReady) return;
    controlsReady = true;
    if (practiceLogin) {
      practiceLogin.addEventListener('click', () => document.querySelector('#authBtn')?.click());
    }
    practiceGateClose?.addEventListener('click', closePracticeGate);
    practiceGate?.addEventListener('click', e => {
      if (e.target === practiceGate) closePracticeGate();
    });
    // 입력창 포커스 시 타이머 가동
    expandInput.addEventListener('focus', () => {
      if (!practiceBusy && currentDrill && !trialRequiresLogin() && !timerRunning && !isWaitingNext) startTimer();
    });
    expandInput.addEventListener('input', () => {
      if (trialRequiresLogin()) {
        stopTimer();
        showPracticeGate();
      }
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
    btnFinishSession.addEventListener('click', openSummaryModal);
    btnCloseSummary.addEventListener('click', () => summaryModal.hidden = true);
    btnSummaryContinue.addEventListener('click', () => {
      summaryModal.hidden = true;
      nextDrill();
    });

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
    clock.style.setProperty('--timer-progress', '100');
    clock.setAttribute('aria-label', `남은 시간 ${remainingSeconds}초`);

    timerInterval = setInterval(() => {
      remainingSeconds--;
      clockSeconds.textContent = String(Math.max(0, remainingSeconds));
      clock.style.setProperty('--timer-progress', String(Math.max(0, Math.round((remainingSeconds / timerLimit) * 100))));
      clock.setAttribute('aria-label', `남은 시간 ${Math.max(0, remainingSeconds)}초`);
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
    if (practiceBusy || !currentDrill) return;
    if (trialRequiresLogin()) {
      stopTimer();
      showPracticeGate();
      return;
    }

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
    practiceBusy = true;
    const timeSpent = Math.max(1, Math.round((Date.now() - startTime) / 1000));
    expandStatus.textContent = 'AI 분석 중...';

    // 평가 요청 (AI 서버 우선 ➔ 최소 폴백)
    let evalResult = null;
    try {
      const token = localStorage.getItem('jwt');
      const res = await fetch('/api/assess', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({
          korean: currentDrill.korean,
          target_expression: currentDrill.target_expression,
          reference_answer: currentDrill.reference_answer || '',
          category: currentDrill.category || '',
          user_text: text,
          time_spent: timeSpent,
          expression_id: currentDrill.expression_id || '',
          training_mode: currentDrill.training_mode || '',
          question_type: currentDrill.question_type || '',
          cefr_level: currentDrill.cefr_level || 'B1'
        })
      });
      if (res.ok) {
        evalResult = await res.json();
        if (token) window.dispatchEvent(new Event('learninghistorychange'));
      }
    } catch (e) {
      console.log('Server assess offline, falling back to local heuristic evaluator');
    }

    if (!evalResult) {
      evalResult = localEvaluate(text, currentDrill);
    }

    renderFeedback(evalResult, text, timeSpent);
    practiceBusy = false;
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
    dailyStats.solved++;
    dailyStats.timeTotal += timeSpent;

    if (!localStorage.getItem('jwt')) {
      trialCount++;
      localStorage.setItem(trialCountKey, String(trialCount));
      if (trialCount >= trialLimit) {
        stopTimer();
        showPracticeGate();
        expandStatus.textContent = '체험판이 종료됐어요. 계속 이용하려면 로그인해 주세요.';
      }
    }

    const outcome = res.outcome || (res.is_correct ? 'correct' : 'incorrect');
    if (outcome === 'correct') {
      sessionCorrect++;
      dailyStats.correct++;
      currentStreak++;
      feedbackTitle.textContent = '정답';
      feedbackTitle.style.color = '#27ae60';
    } else {
      currentStreak = 0;
      feedbackTitle.textContent = outcome === 'partial' ? '부분 정답' : '오답';
      feedbackTitle.style.color = outcome === 'partial' ? '#a45b10' : '#a93525';

      // 오답 노트에 추가
      addWrongNote({
        id: currentDrill.id,
        category: currentDrill.category,
        korean: currentDrill.korean,
        userText: userText,
        corrected: res.corrected_sentence,
        reason: res.short_reason,
        target_expression: currentDrill.target_expression,
        expression_id: currentDrill.expression_id,
        cefr_level: currentDrill.cefr_level,
        question_type: currentDrill.question_type
      });
    }

    correctedSentence.textContent = res.corrected_sentence || currentDrill.reference_answer;
    renderFeedbackPoints(res.feedback_points, res.short_reason);

    if (currentDrill.target_expression && !learnedExpressions.includes(currentDrill.target_expression)) {
      learnedExpressions.push(currentDrill.target_expression);
    }
    if (currentDrill.target_expression && !dailyStats.expressions.includes(currentDrill.target_expression)) {
      dailyStats.expressions.push(currentDrill.target_expression);
    }
    localStorage.setItem(dailyStatsKey, JSON.stringify(dailyStats));

    updateProgress();
    expandStatus.textContent = 'Enter를 누르면 다음 문제로 즉시 넘어갑니다 ➔';

  }

  // 7. 다음 문제로 이동 (AI에서 새 문제 받아옴)
  function nextDrill() {
    fetchAndRenderQuestion().then(() => expandInput.focus());
  }

  // 8. 동기부여 넛지 및 프로그레스 갱신
  function updateProgress() {
    if (!localStorage.getItem('jwt')) {
      progressText.textContent = `체험 ${trialCount}/${trialLimit}문장`;
    } else {
      progressText.textContent = `오늘 ${dailyStats.solved}문장`;
    }
  }

  function trialRequiresLogin() {
    return !localStorage.getItem('jwt') && trialCount >= trialLimit;
  }

  function showPracticeGate() {
    if (practiceGate) practiceGate.hidden = false;
  }

  function closePracticeGate() {
    if (practiceGate) practiceGate.hidden = true;
    expandInput?.focus();
  }

  function updateBadges() {
    // 오답은 자동 복습 큐에서 관리하며 별도 설정 버튼으로 표시하지 않는다.
  }

  // 9. 즐겨찾기 토글
  async function toggleFavorite() {
    if (!currentDrill) return;
    const idx = favoriteNotes.findIndex(f => f.korean === currentDrill.korean);
    let isFav = false;
    if (idx >= 0) {
      favoriteNotes.splice(idx, 1);
      renderFavoriteButton(false);
      isFav = false;
    } else {
      favoriteNotes.push({
        id: currentDrill.id,
        category: currentDrill.category,
        korean: currentDrill.korean,
        expression: currentDrill.target_expression,
        reference: currentDrill.reference_answer
      });
      renderFavoriteButton(true);
      isFav = true;
    }
    localStorage.setItem('favorite_notes', JSON.stringify(favoriteNotes));
  }

  function renderFavoriteButton(isFav) {
    btnToggleFavorite.classList.toggle('active', isFav);
    btnToggleFavorite.textContent = isFav ? '★' : '☆';
    btnToggleFavorite.setAttribute('aria-pressed', String(isFav));
    btnToggleFavorite.setAttribute('aria-label', isFav ? '즐겨찾기에서 제거' : '즐겨찾기에 보관');
    btnToggleFavorite.title = btnToggleFavorite.getAttribute('aria-label');
  }

  function renderFeedbackPoints(points, fallbackReason) {
    const items = Array.isArray(points) && points.length
      ? points
      : String(fallbackReason || '').split(/\n+/).filter(Boolean);
    feedbackReason.replaceChildren();
    (items.length ? items : ['교정문을 참고해 다음 문장에서 다시 시도해 보세요.']).slice(0, 3).forEach(point => {
      const item = document.createElement('p');
      item.className = 'feedback-point';
      item.textContent = point;
      feedbackReason.appendChild(item);
    });
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
    stopTimer();
    document.querySelector('#sumTotalSolved').textContent = `${dailyStats.solved}개`;
    const acc = dailyStats.solved ? Math.round((dailyStats.correct / dailyStats.solved) * 100) : 0;
    document.querySelector('#sumAccuracy').textContent = `${acc}%`;
    const avg = dailyStats.solved ? Math.round(dailyStats.timeTotal / dailyStats.solved) : 0;
    document.querySelector('#sumAvgSpeed').textContent = `${avg}초`;

    const keyList = document.querySelector('#sumKeyExpressions');
    keyList.innerHTML = '';
    const uniqueExp = dailyStats.expressions.filter(Boolean);
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
  window.addEventListener('authchange', () => {
    if (localStorage.getItem('jwt')) {
      window.location.reload();
    } else {
      init();
    }
  });
  window.addEventListener('trialgatecheck', () => {
    if (!localStorage.getItem('jwt')) init();
  });
})();
