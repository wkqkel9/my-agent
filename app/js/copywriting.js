(() => {
  const quotes = [
    ['Every small step is a new beginning.', '작은 한 걸음마다 새로운 시작이 있어요.'],
    ['Make a little room for something new.', '새로운 것을 위한 작은 여유를 만들어보세요.'],
    ['Let your thoughts find their own words.', '생각이 저만의 문장을 찾도록 해보세요.'],
  ];
  const copyInput = document.querySelector('#copyInput');
  if (!copyInput) return;

  const copyStatus = document.querySelector('#copyStatus');
  const copyTarget = document.querySelector('#copyTarget');
  const copyReference = document.querySelector('#copyReference');
  const translation = document.querySelector('#translation');
  const copyCount = document.querySelector('#copyCount');
  const nextQuote = document.querySelector('#nextQuote');
  let quoteIndex = 0;

  function updateCopy() {
    const text = copyInput.value;
    const target = quotes[quoteIndex][0];
    copyInput.maxLength = target.length;

    const fragment = document.createDocumentFragment();
    [...target].forEach((char, index) => {
      const span = document.createElement('span');
      const entered = text[index];
      span.textContent = entered === undefined ? char : entered;
      span.className = entered === undefined ? '' : entered === char ? 'typed-correct' : 'typed-wrong';
      fragment.append(span);
    });
    copyTarget.replaceChildren(fragment);
    copyReference.textContent = target;

    if (text === target) {
      copyStatus.textContent = '✓ 한 문장 완료! 다음 문장도 만나보세요.';
      copyStatus.style.color = '#4c7541';
    } else {
      const wrong = [...text].findIndex((char, index) => char !== target[index]);
      copyStatus.textContent = wrong >= 0
        ? `${wrong + 1}번째 글자를 확인해보세요. 대소문자와 띄어쓰기도 같게 써주세요.`
        : `${text.length} / ${target.length}자 · 천천히, 문장의 흐름을 느껴보세요.`;
      copyStatus.style.color = wrong >= 0 ? '#ce512f' : '';
    }
  }

  copyInput.addEventListener('input', updateCopy);
  nextQuote?.addEventListener('click', () => {
    quoteIndex = (quoteIndex + 1) % quotes.length;
    translation.textContent = quotes[quoteIndex][1];
    copyCount.textContent = `0${quoteIndex + 1} / 03`;
    copyInput.value = '';
    updateCopy();
    copyInput.focus();
  });
  updateCopy();
})();
