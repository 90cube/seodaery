"""큐 워커. Redis에서 요청을 꺼내 라우터 → 실행기 흐름을 처리한다."""

from __future__ import annotations

import asyncio
import json
import logging

from server.domain.intent_router import classify_intent, handle_complex, handle_simple
from server.model.schemas import Intent, RequestStatus
from server.system.redis_client import dequeue_request, store_result

logger = logging.getLogger(__name__)

_running = False


async def process_one(item: dict) -> None:
    """단일 요청을 처리한다: 의도 분류 → 모델 실행 → 결과 저장."""
    request_id = item["request_id"]
    message = item["message"]

    try:
        intent = await classify_intent(message)

        if intent == Intent.SIMPLE:
            response = await handle_simple(request_id, message)
        else:
            response = await handle_complex(request_id, message)

        result = {
            "request_id": response.request_id,
            "content": response.content,
            "model_used": response.model_used,
            "intent": response.intent,
            "status": RequestStatus.COMPLETED.value,
        }
    except Exception as exc:
        logger.exception("요청 처리 실패: %s", request_id)
        result = {
            "request_id": request_id,
            "content": f"처리 중 오류 발생: {exc}",
            "model_used": "none",
            "intent": "unknown",
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
