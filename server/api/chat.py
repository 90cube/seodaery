"""채팅 API 엔드포인트. 로직 없음 — 도메인 레이어 호출만."""

from __future__ import annotations

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from server.data.database import get_db, init_tables
from server.data.user_store import get_user, user_exists
from server.domain.session_manager import register_user, save_session_memories
from server.model.schemas import ChatRequest, RequestStatus
from server.system.queue_store import enqueue_request, get_queue_length, get_result

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat")
async def chat(body: dict, x_user_id: str = Header(default="anonymous")):
    """채팅 요청을 큐에 등록하고 request_id를 반환한다."""
    message = body.get("message", "")
    if not message:
        return {"error": "message is required"}, 400

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


@router.get("/queue/status")
async def queue_status():
    """현재 대기열 상태를 반환한다."""
    length = get_queue_length()
    return {"pending_count": length}


@router.get("/user/me")
async def get_me(x_user_id: str = Header(default="anonymous")):
    """유저 정보를 반환한다. 미등록이면 404."""
    conn = get_db(x_user_id)
    init_tables(conn)
    if not user_exists(conn, x_user_id):
        conn.close()
        return JSONResponse(status_code=404, content={"registered": False})
    user = get_user(conn, x_user_id)
    conn.close()
    return {"registered": True, **user}


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
