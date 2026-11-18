from playwright.sync_api import sync_playwright
from pathlib import Path
import os,json
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
 for width in [1280,390]:
  page=browser.new_page(viewport={'width':width,'height':950})
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  def assess(route):
   data=route.request.post_data_json
   if data['text']=='offline':route.abort();return
   result={'kind':'error','label':'틀린 표현','hint':'앞으로 할 계획을 나타내요. 반복하는 습관에 맞게 현재 시제로 바꿔보세요.','range':[2,7],'meaning':'읽는다'}
   route.fulfill(status=200,content_type='application/json',headers={'Access-Control-Allow-Origin':'*'},body=json.dumps(result))
  page.route('**/api/assess',assess)
  page.goto(os.environ.get('EXPANSION_TEST_URL',(Path(__file__).resolve().parents[1]/'index.html').as_uri()))
  box=page.locator('#expandInput');box.click();box.fill('I gonna read a book');box.press('Enter')
  page.wait_for_function('document.querySelector("#expansionFeedback").dataset.kind==="error"')
  assert page.locator('#expandHighlight .typed-wrong').inner_text()=='gonna'
  assert '현재 시제' in page.locator('#feedbackReason').inner_text()
  box.fill('offline');box.press('Enter');page.wait_for_function('document.querySelector("#expansionFeedback").dataset.kind==="unavailable"')
  assert '다시 시도' in page.locator('#feedbackReason').inner_text()
  box.fill('I read a book');box.press('Enter');assert '02' in page.locator('#roundLabel').inner_text()
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  assert not errors,errors
  page.close()
 browser.close()
 print('Desktop/mobile AI feedback, highlight, failure, accepted advancement and layout passed')
