"""디버그 API. 분류→응답 전 과정을 단계별로 반환한다."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from server.config.constants import (
    EXECUTOR_MODEL_NAME,
    EXECUTOR_MODEL_URL,
    EXECUTOR_TIMEOUT_SEC,
    LIGHT_MODEL_NAME,
    LIGHT_MODEL_URL,
    LIGHT_TIMEOUT_SEC,
    PERSONA_SYSTEM_PROMPT,
    ROUTER_SYSTEM_PROMPT,
    LIGHT_CHAT_SYSTEM_PROMPT,
    get_model_profile,
)
from server.domain.message_router import (
    classify,
    generate_chat_response,
    _strip_think,
)
from server.domain.schema_compiler import compile_tool_prompt
from server.domain.session_manager import get_session, start_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.post("/trace")
async def trace_message(
    body: dict, x_user_id: str = Header(default="anonymous"),
):
    """메시지 처리 전 과정을 추적한다. 실제 큐에 넣지 않음."""
    message = body.get("message", "")
    if not message:
        return JSONResponse(
            status_code=400, content={"error": "message required"},
        )

    steps = []

    # 1. 분류기 프롬프트
    classifier_prompt = (
        f"<|system|>\n{ROUTER_SYSTEM_PROMPT}\n"
        f"<|user|>\n{message}\n<|assistant|>\n"
    )
    steps.append({
        "step": "classifier_prompt",
        "label": "0.8B 분류 프롬프트",
        "model": LIGHT_MODEL_NAME,
        "url": f"{LIGHT_MODEL_URL}/completion",
        "content": classifier_prompt,
    })

    # 2. 분류 실행
    category = await classify(message)
    steps.append({
        "step": "classification",
        "label": "분류 결과",
        "category": category,
        "model": LIGHT_MODEL_NAME,
    })

    # 3. 라우팅 분기
    if category == "chat":
        # chat → 0.8B 즉답
        chat_system = LIGHT_CHAT_SYSTEM_PROMPT
        chat_prompt = (
            f"<|system|>\n{chat_system}\n"
            f"<|user|>\n{message}\n<|assistant|>\n"
        )
        steps.append({
            "step": "chat_prompt",
            "label": "0.8B 채팅 프롬프트",
            "model": LIGHT_MODEL_NAME,
            "url": f"{LIGHT_MODEL_URL}/completion",
            "content": chat_prompt,
        })

        reply = await generate_chat_response(message)
        steps.append({
            "step": "chat_response",
            "label": "0.8B 채팅 응답",
            "model": LIGHT_MODEL_NAME,
            "content": reply,
        })
        target_model = LIGHT_MODEL_NAME
    else:
        # read/think/tool → 9B
        profile = get_model_profile()
        system = PERSONA_SYSTEM_PROMPT
        tool_prompt = compile_tool_prompt()
        if tool_prompt:
            system += f"\n\n{tool_prompt}"

        steps.append({
            "step": "executor_system",
            "label": "9B 시스템 프롬프트",
            "model": EXECUTOR_MODEL_NAME,
            "content": system,
        })
        steps.append({
            "step": "executor_config",
            "label": "9B 모델 설정",
            "model": EXECUTOR_MODEL_NAME,
            "config": {
                "temperature": profile["temperature"],
                "max_tokens": profile["max_tokens"],
                "think_param": profile["think_param"],
                "strip_think_tags": profile["strip_think_tags"],
                "use_think": category != "read",
            },
        })
        target_model = EXECUTOR_MODEL_NAME

    return {
        "message": message,
        "category": category,
        "target_model": target_model,
        "steps": steps,
    }
