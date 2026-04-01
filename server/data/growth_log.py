"""성장 로그. 추출 건수, 캐시 히트율, 시간 추이를 기록한다."""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

GROWTH_DB_PATH = os.path.join(os.getenv("DB_DIR", "db"), "growth_log.db")


def get_growth_db() -> sqlite3.Connection:
    """성장 로그 DB 연결을 반환한다."""
    Path(GROWTH_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(GROWTH_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_growth_tables(conn: sqlite3.Connection) -> None:
    """성장 로그 테이블을 생성한다."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS growth_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            triples_extracted INTEGER DEFAULT 0,
            cache_hits_l1 INTEGER DEFAULT 0,
            cache_hits_l2 INTEGER DEFAULT 0,
            cache_misses INTEGER DEFAULT 0,
            promoted_to_l1 INTEGER DEFAULT 0,
            elapsed_sec REAL DEFAULT 0,
            created_at REAL
        );
    """)
    conn.commit()


def log_growth_event(
    conn: sqlite3.Connection,
    user_id: str,
    event_type: str,
    triples_extracted: int = 0,
    cache_hits_l1: int = 0,
    cache_hits_l2: int = 0,
    cache_misses: int = 0,
    promoted_to_l1: int = 0,
    elapsed_sec: float = 0,
) -> None:
    """성장 이벤트를 기록한다."""
    conn.execute(
        "INSERT INTO growth_events "
        "(user_id, event_type, triples_extracted, cache_hits_l1, "
        "cache_hits_l2, cache_misses, promoted_to_l1, elapsed_sec, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, event_type, triples_extracted, cache_hits_l1,
         cache_hits_l2, cache_misses, promoted_to_l1, elapsed_sec, time.time()),
    )
    conn.commit()


def get_growth_summary(conn: sqlite3.Connection, user_id: str = None) -> dict:
    """성장 통계 요약을 반환한다."""
    where = "WHERE user_id=?" if user_id else ""
    params = (user_id,) if user_id else ()

    row = conn.execute(
        f"SELECT COUNT(*) as events, "
        f"SUM(triples_extracted) as total_triples, "
        f"SUM(cache_hits_l1) as total_l1, "
        f"SUM(cache_hits_l2) as total_l2, "
        f"SUM(cache_misses) as total_miss "
        f"FROM growth_events {where}",
        params,
    ).fetchone()

    total_hits = (row["total_l1"] or 0) + (row["total_l2"] or 0)
    total_all = total_hits + (row["total_miss"] or 0)
    hit_rate = total_hits / total_all if total_all > 0 else 0

    return {
        "events": row["events"],
        "total_triples": row["total_triples"] or 0,
        "cache_hit_rate": round(hit_rate, 4),
        "l1_hits": row["total_l1"] or 0,
        "l2_hits": row["total_l2"] or 0,
        "misses": row["total_miss"] or 0,
    }
