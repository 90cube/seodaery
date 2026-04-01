"""자기 성장 엔진. 대화에서 사실을 추출하고 포인터 캐시를 성장시킨다."""

from __future__ import annotations

import logging
import time

from server.data.database import get_db, init_tables
from server.data.memory_store import store_triple
from server.data.pointer_cache import (
    get_pointer_db,
    init_pointer_tables,
    promote_to_l1,
)
from server.domain.memory_extractor import extract_memories
from server.domain.session_manager import end_session, get_conversation_text

logger = logging.getLogger(__name__)


async def run_growth_cycle(user_id: str) -> dict:
    """세션 종료 시 성장 사이클을 실행한다.

    1. 대화에서 새로운 사실 추출
    2. SQLite 트리플로 저장
    3. 포인터 캐시에서 자주 히트되는 항목을 L1으로 승격

    반환: {"extracted": int, "promoted": int}
    """
    start = time.time()

    # 1. 대화 텍스트 추출
    conversation = get_conversation_text(user_id)
    if not conversation:
        end_session(user_id)
        return {"extracted": 0, "promoted": 0}

    # 2. 0.8B 추론기로 사실 추출
    triples = await extract_memories(conversation)
    extracted = 0

    if triples:
        conn = get_db(user_id)
        init_tables(conn)
        for t in triples:
            store_triple(conn, t["subject"], t["predicate"], t["object"])
            extracted += 1
        conn.close()

    # 3. 포인터 캐시 L1 승격
    ptr_conn = get_pointer_db()
    init_pointer_tables(ptr_conn)
    promoted = promote_to_l1(ptr_conn, min_hits=3)
    ptr_conn.close()

    # 4. 세션 종료
    end_session(user_id)

    elapsed = time.time() - start
    logger.info(
        "성장 사이클 완료: %s — 추출 %d건, L1 승격 %d건 (%.1fs)",
        user_id, extracted, promoted, elapsed,
    )

    return {"extracted": extracted, "promoted": promoted}


def get_growth_stats(user_id: str) -> dict:
    """유저의 성장 통계를 반환한다."""
    from server.data.pointer_cache import get_cache_stats

    conn = get_db(user_id)
    init_tables(conn)
    from server.data.memory_store import get_all_triples
    total_triples = len(get_all_triples(conn))
    conn.close()

    ptr_conn = get_pointer_db()
    init_pointer_tables(ptr_conn)
    cache_stats = get_cache_stats(ptr_conn)
    ptr_conn.close()

    return {
        "total_triples": total_triples,
        **cache_stats,
    }
