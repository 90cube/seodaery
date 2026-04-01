"""큐 워커. 요청을 꺼내 세션 기반으로 처리한다."""

from __future__ import annotations

import asyncio
import logging

from server.config.constants import (
    EXECUTOR_MODEL_NAME,
    QUEUE_TIMEOUT_SEC,
    REGISTRATION_PROMPT,
)
from server.data.database import get_db, init_tables
from server.data.memory_store import get_important_triples
from server.domain.cache_router import lookup, save_to_cache
from server.domain.pointer_builder import (
    assemble_pointer,
    build_knowledge_pointer,
    build_user_pointer,
)
from server.domain.react_loop import run_react_loop
from server.domain.knowledge_search import (
    format_knowledge_context,
    search_game_knowledge,
)
from server.domain.memory_extractor import search_relevant_memories, validate_registration
from server.domain.session_manager import (
    add_message,
    build_context,
    end_session,
    get_conversation_text,
    get_session,
    is_new_user,
    register_user,
    start_session,
)
from server.model.schemas import RequestStatus
from server.system.queue_store import dequeue_request, mark_dedup_done, store_result

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
        logger.warning("타임아웃: %s (%.0f초 초과)", request_id, QUEUE_TIMEOUT_SEC)
        result = {
            "request_id": request_id,
            "content": f"처리 시간이 {int(QUEUE_TIMEOUT_SEC)}초를 초과하여 중단되었습니다.",
            "model_used": "none",
            "input_type": "timeout",
            "status": RequestStatus.ERROR.value,
        }
    except Exception as exc:
        logger.exception("요청 처리 실패: %s", request_id)
        result = {
            "request_id": request_id,
            "content": f"처리 중 오류 발생: {exc}",
            "model_used": "none",
            "input_type": "error",
            "status": RequestStatus.ERROR.value,
        }

    result["_dedup_key"] = dedup_key
    await store_result(request_id, result)


async def _dispatch(request_id: str, user_id: str, message: str) -> dict:
    """최초 접속/일반 대화를 분기한다."""
    if is_new_user(user_id):
        return await _handle_new_user(request_id, user_id, message)
    return await _handle_chat(request_id, user_id, message)


async def _handle_new_user(
    request_id: str, user_id: str, message: str
) -> dict:
    """신규 유저: 등록 정보 검증 후 등록 또는 안내."""
    parsed = await validate_registration(message)

    if parsed and parsed.get("name"):
        register_user(
            user_id,
            parsed["name"],
            parsed.get("position", ""),
            parsed.get("role", ""),
        )
        start_session(user_id)
        add_message(user_id, "user", message)

        welcome = (
            f"{parsed['name']}님, 반갑습니다! "
            f"앞으로 잘 부탁드리겠습니다. 무엇을 도와드릴까요?"
        )
        add_message(user_id, "assistant", welcome)

        return {
            "request_id": request_id,
            "content": welcome,
            "model_used": "system",
            "input_type": "registration",
            "status": RequestStatus.COMPLETED.value,
        }

    return {
        "request_id": request_id,
        "content": REGISTRATION_PROMPT,
        "model_used": "system",
        "input_type": "registration",
        "status": RequestStatus.COMPLETED.value,
    }


async def _handle_chat(
    request_id: str, user_id: str, message: str
) -> dict:
    """기존 유저: 캐시 조회 → 포인터 구성 → 9B 응답 → 캐시 저장."""
    session = get_session(user_id)
    if not session:
        session = start_session(user_id)

    add_message(user_id, "user", message)

    # L1/L2 캐시 조회
    cache_hit = lookup(user_id, message)
    if cache_hit.hit and cache_hit.response_text:
        add_message(user_id, "assistant", cache_hit.response_text)
        return {
            "request_id": request_id,
            "content": cache_hit.response_text,
            "model_used": f"cache-{cache_hit.level}",
            "input_type": "cached",
            "status": RequestStatus.COMPLETED.value,
        }

    # 스키마 포인터 구성
    conn = get_db(user_id)
    init_tables(conn)
    triple_count = len(get_important_triples(conn, limit=30))
    conn.close()

    user_ptr = build_user_pointer(
        user_id,
        session.get("user"),
        triple_count,
    )

    knowledge_results = await search_game_knowledge(message)
    knowledge_ptr = build_knowledge_pointer(knowledge_results)

    pointer = assemble_pointer(user_ptr, knowledge_ptr)

    # 포인터 기반 컨텍스트 → ReAct 루프
    messages = build_context(user_id, schema_pointer=pointer)
    content = await run_react_loop(messages)

    add_message(user_id, "assistant", content)

    # 캐시 저장 (다음번 동일 질문 시 L1/L2 히트)
    save_to_cache(user_id, message, pointer, content)

    return {
        "request_id": request_id,
        "content": content,
        "model_used": EXECUTOR_MODEL_NAME,
        "input_type": "text",
        "status": RequestStatus.COMPLETED.value,
    }


async def run_worker() -> None:
    """큐 워커 루프."""
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
    """워커 루프를 정지시킨다."""
    global _running
    _running = False
