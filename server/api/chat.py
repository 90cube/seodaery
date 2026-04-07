"""채팅 API 엔드포인트. 로직 없음 — 도메인 레이어 호출만."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from server.data.database import get_db, init_tables
from server.data.user_store import get_user, user_exists
from server.domain.session_manager import register_user, save_session_memories
from server.model.schemas import ChatRequest, RequestStatus
from server.system.queue_store import enqueue_request, get_queue_length, get_result

router = APIRouter(prefix="/api", tags=["chat"])

_SYNC_POLL_INTERVAL = 0.5
_SYNC_TIMEOUT = 120.0


@router.post("/chat")
async def chat(body: dict, x_user_id: str = Header(default="anonymous")):
    """채팅 요청을 큐에 등록하고 request_id를 반환한다."""
    message = body.get("message", "")
    if not message:
        return JSONResponse(status_code=400, content={"error": "message is required"})

    req = ChatRequest(message=message)
    queue_len = await enqueue_request(
        req.request_id, req.message, user_id=x_user_id
    )

    if queue_len is None:
        return {"error": "동일한 요청이 이미 처리 중입니다.", "duplicate": True}

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


@router.post("/chat/sync")
async def chat_sync(body: dict, x_user_id: str = Header(default="n8n")):
    """동기 채팅. 큐에 넣고 결과 나올 때까지 대기 후 반환한다.

    n8n 등 외부 자동화 도구용. HTTP Request 노드 하나로 사용 가능.
    """
    message = body.get("message", "")
    if not message:
        return JSONResponse(status_code=400, content={"error": "message is required"})

    req = ChatRequest(message=message)
    queue_len = await enqueue_request(
        req.request_id, req.message, user_id=x_user_id,
    )
    if queue_len is None:
        return JSONResponse(status_code=409, content={"error": "duplicate request"})

    elapsed = 0.0
    while elapsed < _SYNC_TIMEOUT:
        result = get_result(req.request_id)
        if result is not None:
            return {
                "content": result.get("content", ""),
                "model_used": result.get("model_used", ""),
                "status": result.get("status", ""),
                "request_id": req.request_id,
            }
        await asyncio.sleep(_SYNC_POLL_INTERVAL)
        elapsed += _SYNC_POLL_INTERVAL

    return JSONResponse(status_code=504, content={"error": "timeout"})


@router.get("/queue/status")
async def queue_status():
    """현재 대기열 상태를 반환한다."""
    length = get_queue_length()
    return {"pending_count": length}


@router.get("/user/me")
async def get_me(x_user_id: str = Header(default="anonymous")):
    """유저 정보를 반환한다. 미등록이면 404."""
    conn = get_db(x_user_id)
    try:
        init_tables(conn)
        if not user_exists(conn, x_user_id):
            return JSONResponse(status_code=404, content={"registered": False})
        user = get_user(conn, x_user_id)
        return {"registered": True, **user}
    finally:
        conn.close()


@router.post("/register")
async def register_api(body: dict, x_user_id: str = Header(default="anonymous")):
    """유저를 등록/업데이트한다. LLM 파싱 없이 직접 저장."""
    name = body.get("name", "")
    if not name:
        return JSONResponse(status_code=400, content={"error": "name is required"})
    position = body.get("position", "")
    role = body.get("role", "")
    register_user(x_user_id, name, position, role)
    return {"registered": True, "user_id": x_user_id, "name": name}


@router.post("/session/end")
async def end_session(x_user_id: str = Header(default="anonymous")):
    """세션을 종료하고 기억을 저장한다."""
    count = await save_session_memories(x_user_id)
    return {"user_id": x_user_id, "memories_saved": count}
