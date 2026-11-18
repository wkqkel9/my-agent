# Requires Playwright and Chromium: pip install playwright; playwright install chromium
# Run from the repository: python tests/expansion.browser.py
from playwright.sync_api import sync_playwright
from pathlib import Path
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
 errors=[]
 for width in [1280,390]:
  page=browser.new_page(viewport={'width':width,'height':950},is_mobile=width==390,has_touch=width==390)
  page.on('pageerror',lambda error: errors.append(str(error)))
  page.goto((Path(__file__).resolve().parents[1] / 'index.html').as_uri())
  box=page.locator('#expandInput'); box.scroll_into_view_if_needed();box.click()
  box.fill('I raed a book.');box.press('Enter')
  assert page.locator('#feedbackTitle').inner_text()=='철자'
  assert page.locator('#expandHighlight .typed-typo').inner_text()=='raed'
  assert page.locator('#expansion button').count()==0
  box.fill('I read a book.');box.press('Enter')
  assert page.locator('#roundLabel').inner_text()=='02 / 04'
  box.fill('I read a book.');box.press('Enter')
  assert page.locator('#koreanPrompt mark').inner_text()=='잠들기 전에'
  assert page.locator('#feedbackReason').is_visible()
  box.press('Enter');assert 'before bed' in page.locator('#feedbackReason').inner_text()
  assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth'), 'horizontal overflow'
  box.fill('Before bed I read a book.');box.press('Enter')
  box.fill('I read books before bed every night.');box.press('Enter')
  box.fill('I read books before bed every night even when I am busy.');box.press('Enter')
  assert '완료' in page.locator('#expandStatus').inner_text()
  box.press('Enter');assert page.locator('#roundLabel').inner_text()=='01 / 04'
  page.evaluate('deadline=Date.now()-1;tick()')
  assert '시간 종료'==page.locator('#feedbackTitle').inner_text()
  box.click();assert page.locator('#roundLabel').inner_text()=='02 / 04'
  # Timeouts preserve the current answer and do not count as correct.
  box.fill('unfinished answer')
  page.evaluate('deadline=Date.now()-1;tick()')
  assert box.input_value()=='unfinished answer'
  box.press('Enter')
  page.evaluate('deadline=Date.now()-1;tick()')
  box.press('Enter')
  page.evaluate('deadline=Date.now()-1;tick()')
  box.press('Enter')
  assert '0 / 4' in page.locator('#expandStatus').inner_text()
  box.press('Enter')
  box.fill('I read')
  box.press('Enter')
  assert '무엇을 읽는지' in page.locator('#feedbackReason').inner_text()
  box.press('Enter')
  assert '무엇을 읽는지' in page.locator('#feedbackReason').inner_text()
  page.evaluate('deadline=Date.now()+29000;tick()')
  assert page.locator('#clock').get_attribute('data-phase')=='warning'
  page.evaluate('deadline=Date.now()+9000;tick()')
  assert page.locator('#clock').get_attribute('data-phase')=='urgent'
  assert page.locator('#copyTarget').inner_text().startswith('Every small step')
  page.close()
 assert not errors,errors
 browser.close()
 print('PASS: Chromium desktop/mobile layouts, original I read a book regression, inline typo, missing meaning, hints, completion, timeout, no buttons/overflow or page errors.')
