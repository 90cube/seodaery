"""0.8B 라우터 의도 분류. 순수 도메인 로직 — 외부 프레임워크 의존 금지."""

from __future__ import annotations

from server.config.constants import (
    EXECUTOR_MODEL_NAME,
    EXECUTOR_MODEL_URL,
    EXECUTOR_MAX_TOKENS,
    EXECUTOR_TIMEOUT_SEC,
    INTENT_CLASSIFICATION_PROMPT,
    INTENT_COMPLEX,
    INTENT_SIMPLE,
    ROUTER_MAX_TOKENS,
    ROUTER_MODEL_NAME,
    ROUTER_MODEL_URL,
    ROUTER_TIMEOUT_SEC,
)
from server.model.schemas import ChatResponse, Intent
from server.system.llama_client import request_completion


async def classify_intent(message: str) -> Intent:
    """0.8B 모델로 사용자 메시지의 의도를 분류한다."""
    messages = [
        {"role": "system", "content": INTENT_CLASSIFICATION_PROMPT},
        {"role": "user", "content": message},
    ]

    raw = await request_completion(
        base_url=ROUTER_MODEL_URL,
        messages=messages,
        max_tokens=ROUTER_MAX_TOKENS,
        timeout=ROUTER_TIMEOUT_SEC,
        temperature=0.0,
    )

    normalized = raw.lower().strip().strip(".")
    if INTENT_COMPLEX in normalized:
        return Intent.COMPLEX
    return Intent.SIMPLE


async def handle_simple(request_id: str, message: str) -> ChatResponse:
    """단순 요청을 0.8B 모델이 직접 처리한다."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Be concise."},
        {"role": "user", "content": message},
    ]

    content = await request_completion(
        base_url=ROUTER_MODEL_URL,
        messages=messages,
        max_tokens=EXECUTOR_MAX_TOKENS,
        timeout=ROUTER_TIMEOUT_SEC * 5,
        temperature=0.7,
    )

    return ChatResponse(
        request_id=request_id,
        content=content,
        model_used=ROUTER_MODEL_NAME,
        intent=INTENT_SIMPLE,
    )


async def handle_complex(request_id: str, message: str) -> ChatResponse:
    """복잡한 요청을 14B 모델로 처리한다."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": message},
    ]

    content = await request_completion(
        base_url=EXECUTOR_MODEL_URL,
        messages=messages,
        max_tokens=EXECUTOR_MAX_TOKENS,
        timeout=EXECUTOR_TIMEOUT_SEC,
        temperature=0.7,
    )

    return ChatResponse(
        request_id=request_id,
        content=content,
        model_used=EXECUTOR_MODEL_NAME,
        intent=INTENT_COMPLEX,
    )
