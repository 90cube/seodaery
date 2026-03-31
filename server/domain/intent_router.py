"""입력 라우팅 + 9B 응답 생성. 순수 도메인 로직."""

from __future__ import annotations

from server.config.constants import (
    EXECUTOR_MODEL_NAME,
    EXECUTOR_MODEL_URL,
    EXECUTOR_MAX_TOKENS,
    EXECUTOR_TIMEOUT_SEC,
)
from server.system.llama_client import request_completion


async def generate_response(messages: list[dict[str, str]]) -> str:
    """9B 모델로 응답을 생성한다. messages는 session_manager.build_context()의 결과."""
    content = await request_completion(
        base_url=EXECUTOR_MODEL_URL,
        messages=messages,
        max_tokens=EXECUTOR_MAX_TOKENS,
        timeout=EXECUTOR_TIMEOUT_SEC,
        temperature=0.7,
    )
    return content
