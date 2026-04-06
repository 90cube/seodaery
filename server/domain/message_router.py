"""메시지 분류 및 라우팅. 0.8B로 분류, chat이면 0.8B가 즉답."""

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
    ROUTER_SYSTEM_PROMPT,
)
from server.system.llama_client import request_completion

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {"chat", "read", "think", "tool"}
_DEFAULT_CATEGORY = "think"
_CATEGORY_PATTERN = re.compile(r"\b(chat|read|think|tool)\b", re.IGNORECASE)


async def classify(message: str) -> str:
    """사용자 메시지를 0.8B로 분류한다. chat/read/think/tool 중 하나 반환."""
    messages = [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": message},
    ]
    try:
        category = await _classify_raw(messages)
        if category:
            logger.info("분류: '%s' → %s", message[:30], category)
            return category
        logger.warning("분류 실패 → %s", _DEFAULT_CATEGORY)
    except Exception as exc:
        logger.warning("분류 오류: %s → %s", exc, _DEFAULT_CATEGORY)
    return _DEFAULT_CATEGORY


async def _classify_raw(messages: list[dict]) -> str | None:
    """0.8B API를 직접 호출하여 content + reasoning 모두에서 분류 단어를 찾는다."""
    url = f"{LIGHT_MODEL_URL}{LLAMA_COMPLETION_PATH}"
    payload = {
        "messages": messages,
        "max_tokens": 64,
        "temperature": 0.0,
        "stream": False,
        "think": False,
    }
    async with httpx.AsyncClient(timeout=LIGHT_TIMEOUT_SEC) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()

    data = resp.json()
    msg = data["choices"][0]["message"]
    content = msg.get("content") or ""
    reasoning = msg.get("reasoning_content") or ""

    logger.info(
        "0.8B 원문 — content: [%s] / reasoning: [%s]",
        content[:200], reasoning[:200],
    )

    # content를 우선 검사, 없으면 reasoning에서 마지막 분류 단어를 찾음
    for text in [content, reasoning]:
        matches = _CATEGORY_PATTERN.findall(text)
        if matches:
            return matches[-1].lower()
    return None


async def generate_chat_response(
    message: str,
    user_info: dict | None = None,
) -> str:
    """0.8B로 간단한 채팅 응답을 생성한다."""
    system = LIGHT_CHAT_SYSTEM_PROMPT
    if user_info:
        name = user_info.get("name", "")
        if name:
            system += f"\n대화 상대: {name}"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": message},
    ]
    try:
        raw = await request_completion(
            base_url=LIGHT_MODEL_URL,
            messages=messages,
            max_tokens=LIGHT_MAX_TOKENS,
            timeout=LIGHT_TIMEOUT_SEC,
            temperature=0.6,
            think_param=False,
            strip_think=True,
        )
        return raw.strip()
    except Exception as exc:
        logger.error("0.8B 채팅 응답 실패: %s", exc)
        return "죄송합니다, 잠시 후 다시 시도해주세요."
