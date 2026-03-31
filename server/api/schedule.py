"""스케줄 REST API 엔드포인트. 로직 없음 — 도메인 레이어 호출만."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from server.data.run_log_store import get_schedule_logs, init_run_log_table
from server.data.schedule_store import (
    get_schedule,
    get_schedule_db,
    init_schedule_tables,
    toggle_schedule,
)
from server.domain.schedule_manager import (
    cancel_schedule,
    get_my_schedules,
    register_schedule,
)

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


# ── 스케줄 생성 ──────────────────────────────────────────


@router.post("")
async def create(body: dict, x_user_id: str = Header(default="anonymous")):
    """새 스케줄을 등록한다."""
    name = body.get("name")
    cron_expr = body.get("cron_expr")

    if not name or not cron_expr:
        raise HTTPException(status_code=400, detail="name, cron_expr 필수")

    schedule_id = register_schedule(
        user_id=x_user_id,
        name=name,
        cron_expr=cron_expr,
        tool_id=body.get("tool_id"),
        params=body.get("params", {}),
        description=body.get("description", ""),
        max_retries=body.get("max_retries", 3),
        retry_interval=body.get("retry_interval", 60),
    )
    return {"schedule_id": schedule_id}


# ── 내 스케줄 목록 ───────────────────────────────────────


@router.get("")
async def list_schedules(x_user_id: str = Header(default="anonymous")):
    """사용자의 스케줄 목록을 반환한다."""
    schedules = get_my_schedules(x_user_id)
    return {"schedules": schedules, "count": len(schedules)}


# ── 단건 조회 ────────────────────────────────────────────


@router.get("/{schedule_id}")
async def get_one(schedule_id: str):
    """스케줄 한 건을 조회한다."""
    conn = get_schedule_db()
    try:
        init_schedule_tables(conn)
        schedule = get_schedule(conn, schedule_id)
    finally:
        conn.close()

    if not schedule:
        raise HTTPException(status_code=404, detail="스케줄 미존재")
    return schedule


# ── 삭제 ─────────────────────────────────────────────────


@router.delete("/{schedule_id}")
async def delete(schedule_id: str):
    """스케줄을 삭제한다."""
    deleted = cancel_schedule(schedule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="스케줄 미존재")
    return {"deleted": True}


# ── 활성/비활성 전환 ─────────────────────────────────────


@router.post("/{schedule_id}/toggle")
async def toggle(schedule_id: str, body: dict):
    """스케줄 활성 상태를 전환한다."""
    enabled = body.get("enabled")
    if enabled is None:
        raise HTTPException(status_code=400, detail="enabled 필수")

    conn = get_schedule_db()
    try:
        init_schedule_tables(conn)
        updated = toggle_schedule(conn, schedule_id, bool(enabled))
    finally:
        conn.close()

    if not updated:
        raise HTTPException(status_code=404, detail="스케줄 미존재")
    return {"schedule_id": schedule_id, "enabled": bool(enabled)}


# ── 실행 로그 ────────────────────────────────────────────


@router.get("/{schedule_id}/logs")
async def logs(schedule_id: str, limit: int = 20):
    """스케줄의 실행 로그를 반환한다."""
    conn = get_schedule_db()
    try:
        init_schedule_tables(conn)
        init_run_log_table(conn)
        entries = get_schedule_logs(conn, schedule_id, limit=limit)
    finally:
        conn.close()

    return {"logs": entries, "count": len(entries)}
