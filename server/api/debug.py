"""디버그 API. 시스템 프롬프트와 모델 설정을 확인한다."""

from __future__ import annotations

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from server.config.constants import (
    EXECUTOR_MODEL_NAME,
    PERSONA_SYSTEM_PROMPT,
    get_model_profile,
)
from server.domain.schema_compiler import compile_tool_prompt

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.post("/trace")
async def trace_message(
    body: dict, x_user_id: str = Header(default="anonymous"),
):
    """시스템 프롬프트와 모델 설정을 확인한다."""
    message = body.get("message", "")
    if not message:
        return JSONResponse(
            status_code=400, content={"error": "message required"},
        )

    profile = get_model_profile()
    system = PERSONA_SYSTEM_PROMPT
    tool_prompt = compile_tool_prompt()
    if tool_prompt:
        system += f"\n\n{tool_prompt}"

    return {
        "message": message,
        "model": EXECUTOR_MODEL_NAME,
        "system_prompt": system,
        "config": {
            "temperature": profile["temperature"],
            "max_tokens": profile["max_tokens"],
            "think_param": profile["think_param"],
            "strip_think_tags": profile["strip_think_tags"],
        },
    }
