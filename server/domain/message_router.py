"""메시지 분류 및 라우팅. 즉시 판별 + LLM 분류 하이브리드."""

from __future__ import annotations

import logging
import re

import httpx

from server.config.constants import (
    LIGHT_CHAT_SYSTEM_PROMPT,
    LIGHT_MAX_TOKENS,
    LIGHT_MODEL_URL,
    LIGHT_TIMEOUT_SEC,
    LLAMA_COMPLETION_PATH,
)

logger = logging.getLogger(__name__)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

VALID_CATEGORIES = {"chat", "read", "think", "tool"}
_DEFAULT_CATEGORY = "think"

# ── 즉시 판별 (LLM 안 탐) ───────────────────────────────

_GREETING = re.compile(
    r"^(하이|안녕|hi|hello|hey|반가워|ㅎㅇ|ㅋㅋ|감사|고마워|수고|"
    r"잘\s*자|잘\s*가|좋은\s*아침|좋은\s*하루|바이|bye|thanks)"
    r"[\s!?.~ㅋㅎ]*$",
    re.IGNORECASE,
)


_CLASSIFIER_SYSTEM = "<user input> 안의 메시지를 chat, read, think, tool 중 하나로 분류. 한 단어만 답."

_CATEGORY_RE = re.compile(r"\b(chat|read|think|tool)\b", re.IGNORECASE)


# ── 분류기 ───────────────────────────────────────────────


async def classify(
    message: str,
    prev_assistant: str | None = None,
) -> str:
    """하이브리드 분류: 즉시 판별 → LLM(맥락 포함) 폴백."""
    msg = message.strip()

    # 1. 즉시 판별 — 명확한 인사만 (맥락 불필요한 것만)
    if _GREETING.match(msg) and not prev_assistant:
        logger.info("분류(즉시): '%s' → chat [greeting]", msg[:30])
        return "chat"

    # 2. LLM 분류 — 이전 assistant 발화를 맥락으로 전달
    try:
        category = await _classify_llm(msg, prev_assistant)
        if category:
            logger.info("분류(LLM): '%s' → %s", msg[:30], category)
            return category
    except Exception as exc:
        logger.warning("LLM 분류 실패: %s", exc)

    # 3. 폴백
    logger.info("분류(폴백): '%s' → %s", msg[:30], _DEFAULT_CATEGORY)
    return _DEFAULT_CATEGORY


async def _classify_llm(
    message: str,
    prev_assistant: str | None = None,
) -> str | None:
    """/v1/chat/completions로 분류. 이전 대화 맥락 포함."""
    # 맥락이 있으면 user message에 한 줄로 포함
    if prev_assistant:
        user_content = f"이전: {prev_assistant[:60]}\n<user input>{message}</user input>"
    else:
        user_content = f"<user input>{message}</user input>"

    messages = [
        {"role": "system", "content": _CLASSIFIER_SYSTEM},
        {"role": "user", "content": user_content},
    ]

    url = f"{LIGHT_MODEL_URL}{LLAMA_COMPLETION_PATH}"
    payload = {
        "messages": messages,
        "max_tokens": 8,
        "temperature": 0.0,
        "think": False,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=LIGHT_TIMEOUT_SEC) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()

    data = resp.json()
    msg = data["choices"][0]["message"]
    raw = (msg.get("content") or "").strip()

    # think 태그 잔존 시 제거
    cleaned = _strip_think(raw) if "<think>" in raw else raw
    logger.info("LLM 분류 원문: [%s] → 정제: [%s]", raw[:80], cleaned[:80])

    match = _CATEGORY_RE.search(cleaned)
    return match.group(1).lower() if match else None


# ── think 태그 제거 ──────────────────────────────────────


def _strip_think(text: str) -> str:
    """<think>...</think> 제거 후 실제 답변만 반환."""
    cleaned = _THINK_RE.sub("", text).strip()
    if cleaned and cleaned != text.strip():
        return cleaned
    if "</think>" in text:
        return text.split("</think>", 1)[1].strip()
    return re.sub(r"</?think>", "", text).strip()


# ── 0.8B 채팅 응답 ──────────────────────────────────────


async def generate_chat_response(
    message: str,
    user_info: dict | None = None,
) -> str:
    """0.8B /v1/chat/completions로 간단한 채팅 응답을 생성한다."""
    system = LIGHT_CHAT_SYSTEM_PROMPT
    if user_info:
        name = user_info.get("name", "")
        if name:
            system += f"\n대화 상대: {name}"

    url = f"{LIGHT_MODEL_URL}{LLAMA_COMPLETION_PATH}"
    payload = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ],
        "max_tokens": LIGHT_MAX_TOKENS,
        "temperature": 0.6,
        "think": False,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=LIGHT_TIMEOUT_SEC) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        data = resp.json()
        raw = data["choices"][0]["message"].get("content") or ""
        result = _strip_think(raw) if "<think>" in raw else raw.strip()
        logger.info("0.8B 채팅 응답: [%s]", result[:100])
        return result or "안녕하세요! 서대리입니다."
    except Exception as exc:
        logger.error("0.8B 채팅 응답 실패: %s", exc)
        return "죄송합니다, 잠시 후 다시 시도해주세요."
