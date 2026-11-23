(() => {
  const navLinks = [...document.querySelectorAll('[data-learning-link]')];
  const sections = [...document.querySelectorAll('[data-learning-section]')];
  const historyList = document.querySelector('#historyList');
  const historyMessage = document.querySelector('#historyMessage');
  const analysisStats = document.querySelector('#analysisStats');
  const weakExpressions = document.querySelector('#weakExpressions');
  const recentTrend = document.querySelector('#recentTrend');
  const filterButtons = [...document.querySelectorAll('[data-history-filter]')];

  if (!historyList || !historyMessage || !analysisStats || !weakExpressions || !recentTrend) return;

  let records = [];
  let activeFilter = 'all';
  let loadedToken = null;
  let isLoading = false;
  let requestGeneration = 0;

  function isLoggedIn() {
    return Boolean(localStorage.getItem('jwt'));
  }

  function setLearningView(view) {
    const loggedIn = isLoggedIn();
    document.body.classList.toggle('learning-view-active', Boolean(loggedIn && view));
    document.querySelectorAll('main > .practice-lead, main > .project-intro, main > .architecture').forEach((section) => {
      section.hidden = Boolean(loggedIn && view);
    });
    for (const link of navLinks) {
      link.hidden = !loggedIn;
      link.setAttribute('aria-current', loggedIn && link.dataset.learningLink === view ? 'page' : 'false');
    }
    for (const section of sections) {
      section.hidden = !loggedIn || section.dataset.learningSection !== view;
    }
  }

  function viewFromLocation() {
    const view = location.hash === '#learning-history'
      ? 'history'
      : location.hash === '#learning-analysis'
        ? 'analysis'
        : null;
    setLearningView(view);
  }

  function clearLearningData() {
    records = [];
    loadedToken = null;
    historyList.replaceChildren();
    analysisStats.replaceChildren();
    weakExpressions.replaceChildren();
    recentTrend.replaceChildren();
    historyMessage.textContent = '';
  }

  async function loadHistory(force = false) {
    const token = localStorage.getItem('jwt');
    if (!token || (!force && token === loadedToken) || (isLoading && !force)) return;
    const generation = ++requestGeneration;
    isLoading = true;
    historyMessage.textContent = '학습 기록을 불러오는 중...';
    try {
      const response = await window.apiFetch('/api/drill_history');
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || '학습 기록을 불러오지 못했습니다.');
      if (generation !== requestGeneration || !isLoggedIn()) return;
      records = Array.isArray(payload.history) ? payload.history : [];
      loadedToken = localStorage.getItem('jwt');
      renderHistory();
      renderAnalysis();
    } catch (error) {
      if (generation === requestGeneration) {
        historyMessage.textContent = error.message || '학습 기록을 불러오지 못했습니다.';
      }
    } finally {
      if (generation === requestGeneration) isLoading = false;
    }
  }

  function isCorrect(record) {
    return record.outcome
      ? record.outcome === 'correct'
      : record.is_correct === true || record.is_correct === 1 || record.is_correct === 'true';
  }

  function appendText(parent, tagName, className, text) {
    const element = document.createElement(tagName);
    if (className) element.className = className;
    element.textContent = text;
    parent.append(element);
    return element;
  }

  function formatDate(value) {
    if (!value) return '날짜 정보 없음';
    const date = new Date(value);
    return Number.isNaN(date.getTime())
      ? '날짜 정보 없음'
      : new Intl.DateTimeFormat('ko-KR', { dateStyle: 'medium', timeStyle: 'short' }).format(date);
  }

  function feedbackItems(record) {
    if (Array.isArray(record.feedback_points)) return record.feedback_points;
    if (typeof record.feedback_points === 'string') {
      try {
        const parsed = JSON.parse(record.feedback_points);
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    }
    return [];
  }

  function createHistoryRow(record) {
    const row = document.createElement('tr');
    const correct = isCorrect(record);
    const points = feedbackItems(record).filter((point) => String(point).trim());
    const feedbackText = points[0] || record.missed_nuance || '';

    appendText(row, 'td', 'history-date-cell', formatDate(record.created_at));
    appendText(row, 'td', 'history-situation-cell', record.korean || '상황 정보 없음');
    appendText(row, 'td', 'history-expression-cell', record.target_expression || record.category || '기록 없음');
    appendText(row, 'td', 'history-answer-cell', record.user_text || '입력 답안 없음');
    appendText(row, 'td', 'history-corrected-cell', record.corrected_sentence || '-');

    const resultLabel = record.outcome === 'partial' ? '부분 정답' : correct ? '정답' : '오답';
    const resultCell = appendText(row, 'td', 'history-result-cell', resultLabel);
    resultCell.dataset.correct = String(correct);
    if (feedbackText) resultCell.title = feedbackText;
    return row;
  }

  function renderHistory() {
    const filteredRecords = records.filter((record) => {
      if (activeFilter === 'correct') return isCorrect(record);
      if (activeFilter === 'incorrect') return !isCorrect(record);
      return true;
    });
    historyList.replaceChildren();
    if (!records.length) {
      historyMessage.textContent = '아직 저장된 학습 기록이 없어요. 영작을 연습하면 여기에 쌓입니다.';
      return;
    }
    historyMessage.textContent = `최근 ${records.length}회 연습 기록`;
    if (!filteredRecords.length) {
      appendText(historyList, 'p', 'analysis-detail-copy', '이 필터에 해당하는 기록이 없습니다.');
      return;
    }
    const table = document.createElement('table');
    table.className = 'history-table';
    table.setAttribute('aria-label', '학습 기록');
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');
    for (const label of ['날짜', '상황', '핵심 표현', '내 답', '교정문', '판정']) {
      appendText(headerRow, 'th', '', label);
    }
    thead.append(headerRow);
    table.append(thead);

    const tbody = document.createElement('tbody');
    for (const record of filteredRecords) tbody.append(createHistoryRow(record));
    table.append(tbody);
    historyList.append(table);
  }

  function addStat(label, value) {
    const stat = document.createElement('div');
    stat.className = 'analysis-stat';
    appendText(stat, 'div', 'analysis-stat-value', value);
    appendText(stat, 'div', 'analysis-stat-label', label);
    analysisStats.append(stat);
  }

  function renderAnalysis() {
    analysisStats.replaceChildren();
    weakExpressions.replaceChildren();
    recentTrend.replaceChildren();
    if (!records.length) {
      appendText(analysisStats, 'p', 'analysis-detail-copy', '분석할 학습 기록이 아직 없습니다.');
      return;
    }

    const correctCount = records.filter(isCorrect).length;
    const timedRecords = records.map((record) => Number(record.time_spent)).filter((seconds) => Number.isFinite(seconds) && seconds > 0);
    const averageSeconds = timedRecords.length
      ? Math.round(timedRecords.reduce((sum, seconds) => sum + seconds, 0) / timedRecords.length)
      : null;
    addStat('완료 문장', `${records.length}개`);
    addStat(`정답률 · ${records.length}회 기준`, `${Math.round((correctCount / records.length) * 100)}%`);
    addStat('평균 답변 시간', averageSeconds === null ? '—' : `${averageSeconds}초`);

    const expressionStats = new Map();
    for (const record of records) {
      const expression = record.target_expression || record.category;
      if (!expression) continue;
      const current = expressionStats.get(expression) || { attempts: 0, misses: 0 };
      current.attempts++;
      if (!isCorrect(record)) current.misses++;
      expressionStats.set(expression, current);
    }
    const weak = [...expressionStats.entries()]
      .filter(([, stats]) => stats.attempts >= 2 && stats.misses > 0)
      .sort((left, right) => (right[1].misses / right[1].attempts) - (left[1].misses / left[1].attempts))
      .slice(0, 5);
    if (!weak.length) {
      appendText(weakExpressions, 'p', 'analysis-detail-copy', '표현별 기록이 2회 이상 쌓이면 다시 살펴볼 표현을 보여드릴게요.');
    } else {
      const list = document.createElement('div');
      list.className = 'weak-expression-list';
      for (const [expression, stats] of weak) {
        const row = document.createElement('div');
        row.className = 'weak-expression-row';
        appendText(row, 'span', '', expression);
        appendText(row, 'span', '', `${stats.misses}/${stats.attempts}회 다시 연습`);
        list.append(row);
      }
      weakExpressions.append(list);
    }

    if (records.length < 10) {
      appendText(recentTrend, 'p', 'analysis-detail-copy', '최근 기록의 흐름은 연습 기록이 10회 이상 쌓이면 비교해 보여드릴게요.');
      return;
    }
    const recent = records.slice(0, 5);
    const previous = records.slice(5, 10);
    const recentRate = Math.round((recent.filter(isCorrect).length / recent.length) * 100);
    const previousRate = Math.round((previous.filter(isCorrect).length / previous.length) * 100);
    const difference = recentRate - previousRate;
    const direction = difference > 0 ? '올랐어요' : difference < 0 ? '내려갔어요' : '같아요';
    appendText(recentTrend, 'p', 'analysis-detail-copy', `최근 5회 정답률은 ${recentRate}%, 그 이전 5회는 ${previousRate}%예요. ${Math.abs(difference)}%p ${direction}.`);
  }

  for (const button of filterButtons) {
    button.addEventListener('click', () => {
      activeFilter = button.dataset.historyFilter;
      for (const filter of filterButtons) {
        filter.setAttribute('aria-pressed', String(filter === button));
      }
      renderHistory();
    });
  }

  for (const link of navLinks) {
    link.addEventListener('click', (event) => {
      event.preventDefault();
      if (!isLoggedIn()) return;
      history.pushState(null, '', link.href);
      setLearningView(link.dataset.learningLink);
      document.querySelector(`[data-learning-section="${link.dataset.learningLink}"]`)?.scrollIntoView({ behavior: 'smooth' });
    });
  }

  const brandLink = document.querySelector('.brand');
  brandLink?.addEventListener('click', (event) => {
    event.preventDefault();
    history.pushState(null, '', location.pathname);
    setLearningView(null);
  });

  window.addEventListener('popstate', viewFromLocation);
  window.addEventListener('hashchange', viewFromLocation);
  window.addEventListener('authchange', () => {
    if (!isLoggedIn()) {
      requestGeneration++;
      isLoading = false;
      clearLearningData();
      setLearningView(null);
      return;
    }
    viewFromLocation();
    loadHistory();
  });
  window.addEventListener('learninghistorychange', () => loadHistory(true));

  viewFromLocation();
  if (isLoggedIn()) loadHistory();
})();
