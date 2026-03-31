"""스케줄 등록·실행·복원 도메인 로직.

외부 프레임워크 직접 호출 금지 — store/system 레이어만 사용한다.
"""

import asyncio
import json
import logging
import uuid

from server.data.run_log_store import (
    create_log,
    init_run_log_table,
    update_log,
)
from server.data.schedule_store import (
    create_schedule,
    delete_schedule,
    get_enabled_schedules,
    get_schedule,
    get_schedule_db,
    get_user_schedules,
    init_schedule_tables,
    toggle_schedule,
)
from server.domain.tool_executor import execute_tool_call
from server.system.scheduler import add_cron_job, is_available, remove_job

logger = logging.getLogger(__name__)


# ── 스케줄 등록 ──────────────────────────────────────────


def register_schedule(
    user_id: str,
    name: str,
    cron_expr: str,
    tool_id: str | None = None,
    params: dict | None = None,
    description: str = "",
    max_retries: int = 3,
    retry_interval: int = 60,
) -> str:
    """새 스케줄을 DB에 저장하고 APScheduler에 등록한다.

    Returns:
        생성된 schedule_id.
    """
    schedule_id = uuid.uuid4().hex[:12]
    params = params or {}

    conn = get_schedule_db()
    try:
        init_schedule_tables(conn)
        init_run_log_table(conn)
        create_schedule(
            conn, schedule_id, user_id, name, description,
            cron_expr, tool_id, params, max_retries, retry_interval,
        )
    finally:
        conn.close()

    _register_job(schedule_id, cron_expr)
    logger.info("스케줄 등록: %s (%s)", name, schedule_id)
    return schedule_id


# ── 스케줄 취소 ──────────────────────────────────────────


def cancel_schedule(schedule_id: str) -> bool:
    """스케줄을 DB에서 삭제하고 APScheduler 잡을 제거한다."""
    conn = get_schedule_db()
    try:
        init_schedule_tables(conn)
        deleted = delete_schedule(conn, schedule_id)
    finally:
        conn.close()

    remove_job(schedule_id)
    return deleted


# ── 조회 ─────────────────────────────────────────────────


def get_my_schedules(user_id: str) -> list[dict]:
    """사용자의 스케줄 목록을 반환한다."""
    conn = get_schedule_db()
    try:
        init_schedule_tables(conn)
        return get_user_schedules(conn, user_id)
    finally:
        conn.close()


# ── 실행 ─────────────────────────────────────────────────


async def execute_scheduled_job(schedule_id: str) -> None:
    """스케줄된 도구를 실행하고 결과를 로그에 기록한다.

    max_retries 만큼 재시도하며, 각 시도 사이에 retry_interval 대기.
    """
    conn = get_schedule_db()
    try:
        init_schedule_tables(conn)
        init_run_log_table(conn)
        schedule = get_schedule(conn, schedule_id)
    finally:
        conn.close()

    if not schedule:
        logger.warning("스케줄 미존재: %s", schedule_id)
        return

    max_retries = schedule.get("max_retries", 3)
    retry_interval = schedule.get("retry_interval", 60)
    tool_id = schedule.get("tool_id")
    params = schedule.get("params", {})

    for attempt in range(1, max_retries + 1):
        conn = get_schedule_db()
        try:
            log_id = create_log(conn, schedule_id, attempt)
        finally:
            conn.close()

        try:
            raw_call = json.dumps({"tool": tool_id, "params": params})
            result = await execute_tool_call(raw_call)
            status = "success" if result.get("success") else "failed"
            result_str = json.dumps(result, ensure_ascii=False, default=str)

            conn = get_schedule_db()
            try:
                update_log(conn, log_id, status, result=result_str)
            finally:
                conn.close()

            if status == "success":
                return

        except Exception as exc:
            conn = get_schedule_db()
            try:
                update_log(conn, log_id, "error", error=str(exc))
            finally:
                conn.close()

        if attempt < max_retries:
            await asyncio.sleep(retry_interval)


# ── 복원 ─────────────────────────────────────────────────


def restore_schedules() -> int:
    """DB의 활성 스케줄을 APScheduler에 일괄 등록한다.

    Returns:
        복원된 스케줄 수.
    """
    if not is_available():
        return 0

    conn = get_schedule_db()
    try:
        init_schedule_tables(conn)
        init_run_log_table(conn)
        schedules = get_enabled_schedules(conn)
    finally:
        conn.close()

    count = 0
    for s in schedules:
        _register_job(s["schedule_id"], s["cron_expr"])
        count += 1

    logger.info("스케줄 복원 완료: %d건", count)
    return count


# ── 내부 헬퍼 ────────────────────────────────────────────


def _register_job(schedule_id: str, cron_expr: str) -> None:
    """APScheduler에 cron 잡을 등록한다."""
    add_cron_job(
        job_id=schedule_id,
        func=execute_scheduled_job,
        cron_expr=cron_expr,
    )
