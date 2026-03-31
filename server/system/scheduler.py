"""스케줄러. APScheduler + SQLiteJobStore.

APScheduler 미설치 시 기능을 비활성화하고 경고만 출력한다.
"""

import logging
import os

from server.config.constants import DB_DIR

logger = logging.getLogger(__name__)

_scheduler = None
_available = False

try:
    from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    _available = True
except ImportError:
    logger.warning("APScheduler 미설치 — 스케줄 기능 비활성")


# ── 라이프사이클 ─────────────────────────────────────────


def init_scheduler() -> None:
    """스케줄러를 초기화하고 시작한다."""
    global _scheduler
    if not _available:
        return

    jobstore_url = f"sqlite:///{DB_DIR}/apscheduler_jobs.db"
    _scheduler = AsyncIOScheduler(
        jobstores={"default": SQLAlchemyJobStore(url=jobstore_url)}
    )
    _scheduler.start()
    logger.info("스케줄러 시작 (JobStore: %s)", jobstore_url)


def shutdown_scheduler() -> None:
    """스케줄러를 안전하게 종료한다."""
    if _scheduler:
        _scheduler.shutdown()
        logger.info("스케줄러 종료")


# ── 조회 ─────────────────────────────────────────────────


def get_scheduler():
    """APScheduler 인스턴스를 반환한다."""
    return _scheduler


def is_available() -> bool:
    """APScheduler 사용 가능 여부를 반환한다."""
    return _available


def get_jobs() -> list:
    """등록된 잡 목록을 반환한다."""
    if _scheduler:
        return _scheduler.get_jobs()
    return []


# ── 잡 관리 ──────────────────────────────────────────────


def add_cron_job(job_id: str, func, cron_expr: str, **kwargs):
    """cron 표현식으로 반복 작업을 등록한다.

    Args:
        job_id: 고유 잡 식별자.
        func: 실행할 callable.
        cron_expr: '분 시 일 월 요일' 5자리 cron 문자열.
        **kwargs: APScheduler add_job 추가 인자.

    Returns:
        등록된 Job 객체. 스케줄러 미활성 시 None.
    """
    if not _scheduler:
        return None

    parts = cron_expr.split()
    if len(parts) < 5:
        logger.error("잘못된 cron 표현식: %s", cron_expr)
        return None

    trigger_kwargs = {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }

    return _scheduler.add_job(
        func,
        "cron",
        id=job_id,
        replace_existing=True,
        **trigger_kwargs,
        **kwargs,
    )


def remove_job(job_id: str) -> None:
    """등록된 잡을 제거한다. 존재하지 않으면 무시."""
    if not _scheduler:
        return
    try:
        _scheduler.remove_job(job_id)
    except Exception:
        logger.debug("잡 제거 실패 (이미 없음): %s", job_id)
