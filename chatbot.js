// Generated from ask-once/faq.json and chatbot.js; edit the source project.
(() => {
const CHATBOT_FAQ = {"categories": [{"id": "expansion", "label": "문장확장", "intro": "한글 문장을 보고 영어 문장 전체를 쓰는 연습이에요. 어떤 내용이 궁금하세요?", "keywords": ["문장확장", "문장 확장", "영작", "확장"], "items": [{"id": "start", "label": "시작·답 제출", "keywords": ["시작", "입력", "제출", "엔터", "enter", "전송", "키보드"], "answer": "문장확장 입력창을 누르면 60초가 시작돼요. 영어 문장 전체를 쓰고 Enter 또는 모바일 키보드의 전송 키로 확인하세요. 정답이면 다음 문장으로 바로 넘어가요."}, {"id": "timer", "label": "60초·시간 종료", "keywords": ["시간", "타이머", "60", "초", "종료"], "answer": "문장마다 60초가 주어져요. 답을 수정하는 동안에도 시간은 흘러요. 시간이 끝나면 입력한 답이 남고, Enter 또는 입력창을 눌러 다음 문장으로 넘어갈 수 있어요."}, {"id": "feedback", "label": "오류 표시·고치는 순서", "keywords": ["오류", "오답", "틀", "피드백", "힌트", "표시", "밑줄", "철자"], "answer": "현재는 불필요한 표현 → 틀린 표현 → 빠진 표현 순서로 한 항목만 안내해요. 입력한 오류 부분이나 한글에서 빠진 뜻을 확인하고, 수정 후 다시 제출하세요. 정답과 예시 답안은 알려주지 않아요."}, {"id": "grading", "label": "다르게 썼는데 판정이 안 돼요", "keywords": ["판정", "채점", "정답", "다른", "다르게", "맞", "인정"], "answer": "현재 체험은 등록된 표현과 규칙으로 판정해요. 같은 뜻이라도 등록되지 않은 표현은 판정하지 못할 수 있어요. 챗봇은 이용 방법을 안내하며, 입력한 영어 문장의 정오를 따로 판단하지 않아요."}, {"id": "restart", "label": "완료·다시 연습", "keywords": ["완료", "다시", "재시작", "점수", "몇", "문장 수"], "answer": "체험은 네 문장이에요. 완료하면 정답 수가 표시되고, 시간 초과로 넘긴 문장은 정답에 포함되지 않아요. Enter 또는 입력창을 누르면 첫 문장부터 다시 시작해요."}]}, {"id": "copy", "label": "필사", "intro": "흐리게 보이는 영어 문장을 그대로 따라 쓰는 연습이에요. 어떤 내용이 궁금하세요?", "keywords": ["필사", "따라", "베껴"], "items": [{"id": "start", "label": "필사 시작하기", "keywords": ["시작", "방법", "입력", "어떻게"], "answer": "필사 영역의 흐린 영어 문장을 누르고 그대로 입력하세요. 맞게 입력한 글자는 진하게 채워져요. 시간 제한 없이 천천히 연습할 수 있어요."}, {"id": "mistake", "label": "글자가 빨갛게 보여요", "keywords": ["빨", "틀", "오류", "오답", "표시", "띄어쓰기", "대소문자", "마침표"], "answer": "예문과 다른 위치의 글자는 빨갛게 표시돼요. 대소문자, 띄어쓰기, 마침표를 확인하고 입력창에서 수정하세요. 필사는 같은 뜻으로 바꿔 쓰는 영작이 아니라 보이는 문장을 그대로 쓰는 연습이에요."}, {"id": "next", "label": "다음 문장·완료", "keywords": ["다음", "완료", "문장", "넘어", "몇"], "answer": "필사 체험에는 세 문장이 있어요. 마침표까지 입력하면 완료 안내가 나오고, ‘다음 문장’ 버튼으로 넘어갈 수 있어요. 세 번째 다음에는 첫 문장으로 돌아와요."}, {"id": "timer", "label": "필사에도 시간 제한이 있나요?", "keywords": ["시간", "타이머", "초", "제한"], "answer": "필사는 시간 제한이 없어요. 60초 타이머는 문장확장에만 적용돼요."}]}, {"id": "general", "label": "이용 안내", "intro": "현재 페이지에서 제공하는 연습과 이용 범위를 안내해요.", "keywords": ["이용", "기능", "차이", "도움", "가입", "로그인", "저장", "기록", "개인정보"], "items": [{"id": "difference", "label": "문장확장과 필사의 차이", "keywords": ["차이", "기능", "연습", "추천"], "answer": "문장확장은 한글의 뜻을 영어로 직접 쓰는 60초 연습이에요. 필사는 보이는 영어 문장을 그대로 따라 쓰며 글자와 표현을 익히는 시간 제한 없는 연습이에요."}, {"id": "account", "label": "가입·연습 기록", "keywords": ["가입", "로그인", "저장", "기록", "개인정보"], "answer": "가입 없이 이용할 수 있어요. 현재는 연습 결과와 챗봇 대화를 계정에 저장하는 기능이 없어요. 새로고침하면 연습과 대화가 초기화돼요."}, {"id": "scope", "label": "챗봇이 도와주는 범위", "keywords": ["챗봇", "ai", "질문", "번역", "첨삭", "해석", "영어"], "answer": "이 챗봇은 문장확장·필사의 사용 방법을 준비된 FAQ로 안내해요. 영어 문장 채점, 번역, 자유 대화는 제공하지 않아요. 아래에서 기능을 고른 뒤 궁금한 항목을 선택하세요."}]}]};
(() => {
'use strict';
const fab=document.querySelector('#chatFab'),panel=document.querySelector('#chatPanel');
const input=document.querySelector('#chatInput'),log=document.querySelector('#chatLog'),options=document.querySelector('#chatOptions');
const categories=CHATBOT_FAQ.categories;
let category=null;
function message(text,user=false){
 const node=document.createElement('div');node.className='message'+(user?' user':'');node.textContent=text;
 log.append(node);log.scrollTop=log.scrollHeight;
}
function choices(items){
 options.replaceChildren();
 for(const item of items){const button=document.createElement('button');button.type='button';button.textContent=item.label;button.addEventListener('click',item.action);options.append(button);}
}
function home(announce=true){
 category=null;
 if(announce)message('궁금한 기능을 골라주세요. 기능을 선택하면 세부 질문이 나와요.');
 choices(categories.map(group=>({label:group.label,action:()=>openCategory(group)})));
}
function subchoices(){
 choices([...category.items.map(item=>({label:item.label,action:()=>answer(item)})),{label:'‹ 다른 기능 보기',action:()=>home()}]);
}
function openCategory(group){category=group;message(group.label,true);message(group.intro);subchoices();}
function answer(item){message(item.label,true);message(item.answer);subchoices();}
function setOpen(open){panel.hidden=!open;fab.setAttribute('aria-expanded',String(open));(open?input:fab).focus();}
fab.addEventListener('click',()=>setOpen(panel.hidden));
document.querySelector('#closeChat').addEventListener('click',()=>setOpen(false));
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!panel.hidden)setOpen(false);});
function ask(value){
 const question=value.trim();if(!question)return;
 message(question,true);input.value='';
 if(/^(처음|메뉴|뒤로|홈|다른 기능)$/.test(question)){home();return;}
 const normalized=question.toLowerCase();
 const explicit=categories.filter(group=>group.keywords.some(word=>normalized.includes(word)));
 if(explicit.length>1){message('여러 기능이 관련돼 있어요. 먼저 확인할 기능을 골라주세요.');home(false);return;}
 const group=explicit[0]||category;
 if(!group){message('문장확장·필사 이용 방법을 안내해드려요. 아래에서 기능을 고르면 세부 질문을 선택할 수 있어요.');home(false);return;}
 category=group;
 const ranked=group.items.map(item=>({item,score:item.keywords.filter(word=>normalized.includes(word)).length})).sort((a,b)=>b.score-a.score);
 if(ranked[0].score>0&&(ranked.length===1||ranked[0].score>ranked[1].score))message(ranked[0].item.answer);
 else message(group.intro);
 subchoices();
}
document.querySelector('#chatForm').addEventListener('submit',event=>{event.preventDefault();ask(input.value);});
home(false);
})();

})();
