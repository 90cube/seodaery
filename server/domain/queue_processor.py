"""큐 워커. 요청을 꺼내 세션 기반으로 처리한다."""

from __future__ import annotations

import asyncio
import logging

from server.config.constants import EXECUTOR_MODEL_NAME, REGISTRATION_PROMPT
from server.data.database import get_db, init_tables
from server.data.memory_store import (
    get_important_triples,
    store_triple,
)
from server.domain.intent_router import generate_response
from server.domain.memory_extractor import (
    extract_memories,
    search_relevant_memories,
    validate_registration,
)
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
from server.system.queue_store import dequeue_request, store_result

logger = logging.getLogger(__name__)

_running = False


async def process_one(item: dict) -> None:
    """단일 요청을 처리한다."""
    request_id = item["request_id"]
    message = item["message"]
    user_id = item.get("user_id", "anonymous")

    try:
        # 최초 접속 체크
        if is_new_user(user_id):
            result = await _handle_new_user(request_id, user_id, message)
        else:
            result = await _handle_chat(request_id, user_id, message)
    except Exception as exc:
        logger.exception("요청 처리 실패: %s", request_id)
        result = {
            "request_id": request_id,
            "content": f"처리 중 오류 발생: {exc}",
            "model_used": "none",
            "input_type": "error",
            "status": RequestStatus.ERROR.value,
        }

    await store_result(request_id, result)


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
    """기존 유저: 기억 검색 → 컨텍스트 구성 → 9B 응답."""
    session = get_session(user_id)
    if not session:
        start_session(user_id)

    add_message(user_id, "user", message)

    # 0.8B로 관련 기억 검색
    conn = get_db(user_id)
    init_tables(conn)
    all_triples = get_important_triples(conn, limit=30)
    conn.close()

    triple_dicts = [
        {"subject": t[0], "predicate": t[1], "object": t[2]}
        for t in all_triples
    ]
    relevant = await search_relevant_memories(message, triple_dicts)

    # 컨텍스트 구성 → 9B 응답
    messages = build_context(user_id, relevant)
    content = await generate_response(messages)

    add_message(user_id, "assistant", content)

    return {
        "request_id": request_id,
        "content": content,
        "model_used": EXECUTOR_MODEL_NAME,
        "input_type": "text",
        "status": RequestStatus.COMPLETED.value,
    }


async def save_session_memories(user_id: str) -> int:
    """세션 종료 시 대화에서 기억을 추출하여 저장한다."""
    conversation = get_conversation_text(user_id)
    if not conversation:
        return 0

    triples = await extract_memories(conversation)
    if not triples:
        return 0

    conn = get_db(user_id)
    init_tables(conn)
    for t in triples:
        store_triple(conn, t["subject"], t["predicate"], t["object"])
    conn.close()

    end_session(user_id)
    logger.info("기억 저장 완료: %s (%d건)", user_id, len(triples))
    return len(triples)


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
