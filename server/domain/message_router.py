"""메시지 분류 및 라우팅. 0.8B로 분류, chat이면 0.8B가 즉답."""

from __future__ import annotations

import logging

from server.config.constants import (
    LIGHT_CHAT_SYSTEM_PROMPT,
    LIGHT_MAX_TOKENS,
    LIGHT_MODEL_URL,
    LIGHT_TIMEOUT_SEC,
    ROUTER_SYSTEM_PROMPT,
)
from server.system.llama_client import request_completion

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {"chat", "read", "think", "tool"}
_DEFAULT_CATEGORY = "think"


async def classify(message: str) -> str:
    """사용자 메시지를 0.8B로 분류한다. chat/read/think/tool 중 하나 반환."""
    messages = [
        {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": message},
    ]
    try:
        raw = await request_completion(
            base_url=LIGHT_MODEL_URL,
            messages=messages,
            max_tokens=10,
            timeout=LIGHT_TIMEOUT_SEC,
            temperature=0.0,
        )
        category = raw.strip().lower().split()[0]
        if category in VALID_CATEGORIES:
            logger.info("분류: '%s' → %s", message[:30], category)
            return category
        logger.warning("분류 실패 (무효 카테고리: %s) → %s", raw, _DEFAULT_CATEGORY)
    except Exception as exc:
        logger.warning("분류 오류: %s → %s", exc, _DEFAULT_CATEGORY)
    return _DEFAULT_CATEGORY


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
        )
        return raw.strip()
    except Exception as exc:
        logger.error("0.8B 채팅 응답 실패: %s", exc)
        return "죄송합니다, 잠시 후 다시 시도해주세요."
