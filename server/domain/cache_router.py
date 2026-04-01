"""캐시 계층 라우터. L1→L2→L3→L4→L5 순서로 탐색한다."""

from __future__ import annotations

import logging
import time

from server.data.pointer_cache import (
    get_pointer,
    get_pointer_db,
    init_pointer_tables,
    l1_get,
    l1_put,
    make_query_hash,
    store_pointer,
)

logger = logging.getLogger(__name__)


class CacheResult:
    """캐시 조회 결과."""

    __slots__ = ("hit", "level", "pointer_text", "response_text", "elapsed")

    def __init__(
        self,
        hit: bool,
        level: str,
        pointer_text: str = "",
        response_text: str = "",
        elapsed: float = 0.0,
    ):
        self.hit = hit
        self.level = level
        self.pointer_text = pointer_text
        self.response_text = response_text
        self.elapsed = elapsed


def lookup(user_id: str, message: str) -> CacheResult:
    """L1→L2 순서로 캐시를 탐색한다. L3 이상은 별도 호출."""
    start = time.time()
    query_hash = make_query_hash(user_id, message)

    # L1: 메모리 캐시
    l1 = l1_get(query_hash)
    if l1 and l1.get("response_text"):
        elapsed = time.time() - start
        logger.info("L1 히트: %s (%.1fms)", query_hash, elapsed * 1000)
        return CacheResult(
            hit=True,
            level="L1",
            pointer_text=l1["pointer_text"],
            response_text=l1["response_text"],
            elapsed=elapsed,
        )

    # L2: SQLite 포인터 캐시
    conn = get_pointer_db()
    init_pointer_tables(conn)
    l2 = get_pointer(conn, query_hash)
    conn.close()

    if l2 and l2.get("response_text"):
        elapsed = time.time() - start
        logger.info("L2 히트: %s (%.1fms)", query_hash, elapsed * 1000)
        l1_put(query_hash, l2["pointer_text"], l2["response_text"])
        return CacheResult(
            hit=True,
            level="L2",
            pointer_text=l2["pointer_text"],
            response_text=l2["response_text"],
            elapsed=elapsed,
        )

    # L2 포인터만 있고 응답이 없는 경우 (포인터 재사용)
    if l2 and l2.get("pointer_text"):
        elapsed = time.time() - start
        logger.info("L2 포인터 히트 (응답 없음): %s", query_hash)
        return CacheResult(
            hit=False,
            level="L2-pointer",
            pointer_text=l2["pointer_text"],
            elapsed=elapsed,
        )

    elapsed = time.time() - start
    logger.info("캐시 미스: %s (%.1fms)", query_hash, elapsed * 1000)
    return CacheResult(hit=False, level="miss", elapsed=elapsed)


def save_to_cache(
    user_id: str,
    message: str,
    pointer_text: str,
    response_text: str,
) -> None:
    """응답을 L1 + L2에 저장한다."""
    query_hash = make_query_hash(user_id, message)

    l1_put(query_hash, pointer_text, response_text)

    conn = get_pointer_db()
    init_pointer_tables(conn)
    store_pointer(conn, query_hash, pointer_text, response_text)
    conn.close()

    logger.info("캐시 저장: %s", query_hash)
