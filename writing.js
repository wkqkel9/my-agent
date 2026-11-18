const expandInput=document.querySelector('#expandInput'),clock=document.querySelector('#clock'),expandStatus=document.querySelector('#expandStatus');
const feedback=document.querySelector('#expansionFeedback'),expandSurface=document.querySelector('#expandSurface'),expandHighlight=document.querySelector('#expandHighlight');
const prompts=['나는 책을 읽는다.','나는 잠들기 전에 책을 읽는다.','나는 매일 밤 잠들기 전에 책을 읽는다.','나는 바쁜 날에도 매일 밤 잠들기 전에 책을 읽는다.'];
const addedPhrases=['','잠들기 전에','매일 밤','바쁜 날에도'];
const clauses=[['before bed','before going to bed','before i go to bed','before bedtime','before sleeping','before i sleep','prior to going to bed'],['every night','each night'],['even when i am busy','even on busy days','even if i am busy']];
let round=0,running=false,deadline=0,interval=null,practiceState='idle',solved=0,assessmentId=0,assessmentController=null,assessmentKey=null;
const assessmentCache=new Map();
function cancelAssessment(){assessmentId++;if(assessmentController)assessmentController.abort();assessmentController=null;assessmentKey=null;}
function normalizeAnswer(value){return value.toLowerCase().replace(/[’‘]/g,"'").replace(/\bi'm\b/g,'i am').replace(/\bdon't\b/g,'do not').replace(/[.,!?;:]/g,' ').replace(/\s+/g,' ').trim();}
function updatePrompt(meaning=''){
 const prompt=document.querySelector('#koreanPrompt');prompt.replaceChildren();
 const phrase=meaning||addedPhrases[round],position=phrase?prompts[round].indexOf(phrase):-1;
 if(position<0){prompt.textContent=prompts[round];}else{const tag=document.createElement(meaning?'mark':'u');tag.textContent=phrase;prompt.append(document.createTextNode(prompts[round].slice(0,position)),tag,document.createTextNode(prompts[round].slice(position+phrase.length)));}
 document.querySelector('#roundLabel').textContent=`0${round+1} / 04`;
}
function permutations(parts){return parts.length?parts.flatMap((part,i)=>permutations(parts.filter((_,j)=>i!==j)).map(tail=>[part,...tail])):[[]];}
const answerCache=new Map();
function acceptedAnswers(stage=round){
 if(answerCache.has(stage))return answerCache.get(stage);
 let sets=[['i read books'],['i read a book'],['i read the book'],['i read the books']];
 for(let i=0;i<stage;i++)sets=sets.flatMap(parts=>clauses[i].map(clause=>[...parts,clause]));
 const answers=[...new Set(sets.flatMap(parts=>permutations(parts).map(order=>order.join(' '))))];answerCache.set(stage,answers);return answers;
}
function syncExpansionScroll(){expandHighlight.scrollTop=expandInput.scrollTop;expandHighlight.scrollLeft=expandInput.scrollLeft;}
function clearFeedback(){feedback.hidden=true;expandSurface.dataset.reviewed='false';expandHighlight.replaceChildren();updatePrompt();}
function highlightAnswer(result){
 const text=expandInput.value,fragment=document.createDocumentFragment();let range=result.range;
 if(!range&&result.pattern){const match=result.pattern.exec(text);if(match)range=[match.index,match.index+match[0].length];}
 if(!range){expandSurface.dataset.reviewed='false';expandHighlight.replaceChildren();return;}
 fragment.append(document.createTextNode(text.slice(0,range[0])));const span=document.createElement('span');span.className=result.kind==='typo'?'typed-typo':'typed-wrong';span.textContent=text.slice(...range);fragment.append(span,document.createTextNode(text.slice(range[1])+'\n'));expandHighlight.replaceChildren(fragment);expandSurface.dataset.reviewed='true';syncExpansionScroll();
}
function showFeedback(result){
 if(result.kind==='correct'){solved++;const message=result.hint;advanceSentence();if(practiceState!=='complete')expandStatus.textContent=`✓ ${message} 다음 문장에 60초가 주어져요.`;return;}
 feedback.dataset.kind=result.kind;document.querySelector('#feedbackTitle').textContent=result.label;document.querySelector('#feedbackReason').textContent=result.hint;feedback.hidden=false;updatePrompt(result.meaning);highlightAnswer(result);
 expandStatus.textContent='수정 후 Enter로 다시 확인 · 시간은 계속 흘러요.';
}
function tick(){
 const remaining=Math.max(0,Math.ceil((deadline-Date.now())/1000));document.querySelector('#clockSeconds').textContent=String(remaining);clock.dataset.phase=remaining<=10?'urgent':remaining<=30?'warning':'normal';clock.dataset.running=String(running&&remaining>0);clock.setAttribute('aria-label',`이 문장 남은 시간 ${remaining}초`);if(!remaining)finish();
}
function beginSentence(){
 cancelAssessment();
 clearInterval(interval);practiceState='writing';running=true;clearFeedback();expandInput.value='';expandInput.placeholder='영어 문장을 쓰고 Enter ↵';deadline=Date.now()+60000;expandStatus.textContent='Enter로 확인 · 정답이면 다음 문장으로 넘어가요.';tick();interval=setInterval(tick,250);expandInput.focus({preventScroll:true});
}
function startPractice(){round=0;solved=0;beginSentence();}
function advanceSentence(){
 clearInterval(interval);running=false;clock.dataset.running='false';
 if(round===prompts.length-1){practiceState='complete';clearFeedback();expandInput.value='';expandInput.placeholder='연습 완료! 여기를 누르면 다시 시작해요.';expandStatus.textContent=`✓ 연습 완료 · ${solved} / ${prompts.length}문장 정답. Enter 또는 입력창을 눌러 다시 시작하세요.`;return;}
 round++;beginSentence();
}
function finish(){
 cancelAssessment();
 clearInterval(interval);running=false;practiceState='timeout';clock.dataset.running='false';document.querySelector('#clockSeconds').textContent='0';
 expandSurface.dataset.reviewed='false';expandHighlight.replaceChildren();feedback.dataset.kind='timeout';document.querySelector('#feedbackTitle').textContent='시간 종료';document.querySelector('#feedbackReason').textContent='입력한 답은 그대로 남겨뒀어요. 한글 문장의 뜻과 비교해보세요.';feedback.hidden=false;updatePrompt();expandStatus.textContent='Enter를 누르거나 입력창을 눌러 다음으로 넘어가세요.';
}
function submitExpansionAnswer(){
 if(practiceState==='idle'||practiceState==='complete'){startPractice();return;}
 if(practiceState==='timeout'){advanceSentence();return;}
 if(Date.now()>=deadline){finish();return;}
 const text=expandInput.value,key=JSON.stringify([round,text]);
 if(assessmentKey===key)return;
 cancelAssessment();
 if(acceptedAnswers().includes(normalizeAnswer(text))){
  showFeedback({kind:'correct',hint:'같은 뜻의 올바른 표현이에요.'});return;
 }
 if(assessmentCache.has(key)){showFeedback(assessmentCache.get(key));return;}
 const requestId=assessmentId,requestRound=round;
 assessmentKey=key;
 clearFeedback();
 expandStatus.textContent='Enter로 확인 · 정답이면 다음 문장으로 넘어가요.';
 const controller=typeof AbortController==='function'?new AbortController():null;
 assessmentController=controller;
 const timeoutId=controller?setTimeout(()=>controller.abort(),25000):null;
 const isCurrent=()=>assessmentId===requestId&&round===requestRound&&expandInput.value===text&&running&&practiceState==='writing'&&Date.now()<deadline;
 const failed=()=>{if(isCurrent())showFeedback({kind:'unavailable',label:'평가 실패',hint:'평가 응답을 받지 못했어요. Enter를 눌러 다시 시도해주세요.'});};
 Promise.resolve().then(()=>fetch('https://writing-server.vercel.app/api/assess',{
  method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({text,round:requestRound,session_id:'web-session'}),
  signal:controller?controller.signal:undefined
 })).then(resp=>{if(!resp.ok)throw new Error('Assessment request failed');return resp.json();})
 .then(aiResult=>{
  if(!isCurrent())return;
  if(!aiResult||!['correct','extra','error','typo','incomplete'].includes(aiResult.kind)||typeof aiResult.hint!=='string'||!aiResult.hint||typeof aiResult.label!=='string')throw new Error('Invalid assessment');
  assessmentCache.set(key,aiResult);
  if(assessmentCache.size>100)assessmentCache.delete(assessmentCache.keys().next().value);
  showFeedback(aiResult);
 }).catch(failed).finally(()=>{if(timeoutId)clearTimeout(timeoutId);if(assessmentId===requestId){assessmentController=null;assessmentKey=null;}});
}
expandInput.addEventListener('focus',()=>{if(practiceState==='idle')startPractice();});
expandInput.addEventListener('click',()=>{if(practiceState==='complete')startPractice();else if(practiceState==='timeout')advanceSentence();});
expandInput.addEventListener('input',()=>{if(practiceState==='writing'){cancelAssessment();clearFeedback();expandStatus.textContent='Enter로 확인 · 남은 시간 안에 자유롭게 고쳐보세요.';}});
expandInput.addEventListener('scroll',syncExpansionScroll);
document.querySelector('#expandForm').addEventListener('submit',event=>{event.preventDefault();submitExpansionAnswer();});
expandInput.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.isComposing){event.preventDefault();submitExpansionAnswer();}});
expandInput.addEventListener('beforeinput',event=>{if(!event.isComposing&&['insertLineBreak','insertParagraph'].includes(event.inputType)){event.preventDefault();submitExpansionAnswer();}});
document.addEventListener('visibilitychange',()=>{if(running)tick();});
