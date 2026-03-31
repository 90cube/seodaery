"""SQLite 연결 및 테이블 초기화 모듈."""

import os
import sqlite3

_DB_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "db")


def get_db(user_id: str) -> sqlite3.Connection:
    """사용자별 SQLite 데이터베이스 연결을 반환한다.

    Args:
        user_id: 사용자 고유 식별자. DB 파일명으로 사용된다.

    Returns:
        sqlite3.Connection 객체 (row_factory=sqlite3.Row 설정됨).
    """
    db_dir = os.path.abspath(_DB_DIR)
    os.makedirs(db_dir, exist_ok=True)

    db_path = os.path.join(db_dir, f"{user_id}.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    init_tables(conn)
    return conn


def init_tables(conn: sqlite3.Connection) -> None:
    """모든 필수 테이블을 생성한다. 이미 존재하면 무시한다.

    Args:
        conn: SQLite 연결 객체.
    """
    conn.executescript(_SCHEMA_SQL)


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    position TEXT,
    role TEXT,
    created_at REAL,
    last_seen REAL
);

CREATE TABLE IF NOT EXISTS triples (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object TEXT NOT NULL,
    importance INTEGER DEFAULT 1,
    created_at REAL,
    updated_at REAL
);

CREATE TABLE IF NOT EXISTS directives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK(type IN ('directive','restriction','agent','skill')),
    content TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    importance INTEGER DEFAULT 1,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    started_at REAL,
    ended_at REAL,
    kv_slot_path TEXT
);
"""
