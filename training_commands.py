"""Small, explicit practice command vocabulary; no model or side effects."""
import re

CATEGORIES = [
    "해외여행 ✈️", "게임 버그 🎮", "헬스장 🏋️", "배달 사고 🍕",
    "사내 갈등 💼", "고양이 집사 🐱", "서버 장애 💻", "당근마켓 거래 📦",
    "팀 프로젝트 🤝", "지하철 사고 🚇", "소개팅 😅", "카페 진상 ☕",
    "취업 면접 📋", "운전 초보 🚗", "반려견 산책 🐶",
]
TOPICS = dict(zip(
    ["여행", "게임", "운동", "배달", "회사", "고양이", "서버", "중고거래",
     "프로젝트", "지하철", "소개팅", "카페", "면접", "운전", "반려견"], CATEGORIES))
LEVELS = ["A2", "B1", "B1+", "B2", "B2+"]


def parse_command(text):
    text = str(text or "").strip()[:500]
    if re.fullmatch(
        r"(?:훈련|연습)(?:을)?\s*(?:종료|끝내|마치|마쳐|그만|마무리)\s*(?:기|자|할래|(?:해)?\s*(?:줘|주세요)|겠습니다)?[.!]?",
        text,
    ):
        return {"handled": True, "action": {"finish_session": True}}
    next_question = re.search(r"(?:다른|다음|새(?:로운)?)\s*문제|문제(?:를)?\s*(?:바꿔|넘겨|건너뛰)", text)
    relevant = re.search(r"오답|틀린|난이도|쉽게|어렵게|쉬운|어려운|주제|자동.*연습|일반.*연습|새.*문제|\b(?:A2|B1\+?|B2\+?)\b", text, re.I)
    if not relevant and any(topic in text for topic in TOPICS):
        relevant = re.search(r"연습|문제|바꿔", text)
    if not relevant and not next_question:
        return {"handled": False}
    # Explicit execution is required. Questions never change practice state.
    inquiry = re.search(r"[?？]|할 수|가능|해도|되나요|돼요|방법|어떻게|뭐야|무엇|알려|있어", text)
    execute = re.search(r"해\s*줘|바꿔|넘겨|건너뛰|설정|시작|풀래|할래|연습하자|문제\s*(?:줘|주세요)|복습하자", text)
    help_text = ("‘오답노트로 연습해 줘’, ‘난이도 B2로 바꿔 줘’, ‘좀 쉽게 해 줘’, "
                 "‘다른 문제로 바꿔 줘’, ‘여행 주제로 바꿔 줘’, ‘일반 연습 시작해 줘’라고 말해 보세요. "
                 "난이도는 A2, B1, B1+, B2, B2+를 지원합니다.")
    if inquiry or not (execute or re.fullmatch(r"(?:다른|다음|새)\s*문제", text)):
        return {"handled": True, "message": help_text, "action": None}
    settings = {}
    if re.search(r"오답|틀린", text):
        settings["mode"] = "wrong"
    elif re.search(r"일반.*연습", text):
        settings["mode"] = "normal"
    if "난이도" in text and "자동" in text:
        settings["level"] = "auto"
    else:
        level = re.search(r"(?<![A-Za-z0-9])(?:A2|B1\+?|B2\+?)(?![A-Za-z0-9])", text, re.I)
        if level:
            settings["level"] = level.group().upper()
        elif re.search(r"쉽게|쉬운|초급", text):
            settings["level"] = "easier"
        elif re.search(r"어렵게|어려운|고급", text):
            settings["level"] = "harder"
    if "주제" in text and "자동" in text:
        settings["topic"] = "auto"
    else:
        for topic, category in TOPICS.items():
            if topic in text:
                settings["topic"] = category
                break
    if not settings and next_question:
        settings["next_question"] = True
    if not settings:
        return {"handled": True, "action": None, "message": "바꿀 난이도나 주제를 알려 주세요. " + help_text}
    return {"handled": True, "action": settings, "message": "", "selection": "규칙 기반 선택"}
