"""지시사항·제약·스킬 CRUD 전용 모듈."""

import sqlite3
import time
from typing import List, Optional

_VALID_TYPES = ("directive", "restriction", "agent", "skill")


def add_directive(
    conn: sqlite3.Connection,
    directive_type: str,
    content: str,
) -> int:
    """새 지시사항을 추가한다.

    Args:
        conn: SQLite 연결 객체.
        directive_type: 유형 ('directive', 'restriction', 'agent', 'skill').
        content: 지시사항 내용.

    Returns:
        생성된 지시사항의 id.

    Raises:
        ValueError: 유효하지 않은 type일 경우.
    """
    if directive_type not in _VALID_TYPES:
        raise ValueError(
            f"유효하지 않은 type: {directive_type!r}. "
            f"허용: {_VALID_TYPES}"
        )
    now = time.time()
    cur = conn.execute(
        "INSERT INTO directives (type, content, active, importance, created_at) "
        "VALUES (?, ?, 1, 1, ?)",
        (directive_type, content, now),
    )
    conn.commit()
    return cur.lastrowid


def get_directives(
    conn: sqlite3.Connection,
    directive_type: Optional[str] = None,
) -> List[dict]:
    """지시사항 목록을 반환한다. type이 주어지면 해당 유형만 필터링한다.

    Args:
        conn: SQLite 연결 객체.
        directive_type: 필터링할 유형 (None이면 전체).

    Returns:
        지시사항 딕셔너리 리스트.
    """
    if directive_type is not None:
        rows = conn.execute(
            "SELECT * FROM directives WHERE type = ? ORDER BY importance DESC",
            (directive_type,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM directives ORDER BY importance DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_active_skills(conn: sqlite3.Connection) -> List[dict]:
    """활성화된 스킬 목록을 반환한다.

    Args:
        conn: SQLite 연결 객체.

    Returns:
        활성 스킬 딕셔너리 리스트.
    """
    rows = conn.execute(
        "SELECT * FROM directives "
        "WHERE type = 'skill' AND active = 1 "
        "ORDER BY importance DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def deactivate_directive(
    conn: sqlite3.Connection, directive_id: int
) -> None:
    """지시사항을 비활성화한다 (active=0).

    Args:
        conn: SQLite 연결 객체.
        directive_id: 비활성화할 지시사항 id.
    """
    conn.execute(
        "UPDATE directives SET active = 0 WHERE id = ?",
        (directive_id,),
    )
    conn.commit()


def increase_importance(
    conn: sqlite3.Connection, directive_id: int
) -> None:
    """지시사항의 중요도를 1 증가시킨다.

    Args:
        conn: SQLite 연결 객체.
        directive_id: 중요도를 올릴 지시사항 id.
    """
    conn.execute(
        "UPDATE directives SET importance = importance + 1 WHERE id = ?",
        (directive_id,),
    )
    conn.commit()
