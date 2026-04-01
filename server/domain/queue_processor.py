"""큐 워커. 기본 9B 직답, 필요 시에만 검색/도구."""

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

# 검색이 필요한 신호 키워드
_SEARCH_SIGNALS = frozenset(
    ["알려", "뭐야", "뭔가", "찾아", "검색", "스킬", "정보", "어디", "목록",
     "비교", "차이", "어떻게", "방법", "설명", "패치", "업데이트", "스킨"]
)


def _needs_search(message: str) -> bool:
    """검색이 필요한지 Python으로 판단. LLM 호출 없음."""
    msg = message.strip()
    return any(s in msg for s in _SEARCH_SIGNALS)


def _needs_tools() -> bool:
    """등록된 도구가 있는지 확인. 없으면 ReAct 불필요."""
    try:
        from server.data.tool_registry import get_tools_db, init_tool_tables, get_enabled_tools
        conn = get_tools_db()
        init_tool_tables(conn)
        tools = get_enabled_tools(conn)
        conn.close()
        return len(tools) > 0
    except Exception:
        return False


async def process_one(item: dict) -> None:
    """단일 요청 처리. 60초 타임아웃."""
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
    """기본 9B 직답. 검색/도구는 필요 시에만."""
    session = get_session(user_id)
    if not session:
        session = start_session(user_id)
    add_message(user_id, "user", message)

    # L1/L2 캐시
    cache = lookup(user_id, message)
    if cache.hit and cache.response_text:
        add_message(user_id, "assistant", cache.response_text)
        return _ok_result(request_id, cache.response_text, f"cache-{cache.level}", "cached")

    # Python 분류 (0ms, LLM 호출 없음)
    search = _needs_search(message)
    tools = _needs_tools() if search else False

    if tools:
        content = await _response_with_tools(user_id, session, message)
    elif search:
        content = await _response_with_search(user_id, session, message)
    else:
        content = await _direct_response(session)

    add_message(user_id, "assistant", content)
    if content:
        save_to_cache(user_id, message, "", content)
    return _ok_result(request_id, content, EXECUTOR_MODEL_NAME, "text")


async def _direct_response(session: dict) -> str:
    """9B 직답. 페르소나 + 대화 히스토리만."""
    system = PERSONA_SYSTEM_PROMPT
    user = session.get("user")
    if user:
        system += f"\n대화 상대: {user.get('name', '?')}"
    msgs = [{"role": "system", "content": system}]
    msgs.extend(session.get("messages", [])[-6:])
    return await request_completion(
        base_url=EXECUTOR_MODEL_URL, messages=msgs,
        max_tokens=512, timeout=EXECUTOR_TIMEOUT_SEC,
    )


async def _response_with_search(user_id: str, session: dict, message: str) -> str:
    """지식 검색 + 9B 직답."""
    knowledge = await search_game_knowledge(message)
    knowledge_ptr = build_knowledge_pointer(knowledge)
    user_ptr = build_user_pointer(user_id, session.get("user"), 0)
    pointer = assemble_pointer(user_ptr, knowledge_ptr)
    msgs = build_context(user_id, schema_pointer=pointer)
    return await request_completion(
        base_url=EXECUTOR_MODEL_URL, messages=msgs,
        max_tokens=EXECUTOR_MAX_TOKENS, timeout=EXECUTOR_TIMEOUT_SEC,
    )


async def _response_with_tools(user_id: str, session: dict, message: str) -> str:
    """지식 검색 + 포인터 + ReAct."""
    knowledge = await search_game_knowledge(message)
    knowledge_ptr = build_knowledge_pointer(knowledge)
    user_ptr = build_user_pointer(user_id, session.get("user"), 0)
    pointer = assemble_pointer(user_ptr, knowledge_ptr)
    msgs = build_context(user_id, schema_pointer=pointer)
    return await run_react_loop(msgs)


def _ok_result(rid: str, content: str, model: str, itype: str) -> dict:
    return {"request_id": rid, "content": content, "model_used": model,
            "input_type": itype, "status": RequestStatus.COMPLETED.value}


def _error_result(rid: str, content: str, itype: str) -> dict:
    return {"request_id": rid, "content": content, "model_used": "none",
            "input_type": itype, "status": RequestStatus.ERROR.value}


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
