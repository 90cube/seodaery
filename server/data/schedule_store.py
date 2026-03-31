"""스케줄 CRUD 모듈. 전역 SQLite DB(schedules.db) 사용."""

import json
import sqlite3
import time
from pathlib import Path

from server.config.constants import DB_DIR

SCHEDULE_DB_PATH = str(Path(DB_DIR) / "schedules.db")


# ── 연결 ─────────────────────────────────────────────────


def get_schedule_db() -> sqlite3.Connection:
    """스케줄 전용 DB 연결을 반환한다."""
    Path(SCHEDULE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SCHEDULE_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_schedule_tables(conn: sqlite3.Connection) -> None:
    """스케줄 테이블을 생성한다. 이미 존재하면 무시한다."""
    conn.executescript(_SCHEMA_SQL)


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schedules (
    schedule_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    cron_expr TEXT NOT NULL,
    tool_id TEXT DEFAULT NULL,
    params TEXT DEFAULT '{}',
    enabled INTEGER DEFAULT 1,
    max_retries INTEGER DEFAULT 3,
    retry_interval INTEGER DEFAULT 60,
    created_at REAL,
    updated_at REAL
);
"""


# ── CRUD ─────────────────────────────────────────────────


def create_schedule(
    conn: sqlite3.Connection,
    schedule_id: str,
    user_id: str,
    name: str,
    description: str,
    cron_expr: str,
    tool_id: str | None,
    params: dict,
    max_retries: int = 3,
    retry_interval: int = 60,
) -> None:
    """새 스케줄을 생성한다."""
    now = time.time()
    conn.execute(
        """INSERT INTO schedules
           (schedule_id, user_id, name, description, cron_expr,
            tool_id, params, enabled, max_retries, retry_interval,
            created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)""",
        (
            schedule_id, user_id, name, description, cron_expr,
            tool_id, json.dumps(params, ensure_ascii=False),
            max_retries, retry_interval, now, now,
        ),
    )
    conn.commit()


def get_schedule(conn: sqlite3.Connection, schedule_id: str) -> dict | None:
    """스케줄 한 건을 조회한다."""
    row = conn.execute(
        "SELECT * FROM schedules WHERE schedule_id = ?", (schedule_id,)
    ).fetchone()
    return _row_to_dict(row) if row else None


def get_user_schedules(conn: sqlite3.Connection, user_id: str) -> list[dict]:
    """특정 사용자의 스케줄 목록을 반환한다."""
    rows = conn.execute(
        "SELECT * FROM schedules WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_all_schedules(conn: sqlite3.Connection) -> list[dict]:
    """전체 스케줄 목록을 반환한다."""
    rows = conn.execute(
        "SELECT * FROM schedules ORDER BY created_at DESC"
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_enabled_schedules(conn: sqlite3.Connection) -> list[dict]:
    """활성화된 스케줄만 반환한다."""
    rows = conn.execute(
        "SELECT * FROM schedules WHERE enabled = 1 ORDER BY created_at DESC"
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def update_schedule(
    conn: sqlite3.Connection,
    schedule_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    cron_expr: str | None = None,
    tool_id: str | None = None,
    params: dict | None = None,
    max_retries: int | None = None,
    retry_interval: int | None = None,
) -> bool:
    """스케줄 필드를 부분 갱신한다. 변경된 행이 있으면 True."""
    fields: list[str] = []
    values: list = []
    for col, val in [
        ("name", name), ("description", description),
        ("cron_expr", cron_expr), ("tool_id", tool_id),
        ("max_retries", max_retries), ("retry_interval", retry_interval),
    ]:
        if val is not None:
            fields.append(f"{col} = ?")
            values.append(val)
    if params is not None:
        fields.append("params = ?")
        values.append(json.dumps(params, ensure_ascii=False))
    if not fields:
        return False
    fields.append("updated_at = ?")
    values.append(time.time())
    values.append(schedule_id)
    cur = conn.execute(
        f"UPDATE schedules SET {', '.join(fields)} WHERE schedule_id = ?",
        values,
    )
    conn.commit()
    return cur.rowcount > 0


def toggle_schedule(
    conn: sqlite3.Connection, schedule_id: str, enabled: bool
) -> bool:
    """스케줄 활성/비활성을 전환한다."""
    cur = conn.execute(
        "UPDATE schedules SET enabled = ?, updated_at = ? WHERE schedule_id = ?",
        (int(enabled), time.time(), schedule_id),
    )
    conn.commit()
    return cur.rowcount > 0


def delete_schedule(conn: sqlite3.Connection, schedule_id: str) -> bool:
    """스케줄을 삭제한다."""
    cur = conn.execute(
        "DELETE FROM schedules WHERE schedule_id = ?", (schedule_id,)
    )
    conn.commit()
    return cur.rowcount > 0


# ── 헬퍼 ─────────────────────────────────────────────────


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Row 객체를 딕셔너리로 변환한다. params는 JSON 파싱."""
    d = dict(row)
    d["params"] = json.loads(d.get("params", "{}"))
    d["enabled"] = bool(d.get("enabled", 0))
    return d
