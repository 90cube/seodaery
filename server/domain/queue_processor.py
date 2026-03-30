"""큐 워커. 인메모리 큐에서 요청을 꺼내 분류 → 실행 흐름을 처리한다."""

from __future__ import annotations

import asyncio
import logging

from server.domain.intent_router import (
    classify_input_type,
    handle_image,
    handle_text,
    handle_worker,
)
from server.model.schemas import InputType, RequestStatus
from server.system.queue_store import dequeue_request, store_result

logger = logging.getLogger(__name__)

_running = False


async def process_one(item: dict) -> None:
    """단일 요청을 처리한다: 타입 분류 → 핸들러 실행 → 결과 저장."""
    request_id = item["request_id"]
    message = item["message"]

    try:
        input_type = await classify_input_type(message)
        logger.info("분류 완료: %s → %s", request_id, input_type.value)

        if input_type == InputType.IMAGE:
            response = await handle_image(request_id, message)
        elif input_type == InputType.WORKER:
            response = await handle_worker(request_id, message)
        else:
            response = await handle_text(request_id, message)

        result = {
            "request_id": response.request_id,
            "content": response.content,
            "model_used": response.model_used,
            "input_type": response.input_type,
            "status": RequestStatus.COMPLETED.value,
        }
    except Exception as exc:
        logger.exception("요청 처리 실패: %s", request_id)
        result = {
            "request_id": request_id,
            "content": f"처리 중 오류 발생: {exc}",
            "model_used": "none",
            "input_type": "unknown",
            "status": RequestStatus.ERROR.value,
        }

    await store_result(request_id, result)


async def run_worker() -> None:
    """큐 워커 루프. 서버 시작 시 백그라운드 태스크로 실행된다."""
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
