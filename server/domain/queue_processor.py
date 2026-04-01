"""큐 워커. 모든 대화는 9B 직답. 0.8B는 백그라운드 작업만."""

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
from server.domain.memory_extractor import validate_registration
from server.domain.session_manager import (
    add_message,
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
    """모든 대화 → 9B 직답. 0.8B는 여기서 호출하지 않는다."""
    session = get_session(user_id)
    if not session:
        session = start_session(user_id)
    add_message(user_id, "user", message)

    # 9B에게 보낼 메시지 구성: 페르소나 + 유저 정보 + 대화 히스토리
    system = PERSONA_SYSTEM_PROMPT
    user_info = session.get("user")
    if user_info:
        system += f"\n대화 상대: {user_info.get('name', '?')} ({user_info.get('position', '')}, {user_info.get('role', '')})"

    messages = [{"role": "system", "content": system}]
    messages.extend(session.get("messages", [])[-10:])

    # 9B 직답
    content = await request_completion(
        base_url=EXECUTOR_MODEL_URL,
        messages=messages,
        max_tokens=EXECUTOR_MAX_TOKENS,
        timeout=EXECUTOR_TIMEOUT_SEC,
    )

    add_message(user_id, "assistant", content)
    return _ok(request_id, content, EXECUTOR_MODEL_NAME)


def _ok(rid: str, content: str, model: str) -> dict:
    return {
        "request_id": rid,
        "content": content,
        "model_used": model,
        "status": RequestStatus.COMPLETED.value,
    }


def _error(rid: str, content: str) -> dict:
    return {
        "request_id": rid,
        "content": content,
        "model_used": "none",
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
