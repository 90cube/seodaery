"""스키마 포인터 캐시. 쿼리 해시 → 포인터 텍스트 매핑 + 히트 카운트."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import time
from pathlib import Path

POINTER_DB_PATH = os.path.join(os.getenv("DB_DIR", "db"), "pointer_cache.db")

_l1_cache: dict[str, dict] = {}
L1_MAX = 200


def get_pointer_db() -> sqlite3.Connection:
    """포인터 캐시 DB 연결을 반환한다."""
    Path(POINTER_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(POINTER_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_pointer_tables(conn: sqlite3.Connection) -> None:
    """포인터 캐시 테이블을 생성한다."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS pointers (
            query_hash TEXT PRIMARY KEY,
            pointer_text TEXT NOT NULL,
            response_text TEXT DEFAULT '',
            hit_count INTEGER DEFAULT 1,
            created_at REAL,
            last_hit REAL
        );
    """)
    conn.commit()


def make_query_hash(user_id: str, message: str) -> str:
    """쿼리의 해시를 생성한다."""
    raw = f"{user_id}:{message.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def get_pointer(conn: sqlite3.Connection, query_hash: str) -> dict | None:
    """L2: DB에서 포인터를 조회한다."""
    row = conn.execute(
        "SELECT pointer_text, response_text, hit_count FROM pointers WHERE query_hash=?",
        (query_hash,),
    ).fetchone()
    if row:
        conn.execute(
            "UPDATE pointers SET hit_count=hit_count+1, last_hit=? WHERE query_hash=?",
            (time.time(), query_hash),
        )
        conn.commit()
        return dict(row)
    return None


def store_pointer(
    conn: sqlite3.Connection,
    query_hash: str,
    pointer_text: str,
    response_text: str = "",
) -> None:
    """포인터를 DB에 저장한다."""
    now = time.time()
    conn.execute(
        "INSERT OR REPLACE INTO pointers (query_hash, pointer_text, response_text, hit_count, created_at, last_hit) "
        "VALUES (?, ?, ?, COALESCE((SELECT hit_count FROM pointers WHERE query_hash=?), 0) + 1, ?, ?)",
        (query_hash, pointer_text, response_text, query_hash, now, now),
    )
    conn.commit()


def l1_get(query_hash: str) -> dict | None:
    """L1: 메모리 캐시에서 조회한다."""
    return _l1_cache.get(query_hash)


def l1_put(query_hash: str, pointer_text: str, response_text: str = "") -> None:
    """L1: 메모리 캐시에 저장한다."""
    if len(_l1_cache) >= L1_MAX:
        oldest = min(_l1_cache, key=lambda k: _l1_cache[k].get("last_hit", 0))
        del _l1_cache[oldest]
    _l1_cache[query_hash] = {
        "pointer_text": pointer_text,
        "response_text": response_text,
        "last_hit": time.time(),
    }


def promote_to_l1(conn: sqlite3.Connection, min_hits: int = 3) -> int:
    """히트 카운트가 높은 포인터를 L1으로 승격한다."""
    rows = conn.execute(
        "SELECT query_hash, pointer_text, response_text FROM pointers "
        "WHERE hit_count >= ? ORDER BY hit_count DESC LIMIT ?",
        (min_hits, L1_MAX),
    ).fetchall()
    for row in rows:
        l1_put(row["query_hash"], row["pointer_text"], row["response_text"])
    return len(rows)


def get_cache_stats(conn: sqlite3.Connection) -> dict:
    """캐시 통계를 반환한다."""
    total = conn.execute("SELECT COUNT(*) FROM pointers").fetchone()[0]
    hot = conn.execute("SELECT COUNT(*) FROM pointers WHERE hit_count >= 3").fetchone()[0]
    return {"l1_size": len(_l1_cache), "l2_total": total, "l2_hot": hot}
