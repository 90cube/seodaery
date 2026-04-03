"""생일 CRUD. events.db 사용."""

import sqlite3
import time
from pathlib import Path

from server.config.constants import DB_DIR, EVENT_DB_NAME

EVENT_DB_PATH = str(Path(DB_DIR) / EVENT_DB_NAME)


def get_event_db() -> sqlite3.Connection:
    """이벤트 전용 DB 연결을 반환한다."""
    Path(EVENT_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(EVENT_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


_BIRTHDAY_SCHEMA = """
CREATE TABLE IF NOT EXISTS birthdays (
    user_id    TEXT PRIMARY KEY,
    user_name  TEXT NOT NULL,
    birthday   TEXT NOT NULL,
    created_at REAL
);
"""


def init_birthday_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(_BIRTHDAY_SCHEMA)


# ── CRUD ─────────────────────────────────────────────────


def upsert_birthday(
    conn: sqlite3.Connection,
    user_id: str,
    user_name: str,
    birthday: str,
) -> None:
    """생일을 등록하거나 갱신한다. birthday 형식: MM-DD."""
    conn.execute(
        """INSERT INTO birthdays (user_id, user_name, birthday, created_at)
           VALUES (?,?,?,?)
           ON CONFLICT(user_id) DO UPDATE SET
             user_name = excluded.user_name,
             birthday  = excluded.birthday""",
        (user_id, user_name, birthday, time.time()),
    )
    conn.commit()


def get_birthday(conn: sqlite3.Connection, user_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM birthdays WHERE user_id = ?", (user_id,)
    ).fetchone()
    return dict(row) if row else None


def list_birthdays(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM birthdays ORDER BY birthday"
    ).fetchall()
    return [dict(r) for r in rows]


def get_upcoming_birthdays(conn: sqlite3.Connection, today_mmdd: str) -> list[dict]:
    """오늘 이후 가장 가까운 생일 목록을 반환한다."""
    rows = conn.execute(
        """SELECT * FROM birthdays
           WHERE birthday >= ?
           ORDER BY birthday
           LIMIT 10""",
        (today_mmdd,),
    ).fetchall()
    return [dict(r) for r in rows]


def delete_birthday(conn: sqlite3.Connection, user_id: str) -> bool:
    cur = conn.execute(
        "DELETE FROM birthdays WHERE user_id = ?", (user_id,)
    )
    conn.commit()
    return cur.rowcount > 0
