"""ReAct 루프. 생각 → 행동 → 관찰을 반복하여 도구 기반 추론을 수행한다."""

from __future__ import annotations

import json
import logging
import re

from server.config.constants import (
    EXECUTOR_MAX_TOKENS,
    EXECUTOR_MODEL_URL,
    EXECUTOR_TIMEOUT_SEC,
)
from server.domain.schema_compiler import compile_tool_prompt
from server.domain.tool_executor import execute_tool_call
from server.system.llama_client import request_completion

logger = logging.getLogger(__name__)

MAX_REACT_ITERATIONS = 5
TOOL_CALL_PATTERN = re.compile(r'\{[^{}]*"tool"\s*:.*?\}', re.DOTALL)

REACT_SYSTEM_SUFFIX = (
    "\n\n도구를 사용하려면 JSON을 출력하세요: "
    '{"tool": "tool_id", "params": {...}}\n'
    "도구 없이 답변하려면 일반 텍스트로 답변하세요.\n"
    "도구 실행 결과가 돌아오면 그것을 바탕으로 최종 답변을 하세요."
)


async def run_react_loop(messages: list[dict]) -> str:
    """사용자 메시지를 받아 ReAct 루프를 실행하고 최종 응답을 반환한다.

    도구가 등록되어 있지 않으면 단순 완성 요청으로 대체한다.
    최대 ``MAX_REACT_ITERATIONS`` 회 반복 후 강제로 최종 답변을 요청한다.
    """
    tool_prompt = compile_tool_prompt()

    if not tool_prompt:
        return await _plain_completion(messages)

    working_messages = _inject_tool_context(messages, tool_prompt)

    for iteration in range(1, MAX_REACT_ITERATIONS + 1):
        logger.info("ReAct 반복 %d/%d", iteration, MAX_REACT_ITERATIONS)

        response = await _plain_completion(working_messages)
        tool_call_json = _extract_tool_call(response)

        if tool_call_json is None:
            return response

        logger.info("도구 호출 감지: %s", tool_call_json[:100])
        result = await execute_tool_call(tool_call_json)

        working_messages.append({"role": "assistant", "content": response})
        observation = _format_observation(result)
        working_messages.append({"role": "user", "content": observation})

    return await _force_final_answer(working_messages)


# ── 내부 헬퍼 ───────────────────────────────────────────────


async def _plain_completion(messages: list[dict]) -> str:
    """LLM 완성 요청을 전송한다."""
    return await request_completion(
        base_url=EXECUTOR_MODEL_URL,
        messages=messages,
        max_tokens=EXECUTOR_MAX_TOKENS,
        timeout=EXECUTOR_TIMEOUT_SEC,
    )


async def _force_final_answer(messages: list[dict]) -> str:
    """반복 횟수 초과 시 최종 답변을 강제로 요청한다."""
    messages.append({
        "role": "user",
        "content": "반복 횟수를 초과했습니다. 지금까지의 정보로 최종 답변을 해주세요.",
    })
    return await _plain_completion(messages)


def _inject_tool_context(
    messages: list[dict],
    tool_prompt: str,
) -> list[dict]:
    """시스템 메시지에 도구 설명과 사용 안내를 주입한다."""
    result: list[dict] = []
    for msg in messages:
        if msg["role"] == "system":
            result.append({
                "role": "system",
                "content": msg["content"] + "\n\n" + tool_prompt + REACT_SYSTEM_SUFFIX,
            })
        else:
            result.append(msg.copy())
    return result


def _extract_tool_call(response: str) -> str | None:
    """응답 텍스트에서 도구 호출 JSON을 추출한다. 없으면 None을 반환한다."""
    match = TOOL_CALL_PATTERN.search(response)
    if match is None:
        return None

    candidate = match.group(0)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None

    if "tool" in parsed:
        return candidate
    return None


def _format_observation(result: dict) -> str:
    """도구 실행 결과를 관찰 메시지로 포맷한다."""
    if result["success"]:
        payload = json.dumps(
            result["result"],
            ensure_ascii=False,
            default=str,
        )
        return f"[도구 실행 결과]\n{payload}"
    return f"[도구 실행 실패]\n{result['error']}"
