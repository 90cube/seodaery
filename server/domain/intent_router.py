"""0.8B 입력 타입 분류 + 9B 응답 생성. 순수 도메인 로직."""

from __future__ import annotations

from server.config.constants import (
    EXECUTOR_MODEL_NAME,
    EXECUTOR_MODEL_URL,
    EXECUTOR_MAX_TOKENS,
    EXECUTOR_SYSTEM_PROMPT,
    EXECUTOR_TIMEOUT_SEC,
    INPUT_TYPE_CLASSIFICATION_PROMPT,
    INPUT_TYPE_IMAGE,
    INPUT_TYPE_TEXT,
    INPUT_TYPE_WORKER,
    ROUTER_MAX_TOKENS,
    ROUTER_MODEL_URL,
    ROUTER_TIMEOUT_SEC,
)
from server.model.schemas import ChatResponse, InputType
from server.system.llama_client import request_completion


async def classify_input_type(message: str) -> InputType:
    """0.8B 모델로 입력 타입을 분류한다. (text / image / worker)"""
    messages = [
        {"role": "system", "content": INPUT_TYPE_CLASSIFICATION_PROMPT},
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
    if INPUT_TYPE_IMAGE in normalized:
        return InputType.IMAGE
    if INPUT_TYPE_WORKER in normalized:
        return InputType.WORKER
    return InputType.TEXT


async def handle_text(request_id: str, message: str) -> ChatResponse:
    """텍스트 요청 — 9B 모델이 CoT로 응답한다."""
    messages = [
        {"role": "system", "content": EXECUTOR_SYSTEM_PROMPT},
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
        input_type=InputType.TEXT.value,
    )


async def handle_image(request_id: str, message: str) -> ChatResponse:
    """이미지 요청 — 향후 멀티모달 처리 확장 지점."""
    return ChatResponse(
        request_id=request_id,
        content="[이미지 처리는 아직 미구현입니다]",
        model_used=EXECUTOR_MODEL_NAME,
        input_type=InputType.IMAGE.value,
    )


async def handle_worker(request_id: str, message: str) -> ChatResponse:
    """워커 요청 — 향후 자동화 태스크 확장 지점."""
    return ChatResponse(
        request_id=request_id,
        content="[워커 처리는 아직 미구현입니다]",
        model_used="system",
        input_type=InputType.WORKER.value,
    )
