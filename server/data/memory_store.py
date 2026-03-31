"""온톨로지 트리플 CRUD 전용 모듈."""

import sqlite3
import time
from typing import List


def store_triple(
    conn: sqlite3.Connection,
    subject: str,
    predicate: str,
    object_val: str,
) -> int:
    """트리플을 저장한다. 동일 트리플이 존재하면 importance를 1 증가시킨다.

    Args:
        conn: SQLite 연결 객체.
        subject: 주어.
        predicate: 술어.
        object_val: 목적어.

    Returns:
        저장 또는 갱신된 트리플의 id.
    """
    now = time.time()
    existing = conn.execute(
        "SELECT id, importance FROM triples "
        "WHERE subject = ? AND predicate = ? AND object = ?",
        (subject, predicate, object_val),
    ).fetchone()

    if existing:
        triple_id = existing["id"]
        new_importance = existing["importance"] + 1
        conn.execute(
            "UPDATE triples SET importance = ?, updated_at = ? WHERE id = ?",
            (new_importance, now, triple_id),
        )
    else:
        cur = conn.execute(
            "INSERT INTO triples (subject, predicate, object, importance, created_at, updated_at) "
            "VALUES (?, ?, ?, 1, ?, ?)",
            (subject, predicate, object_val, now, now),
        )
        triple_id = cur.lastrowid

    conn.commit()
    return triple_id


def search_triples(conn: sqlite3.Connection, keyword: str) -> List[dict]:
    """주어·술어·목적어에 키워드가 포함된 트리플을 검색한다.

    Args:
        conn: SQLite 연결 객체.
        keyword: 검색어 (LIKE %keyword% 방식).

    Returns:
        일치하는 트리플 딕셔너리 리스트.
    """
    pattern = f"%{keyword}%"
    rows = conn.execute(
        "SELECT * FROM triples "
        "WHERE subject LIKE ? OR predicate LIKE ? OR object LIKE ? "
        "ORDER BY importance DESC",
        (pattern, pattern, pattern),
    ).fetchall()
    return [dict(r) for r in rows]


def get_important_triples(
    conn: sqlite3.Connection, limit: int = 20
) -> List[dict]:
    """중요도 순으로 상위 트리플을 반환한다.

    Args:
        conn: SQLite 연결 객체.
        limit: 반환할 최대 개수 (기본 20).

    Returns:
        트리플 딕셔너리 리스트 (importance 내림차순).
    """
    rows = conn.execute(
        "SELECT * FROM triples ORDER BY importance DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_all_triples(conn: sqlite3.Connection) -> List[dict]:
    """모든 트리플을 반환한다.

    Args:
        conn: SQLite 연결 객체.

    Returns:
        전체 트리플 딕셔너리 리스트.
    """
    rows = conn.execute(
        "SELECT * FROM triples ORDER BY importance DESC"
    ).fetchall()
    return [dict(r) for r in rows]
