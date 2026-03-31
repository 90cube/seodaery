"""사용자 CRUD 전용 모듈."""

import sqlite3
import time
from typing import Optional


def create_user(
    conn: sqlite3.Connection,
    user_id: str,
    name: str,
    position: Optional[str] = None,
    role: Optional[str] = None,
) -> None:
    """새 사용자를 생성한다.

    Args:
        conn: SQLite 연결 객체.
        user_id: 사용자 고유 식별자.
        name: 사용자 이름.
        position: 직책 (선택).
        role: 역할 (선택).
    """
    now = time.time()
    conn.execute(
        "INSERT INTO users (user_id, name, position, role, created_at, last_seen) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, name, position, role, now, now),
    )
    conn.commit()


def get_user(conn: sqlite3.Connection, user_id: str) -> Optional[dict]:
    """사용자 정보를 딕셔너리로 반환한다. 없으면 None.

    Args:
        conn: SQLite 연결 객체.
        user_id: 사용자 고유 식별자.

    Returns:
        사용자 정보 딕셔너리 또는 None.
    """
    row = conn.execute(
        "SELECT * FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def update_last_seen(conn: sqlite3.Connection, user_id: str) -> None:
    """사용자의 last_seen을 현재 시각으로 갱신한다.

    Args:
        conn: SQLite 연결 객체.
        user_id: 사용자 고유 식별자.
    """
    conn.execute(
        "UPDATE users SET last_seen = ? WHERE user_id = ?",
        (time.time(), user_id),
    )
    conn.commit()


def user_exists(conn: sqlite3.Connection, user_id: str) -> bool:
    """사용자 존재 여부를 반환한다.

    Args:
        conn: SQLite 연결 객체.
        user_id: 사용자 고유 식별자.

    Returns:
        존재하면 True, 아니면 False.
    """
    row = conn.execute(
        "SELECT 1 FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()
    return row is not None
