"""메시지 라우팅. 기본 = 채팅(0.8B). 도구 필요 시에만 9B로 라우팅."""

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

# 분류기가 감지하는 특수 라우팅 (이것 외엔 전부 채팅)
_SPECIAL_RE = re.compile(r"\b(read|think|tool)\b", re.IGNORECASE)

_CLASSIFIER_SYSTEM = (
    "<user input> 안의 메시지에 <tools></tools> 호출이 필요하면 tool, "
    "정보 조회가 필요하면 read, 깊은 분석이 필요하면 think. "
    "아니면 아무것도 출력하지 마."
)


async def classify(
    message: str,
    prev_assistant: str | None = None,
) -> str:
    """기본 = chat. 특수 라우팅(tool/read/think) 필요할 때만 분류."""
    # LLM에게 특수 케이스인지만 물어봄
    try:
        category = await _detect_special(message, prev_assistant)
        if category:
            logger.info("분류: '%s' → %s", message[:30], category)
            return category
    except Exception as exc:
        logger.warning("분류 실패: %s → chat", exc)

    # 기본 = 채팅
    logger.info("분류: '%s' → chat", message[:30])
    return "chat"


async def _detect_special(
    message: str,
    prev_assistant: str | None = None,
) -> str | None:
    """특수 라우팅이 필요한지 LLM에게 물어본다. 필요 없으면 None."""
    if prev_assistant:
        user_content = f"이전: {prev_assistant[:60]}\n<user input>{message}</user input>"
    else:
        user_content = f"<user input>{message}</user input>"

    url = f"{LIGHT_MODEL_URL}{LLAMA_COMPLETION_PATH}"
    payload = {
        "messages": [
            {"role": "system", "content": _CLASSIFIER_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": 8,
        "temperature": 0.0,
        "think": False,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=LIGHT_TIMEOUT_SEC) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()

    data = resp.json()
    raw = (data["choices"][0]["message"].get("content") or "").strip()
    cleaned = _strip_think(raw) if "<think>" in raw else raw
    logger.info("분류 LLM 응답: [%s]", cleaned[:80])

    match = _SPECIAL_RE.search(cleaned)
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
    """0.8B로 채팅 응답을 생성한다."""
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
