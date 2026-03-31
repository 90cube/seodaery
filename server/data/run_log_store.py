"""실행 로그 CRUD 모듈. schedules.db 내 run_logs 테이블 사용."""

import sqlite3
import time


# ── 테이블 초기화 ────────────────────────────────────────


def init_run_log_table(conn: sqlite3.Connection) -> None:
    """run_logs 테이블을 생성한다. 이미 존재하면 무시한다."""
    conn.executescript(_SCHEMA_SQL)


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS run_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id TEXT NOT NULL,
    started_at REAL,
    ended_at REAL,
    status TEXT NOT NULL DEFAULT 'running',
    result TEXT DEFAULT '',
    error TEXT DEFAULT '',
    attempt INTEGER DEFAULT 1
);
"""


# ── CRUD ─────────────────────────────────────────────────


def create_log(
    conn: sqlite3.Connection, schedule_id: str, attempt: int = 1
) -> int:
    """실행 로그를 생성하고 log_id를 반환한다."""
    cur = conn.execute(
        """INSERT INTO run_logs (schedule_id, started_at, status, attempt)
           VALUES (?, ?, 'running', ?)""",
        (schedule_id, time.time(), attempt),
    )
    conn.commit()
    return cur.lastrowid


def update_log(
    conn: sqlite3.Connection,
    log_id: int,
    status: str,
    result: str = "",
    error: str = "",
    ended_at: float | None = None,
) -> bool:
    """실행 로그를 갱신한다. 변경된 행이 있으면 True."""
    if ended_at is None:
        ended_at = time.time()
    cur = conn.execute(
        """UPDATE run_logs
           SET status = ?, result = ?, error = ?, ended_at = ?
           WHERE log_id = ?""",
        (status, result, error, ended_at, log_id),
    )
    conn.commit()
    return cur.rowcount > 0


def get_schedule_logs(
    conn: sqlite3.Connection, schedule_id: str, limit: int = 20
) -> list[dict]:
    """특정 스케줄의 실행 로그를 최신순으로 반환한다."""
    rows = conn.execute(
        """SELECT * FROM run_logs
           WHERE schedule_id = ?
           ORDER BY started_at DESC LIMIT ?""",
        (schedule_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_recent_logs(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    """전체 실행 로그를 최신순으로 반환한다."""
    rows = conn.execute(
        "SELECT * FROM run_logs ORDER BY started_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]
