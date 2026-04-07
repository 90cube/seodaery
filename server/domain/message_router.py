"""메시지 분류 및 라우팅. 규칙 기반 분류 + 0.8B chat 응답."""

from __future__ import annotations

import logging
import re

import httpx

from server.config.constants import (
    LIGHT_CHAT_SYSTEM_PROMPT,
    LIGHT_MAX_TOKENS,
    LIGHT_MODEL_URL,
    LIGHT_TIMEOUT_SEC,
)

logger = logging.getLogger(__name__)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

VALID_CATEGORIES = {"chat", "read", "think", "tool"}

# ── 규칙 기반 분류 패턴 ──────────────────────────────────

_GREETING = re.compile(
    r"^(하이|안녕|hi|hello|hey|반가워|ㅎㅇ|ㅎㅎ|ㅋㅋ|감사|고마워|고맙|수고|"
    r"잘\s*자|잘\s*가|좋은\s*아침|좋은\s*하루|바이|bye|thanks|thank)"
    r"[\s!?.~ㅋㅎ]*$",
    re.IGNORECASE,
)

_CHAT_SHORT = re.compile(
    r"^(네|응|ㅇㅇ|ㅇㅋ|ㄱㄱ|ㅎ|ㄴ|뭐|누구|뭐해|뭐야|왜|아|오|헐|"
    r"ㄷㄷ|대박|진짜|마자|맞아|그래|알겠|ok|yes|no|nope|yep|sure|lol)"
    r"[\s!?.~ㅋㅎ]*$",
    re.IGNORECASE,
)

_TOOL_ACTION = re.compile(
    r"(등록|생성|만들|추가|삭제|제거|수정|변경|설정|예약|"
    r"일정\s*(잡|만|등록|추가|삭제)|스케줄|취소|업데이트)",
    re.IGNORECASE,
)

_READ_QUERY = re.compile(
    r"(조회|검색|찾아|목록|리스트|보여|알려|확인|몇\s*개|"
    r"어떤|무슨|언제|어디|누가|몇\s*시|오늘\s*일정|내\s*일정)",
    re.IGNORECASE,
)


def classify(message: str) -> str:
    """규칙 기반으로 메시지를 분류한다. LLM 호출 없음."""
    msg = message.strip()

    # 1. 인사 / 짧은 대화
    if _GREETING.match(msg):
        logger.info("분류(규칙): '%s' → chat [greeting]", msg[:30])
        return "chat"

    # 2. 초단문 대화 (5자 이하이거나 패턴 매칭)
    if len(msg) <= 5 or _CHAT_SHORT.match(msg):
        logger.info("분류(규칙): '%s' → chat [short]", msg[:30])
        return "chat"

    # 3. 도구 호출 (생성/삭제/예약 등 액션 동사)
    if _TOOL_ACTION.search(msg):
        logger.info("분류(규칙): '%s' → tool [action]", msg[:30])
        return "tool"

    # 4. 조회/검색 (보여줘/목록/확인 등)
    if _READ_QUERY.search(msg):
        logger.info("분류(규칙): '%s' → read [query]", msg[:30])
        return "read"

    # 5. 기본: 사고가 필요한 질문
    logger.info("분류(규칙): '%s' → think [default]", msg[:30])
    return "think"


# ── 0.8B 채팅 응답 ───────────────────────────────────────


def _strip_think(text: str) -> str:
    """<think>...</think> 제거 후 실제 답변만 반환."""
    cleaned = _THINK_RE.sub("", text).strip()
    if cleaned and cleaned != text.strip():
        return cleaned
    if "</think>" in text:
        return text.split("</think>", 1)[1].strip()
    return re.sub(r"</?think>", "", text).strip()


async def generate_chat_response(
    message: str,
    user_info: dict | None = None,
) -> str:
    """0.8B /completion으로 간단한 채팅 응답을 생성한다."""
    system = LIGHT_CHAT_SYSTEM_PROMPT
    if user_info:
        name = user_info.get("name", "")
        if name:
            system += f"\n대화 상대: {name}"

    prompt = f"<|system|>\n{system}\n<|user|>\n{message}\n<|assistant|>\n"
    url = f"{LIGHT_MODEL_URL}/completion"
    payload = {
        "prompt": prompt,
        "n_predict": LIGHT_MAX_TOKENS,
        "temperature": 0.6,
        "stop": ["<|", "</s>"],
    }
    try:
        async with httpx.AsyncClient(timeout=LIGHT_TIMEOUT_SEC) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        raw = resp.json().get("content", "")
        result = _strip_think(raw)
        logger.info("0.8B 채팅 응답: [%s]", result[:100])
        return result or "안녕하세요! 서대리입니다."
    except Exception as exc:
        logger.error("0.8B 채팅 응답 실패: %s", exc)
        return "죄송합니다, 잠시 후 다시 시도해주세요."
