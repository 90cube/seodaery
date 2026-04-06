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
    ROUTER_SYSTEM_PROMPT,
)
from server.system.llama_client import request_completion

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {"chat", "read", "think", "tool"}
_DEFAULT_CATEGORY = "think"

# 0.8B가 분류 단어 대신 동의어를 쓸 수 있으므로 매핑
_SYNONYM_MAP = {
    # chat
    "chat": "chat", "greeting": "chat", "hello": "chat", "hi": "chat",
    "casual": "chat", "small": "chat", "thanks": "chat", "thank": "chat",
    "simple": "chat",
    # read
    "read": "read", "lookup": "read", "list": "read", "fetch": "read",
    "search": "read", "query": "read", "show": "read", "view": "read",
    # think
    "think": "think", "analysis": "think", "analyze": "think",
    "explain": "think", "complex": "think", "summarize": "think",
    "compare": "think", "reason": "think",
    # tool
    "tool": "tool", "create": "tool", "register": "tool", "assign": "tool",
    "delete": "tool", "update": "tool", "schedule": "tool", "action": "tool",
}
_SYNONYM_PATTERN = re.compile(
    r"\b(" + "|".join(_SYNONYM_MAP.keys()) + r")\b", re.IGNORECASE,
)


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
    """0.8B /completion 엔드포인트로 순수 텍스트 분류."""
    # chat completions의 think 모드를 우회하기 위해 /completion 사용
    system = messages[0]["content"]
    user_msg = messages[1]["content"]
    prompt = f"<|system|>\n{system}\n<|user|>\n{user_msg}\n<|assistant|>\n"

    url = f"{LIGHT_MODEL_URL}/completion"
    payload = {
        "prompt": prompt,
        "n_predict": 16,
        "temperature": 0.0,
        "stop": ["\n", "<|", "</s>"],
    }
    async with httpx.AsyncClient(timeout=LIGHT_TIMEOUT_SEC) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()

    data = resp.json()
    content = data.get("content", "")
    logger.info("0.8B 원문: [%s]", content.strip())

    matches = _SYNONYM_PATTERN.findall(content)
    if matches:
        last_match = matches[-1].lower()
        return _SYNONYM_MAP.get(last_match)
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
