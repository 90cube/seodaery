"""큐 워커. 복잡도 기반 3경로 분기로 처리한다."""

from __future__ import annotations

import asyncio
import logging

from server.config.constants import (
    EXECUTOR_MAX_TOKENS,
    EXECUTOR_MODEL_NAME,
    EXECUTOR_MODEL_URL,
    EXECUTOR_TIMEOUT_SEC,
    PERSONA_SYSTEM_PROMPT,
    QUEUE_TIMEOUT_SEC,
    REGISTRATION_PROMPT,
)
from server.domain.cache_router import lookup, save_to_cache
from server.domain.complexity_scorer import score_complexity
from server.domain.knowledge_search import search_game_knowledge
from server.domain.memory_extractor import validate_registration
from server.domain.pointer_builder import (
    assemble_pointer,
    build_knowledge_pointer,
    build_user_pointer,
)
from server.domain.react_loop import run_react_loop
from server.domain.session_manager import (
    add_message,
    build_context,
    get_session,
    is_new_user,
    register_user,
    start_session,
)
from server.model.schemas import RequestStatus
from server.system.llama_client import request_completion
from server.system.queue_store import dequeue_request, store_result

logger = logging.getLogger(__name__)

_running = False


async def process_one(item: dict) -> None:
    """단일 요청을 처리한다. 60초 타임아웃 적용."""
    request_id = item["request_id"]
    message = item["message"]
    user_id = item.get("user_id", "anonymous")
    dedup_key = item.get("dedup_key", "")

    try:
        coro = _dispatch(request_id, user_id, message)
        result = await asyncio.wait_for(coro, timeout=QUEUE_TIMEOUT_SEC)
    except asyncio.TimeoutError:
        logger.warning("타임아웃: %s (%.0f초)", request_id, QUEUE_TIMEOUT_SEC)
        result = _error_result(request_id, "처리 시간 초과", "timeout")
    except Exception as exc:
        logger.exception("요청 처리 실패: %s", request_id)
        result = _error_result(request_id, f"오류: {exc}", "error")

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
        return _ok_result(request_id, welcome, "system", "registration")
    return _ok_result(request_id, REGISTRATION_PROMPT, "system", "registration")


async def _handle_chat(request_id: str, user_id: str, message: str) -> dict:
    """복잡도 기반 3경로 분기."""
    session = get_session(user_id)
    if not session:
        session = start_session(user_id)
    add_message(user_id, "user", message)

    # L1/L2 캐시
    cache = lookup(user_id, message)
    if cache.hit and cache.response_text:
        add_message(user_id, "assistant", cache.response_text)
        return _ok_result(request_id, cache.response_text, f"cache-{cache.level}", "cached")

    # 복잡도 판정 (0.8B 라우터, ~0.5초)
    complexity = await score_complexity(message)
    logger.info("복잡도: %d — %s", complexity, message[:30])

    if complexity <= 2:
        content = await _direct_response(session, message)
    elif complexity <= 3:
        content = await _standard_response(user_id, session, message)
    else:
        content = await _full_response(user_id, session, message)

    add_message(user_id, "assistant", content)
    save_to_cache(user_id, message, "", content)
    return _ok_result(request_id, content, EXECUTOR_MODEL_NAME, "text")


async def _direct_response(session: dict, message: str) -> str:
    """경량 경로: 9B에 페르소나 + 대화 히스토리만. 검색/도구 없음."""
    system = PERSONA_SYSTEM_PROMPT
    user = session.get("user")
    if user:
        system += f"\n대화 상대: {user.get('name', '?')}"

    messages = [{"role": "system", "content": system}]
    messages.extend(session.get("messages", [])[-6:])

    return await request_completion(
        base_url=EXECUTOR_MODEL_URL,
        messages=messages,
        max_tokens=512,
        timeout=EXECUTOR_TIMEOUT_SEC,
    )


async def _standard_response(user_id: str, session: dict, message: str) -> str:
    """표준 경로: 지식 검색 + 포인터 → 9B 직답."""
    knowledge = await search_game_knowledge(message)
    knowledge_ptr = build_knowledge_pointer(knowledge)
    user_ptr = build_user_pointer(user_id, session.get("user"), 0)
    pointer = assemble_pointer(user_ptr, knowledge_ptr)

    messages = build_context(user_id, schema_pointer=pointer)
    return await request_completion(
        base_url=EXECUTOR_MODEL_URL,
        messages=messages,
        max_tokens=EXECUTOR_MAX_TOKENS,
        timeout=EXECUTOR_TIMEOUT_SEC,
    )


async def _full_response(user_id: str, session: dict, message: str) -> str:
    """풀 경로: 병렬 검색 + 포인터 + ReAct."""
    knowledge = await search_game_knowledge(message)
    knowledge_ptr = build_knowledge_pointer(knowledge)
    user_ptr = build_user_pointer(user_id, session.get("user"), 0)
    pointer = assemble_pointer(user_ptr, knowledge_ptr)

    messages = build_context(user_id, schema_pointer=pointer)
    return await run_react_loop(messages)


def _ok_result(request_id: str, content: str, model: str, input_type: str) -> dict:
    return {
        "request_id": request_id,
        "content": content,
        "model_used": model,
        "input_type": input_type,
        "status": RequestStatus.COMPLETED.value,
    }


def _error_result(request_id: str, content: str, input_type: str) -> dict:
    return {
        "request_id": request_id,
        "content": content,
        "model_used": "none",
        "input_type": input_type,
        "status": RequestStatus.ERROR.value,
    }


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
