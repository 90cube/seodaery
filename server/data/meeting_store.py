"""회의 일정 + 참석자 CRUD. events.db 사용."""

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
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


_MEETING_SCHEMA = """
CREATE TABLE IF NOT EXISTS meetings (
    meeting_id       TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    meeting_date     TEXT NOT NULL,
    location         TEXT DEFAULT '',
    description      TEXT DEFAULT '',
    related_patch_id TEXT,
    created_by       TEXT NOT NULL,
    created_at       REAL
);

CREATE TABLE IF NOT EXISTS meeting_participants (
    meeting_id  TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    user_name   TEXT NOT NULL,
    PRIMARY KEY (meeting_id, user_id),
    FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id)
);
"""


def init_meeting_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(_MEETING_SCHEMA)


# ── 회의 CRUD ───────────────────────────────────────────


def create_meeting(conn: sqlite3.Connection, meeting_id: str, **kw) -> None:
    conn.execute(
        """INSERT INTO meetings
           (meeting_id, title, meeting_date, location, description,
            related_patch_id, created_by, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            meeting_id, kw["title"], kw["meeting_date"],
            kw.get("location", ""), kw.get("description", ""),
            kw.get("related_patch_id"), kw["created_by"], time.time(),
        ),
    )
    conn.commit()


def get_meeting(conn: sqlite3.Connection, meeting_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM meetings WHERE meeting_id = ?", (meeting_id,)
    ).fetchone()
    return dict(row) if row else None


def list_meetings(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM meetings ORDER BY meeting_date DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def list_meetings_by_patch(conn: sqlite3.Connection, patch_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM meetings WHERE related_patch_id = ? ORDER BY meeting_date",
        (patch_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def delete_meeting(conn: sqlite3.Connection, meeting_id: str) -> bool:
    conn.execute(
        "DELETE FROM meeting_participants WHERE meeting_id = ?", (meeting_id,)
    )
    cur = conn.execute(
        "DELETE FROM meetings WHERE meeting_id = ?", (meeting_id,)
    )
    conn.commit()
    return cur.rowcount > 0


# ── 참석자 CRUD ─────────────────────────────────────────


def add_participant(
    conn: sqlite3.Connection,
    meeting_id: str,
    user_id: str,
    user_name: str,
) -> None:
    conn.execute(
        """INSERT OR IGNORE INTO meeting_participants
           (meeting_id, user_id, user_name) VALUES (?,?,?)""",
        (meeting_id, user_id, user_name),
    )
    conn.commit()


def get_participants(conn: sqlite3.Connection, meeting_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM meeting_participants WHERE meeting_id = ?",
        (meeting_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_user_meetings(conn: sqlite3.Connection, user_id: str) -> list[dict]:
    """특정 사용자가 참석하는 회의 목록을 반환한다."""
    rows = conn.execute(
        """SELECT m.*
           FROM meetings m
           JOIN meeting_participants mp ON m.meeting_id = mp.meeting_id
           WHERE mp.user_id = ?
           ORDER BY m.meeting_date""",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def remove_participant(
    conn: sqlite3.Connection, meeting_id: str, user_id: str
) -> bool:
    cur = conn.execute(
        "DELETE FROM meeting_participants WHERE meeting_id = ? AND user_id = ?",
        (meeting_id, user_id),
    )
    conn.commit()
    return cur.rowcount > 0
