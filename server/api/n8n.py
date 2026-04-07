"""n8n 연동 API. 도구 직접 호출 + LLM 경유 동기 채팅."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from server.domain.tool_executor import get_executor, list_registered
from server.model.schemas import ChatRequest
from server.system.queue_store import enqueue_request, get_result

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/n8n", tags=["n8n"])

_SYNC_POLL_INTERVAL = 0.5
_SYNC_TIMEOUT = 120.0


@router.post("/tool")
async def call_tool(
    body: dict,
    x_n8n_action: str = Header(..., alias="X-N8N-Action"),
    x_user_id: str = Header(default="n8n"),
):
    """도구를 직접 호출한다. LLM을 거치지 않음.

    Headers:
        X-N8N-Action: 도구 ID (list_schedules, create_schedule 등)
        X-User-Id: 유저 식별자 (기본 n8n)

    Body:
        도구 파라미터 (category, patch_id 등)
    """
    executor = get_executor(x_n8n_action)
    if executor is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": f"도구 '{x_n8n_action}' 없음",
                "available": list_registered(),
            },
        )

    try:
        result = await executor(**body, user_id=x_user_id)
        return result
    except Exception as exc:
        logger.exception("n8n 도구 실행 실패: %s", x_n8n_action)
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )


@router.post("/chat")
async def chat_sync(
    body: dict,
    x_user_id: str = Header(default="n8n"),
):
    """LLM 경유 동기 채팅. 큐에 넣고 결과 대기 후 반환."""
    message = body.get("message", "")
    if not message:
        return JSONResponse(
            status_code=400, content={"error": "message required"},
        )

    req = ChatRequest(message=message)
    queue_len = await enqueue_request(
        req.request_id, req.message, user_id=x_user_id,
    )
    if queue_len is None:
        return JSONResponse(
            status_code=409, content={"error": "duplicate"},
        )

    elapsed = 0.0
    while elapsed < _SYNC_TIMEOUT:
        result = get_result(req.request_id)
        if result is not None:
            return {
                "content": result.get("content", ""),
                "model_used": result.get("model_used", ""),
                "status": result.get("status", ""),
            }
        await asyncio.sleep(_SYNC_POLL_INTERVAL)
        elapsed += _SYNC_POLL_INTERVAL

    return JSONResponse(status_code=504, content={"error": "timeout"})


@router.get("/tools")
async def list_tools():
    """사용 가능한 도구 목록을 반환한다."""
    return {"tools": list_registered()}
