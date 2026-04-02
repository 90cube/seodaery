"""큐 워커. 모든 대화는 9B 직답. 9B가 도구를 요청하면 Python이 실행하고 돌려준다."""

from __future__ import annotations

import asyncio
import json
import logging
import re

from server.config.constants import (
    EXECUTOR_MODEL_NAME,
    EXECUTOR_MODEL_URL,
    EXECUTOR_TIMEOUT_SEC,
    PERSONA_SYSTEM_PROMPT,
    QUEUE_TIMEOUT_SEC,
    REGISTRATION_PROMPT,
    get_model_profile,
)
from server.domain.memory_extractor import validate_registration
from server.domain.schema_compiler import compile_tool_prompt
from server.domain.session_manager import (
    add_message,
    get_session,
    is_new_user,
    register_user,
    start_session,
)
from server.domain.tool_executor import execute_tool_call
from server.model.schemas import RequestStatus
from server.system.llama_client import request_completion
from server.system.queue_store import dequeue_request, store_result

logger = logging.getLogger(__name__)

_running = False
_TOOL_PATTERN = re.compile(r'\{[^{}]*"tool"\s*:.*?\}', re.DOTALL)
_MAX_TOOL_ROUNDS = 5


async def process_one(item: dict) -> None:
    request_id = item["request_id"]
    message = item["message"]
    user_id = item.get("user_id", "anonymous")
    dedup_key = item.get("dedup_key", "")

    try:
        coro = _dispatch(request_id, user_id, message)
        result = await asyncio.wait_for(coro, timeout=QUEUE_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        result = _error(request_id, "처리 시간 초과")
    except Exception as exc:
        logger.exception("요청 처리 실패: %s", request_id)
        result = _error(request_id, f"오류: {exc}")

    result["_dedup_key"] = dedup_key
    await store_result(request_id, result)


async def _dispatch(request_id: str, user_id: str, message: str) -> dict:
    if is_new_user(user_id):
        return await _handle_new_user(request_id, user_id, message)
    return await _handle_chat(request_id, user_id, message)


async def _handle_new_user(request_id: str, user_id: str, message: str) -> dict:
    parsed = await validate_registration(message)
    if parsed and parsed.get("name"):
        register_user(user_id, parsed["name"], parsed.get("position", ""), parsed.get("role", ""))
        start_session(user_id)
        add_message(user_id, "user", message)
        welcome = f"{parsed['name']}님, 반갑습니다! 무엇을 도와드릴까요?"
        add_message(user_id, "assistant", welcome)
        return _ok(request_id, welcome, "system")
    return _ok(request_id, REGISTRATION_PROMPT, "system")


async def _handle_chat(request_id: str, user_id: str, message: str) -> dict:
    """모든 대화 → 9B. 9B가 도구를 요청하면 실행 후 돌려준다."""
    session = get_session(user_id)
    if not session:
        session = start_session(user_id)
    add_message(user_id, "user", message)

    # 시스템 프롬프트: 페르소나 + 유저 정보 + (도구가 있으면) 도구 목록
    system = PERSONA_SYSTEM_PROMPT
    user_info = session.get("user")
    if user_info:
        system += f"\n대화 상대: {user_info.get('name', '?')} ({user_info.get('position', '')}, {user_info.get('role', '')})"

    tool_prompt = compile_tool_prompt()
    if tool_prompt:
        system += (
            f"\n\n{tool_prompt}"
            '\n\n도구가 필요하면 {"tool": "id", "params": {...}} JSON을 출력하세요.'
            "\n필요 없으면 바로 답변하세요."
        )

    messages = [{"role": "system", "content": system}]
    messages.extend(session.get("messages", [])[-10:])

    # 9B 응답 → 도구 호출이면 실행 후 재응답 (최대 5회)
    content = await _generate_with_tools(messages)

    add_message(user_id, "assistant", content)
    return _ok(request_id, content, EXECUTOR_MODEL_NAME)


async def _generate_with_tools(messages: list[dict]) -> str:
    """응답을 생성하고, 도구 호출이 있으면 실행 후 재생성한다."""
    profile = get_model_profile()
    for round_num in range(1, _MAX_TOOL_ROUNDS + 1):
        response = await request_completion(
            base_url=EXECUTOR_MODEL_URL,
            messages=messages,
            max_tokens=profile["max_tokens"],
            timeout=EXECUTOR_TIMEOUT_SEC,
            temperature=profile["temperature"],
            think_param=profile["think_param"],
            strip_think=profile["strip_think_tags"],
        )

        # 도구 호출 JSON 감지
        tool_json = _extract_tool_call(response)
        if tool_json is None:
            return response  # 도구 없음 → 최종 응답

        # 도구 실행
        logger.info("9B 도구 요청 (라운드 %d): %s", round_num, tool_json[:80])
        result = await execute_tool_call(tool_json)

        # 결과를 대화에 추가하고 9B에게 재응답 요청
        messages.append({"role": "assistant", "content": response})
        if result["success"]:
            obs = f"[도구 결과]\n{json.dumps(result['result'], ensure_ascii=False, default=str)}"
        else:
            obs = f"[도구 실패]\n{result['error']}"
        messages.append({"role": "user", "content": obs})

    # 최대 라운드 초과 → 강제 최종 답변 요청
    messages.append({"role": "user", "content": "도구 호출 횟수를 초과했습니다. 최종 답변을 해주세요."})
    return await request_completion(
        base_url=EXECUTOR_MODEL_URL,
        messages=messages,
        max_tokens=profile["max_tokens"],
        timeout=EXECUTOR_TIMEOUT_SEC,
        temperature=profile["temperature"],
        think_param=profile["think_param"],
        strip_think=profile["strip_think_tags"],
    )


def _extract_tool_call(response: str) -> str | None:
    """9B 응답에서 도구 호출 JSON을 추출한다."""
    match = _TOOL_PATTERN.search(response)
    if match is None:
        return None
    try:
        parsed = json.loads(match.group(0))
        if "tool" in parsed:
            return match.group(0)
    except json.JSONDecodeError as exc:
        logger.debug("도구 JSON 파싱 실패: %s (raw: %.200s)", exc, match.group(0))
    return None


def _ok(rid: str, content: str, model: str) -> dict:
    return {"request_id": rid, "content": content,
            "model_used": model, "status": RequestStatus.COMPLETED.value}


def _error(rid: str, content: str) -> dict:
    return {"request_id": rid, "content": content,
            "model_used": "none", "status": RequestStatus.ERROR.value}


async def run_worker() -> None:
    global _running
    _running = True
    logger.info("큐 워커 시작")
    while _running:
        item = await dequeue_request()
        if item is None:
            continue
        await process_one(item)
    logger.info("큐 워커 종료")


def stop_worker() -> None:
    global _running
    _running = False
