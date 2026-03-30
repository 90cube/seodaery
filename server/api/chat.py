"""채팅 API 엔드포인트. 로직 없음 — 도메인 레이어 호출만."""

from __future__ import annotations

import asyncio
from dataclasses import asdict

from fastapi import APIRouter

from server.model.schemas import ChatRequest, RequestStatus
from server.system.queue_store import enqueue_request, get_queue_length, get_result

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat(body: dict):
    """채팅 요청을 큐에 등록하고 request_id를 반환한다."""
    message = body.get("message", "")
    if not message:
        return {"error": "message is required"}, 400

    req = ChatRequest(message=message)
    queue_len = await enqueue_request(req.request_id, req.message)

    return {
        "request_id": req.request_id,
        "status": RequestStatus.QUEUED.value,
        "position": queue_len,
    }


@router.get("/chat/{request_id}")
async def get_chat_result(request_id: str):
    """처리 결과를 폴링한다."""
    result = get_result(request_id)
    if result is None:
        queue_len = get_queue_length()
        return {
            "request_id": request_id,
            "status": RequestStatus.PROCESSING.value,
            "pending_count": queue_len,
        }
    return result


@router.get("/queue/status")
async def queue_status():
    """현재 대기열 상태를 반환한다."""
    length = get_queue_length()
    return {"pending_count": length}
