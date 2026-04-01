"""병렬 페처. asyncio.gather로 기억/지식/DB/일정을 동시 조회한다."""

from __future__ import annotations

import asyncio
import logging
import time

from server.data.database import get_db, init_tables
from server.data.memory_store import get_important_triples
from server.domain.knowledge_search import search_game_knowledge
from server.domain.memory_extractor import search_relevant_memories
from server.domain.pointer_builder import (
    assemble_pointer,
    build_asset_pointer,
    build_knowledge_pointer,
    build_schedule_pointer,
    build_tool_pointer,
    build_user_pointer,
)

logger = logging.getLogger(__name__)


async def fetch_all_parallel(
    user_id: str,
    message: str,
    user_info: dict | None = None,
) -> dict:
    """모든 데이터 소스를 병렬로 조회하고 스키마 포인터를 조립한다."""
    start = time.time()

    # 병렬 실행
    memory_task = _fetch_memories(user_id, message)
    knowledge_task = _fetch_knowledge(message)
    schedule_task = _fetch_schedules(user_id)
    tool_task = _fetch_tools()

    results = await asyncio.gather(
        memory_task, knowledge_task, schedule_task, tool_task,
        return_exceptions=True,
    )

    memories = results[0] if not isinstance(results[0], Exception) else []
    knowledge = results[1] if not isinstance(results[1], Exception) else []
    schedules = results[2] if not isinstance(results[2], Exception) else []
    tools = results[3] if not isinstance(results[3], Exception) else {}

    # 포인터 조립
    triple_count = len(memories) if isinstance(memories, list) else 0
    user_ptr = build_user_pointer(user_id, user_info, triple_count)
    knowledge_ptr = build_knowledge_pointer(knowledge)
    schedule_ptr = build_schedule_pointer(schedules)
    tool_ptr = build_tool_pointer(
        tools.get("count", 0), tools.get("skill_names", [])
    )

    pointer = assemble_pointer(user_ptr, knowledge_ptr, schedule_ptr, tool_ptr)
    elapsed = time.time() - start

    logger.info("병렬 조회 완료: %.1fms, 포인터: %s", elapsed * 1000, pointer[:80])

    return {
        "pointer": pointer,
        "memories": memories,
        "knowledge": knowledge,
        "schedules": schedules,
        "elapsed": elapsed,
    }


async def _fetch_memories(user_id: str, message: str) -> list[dict]:
    """유저 기억 트리플을 조회하고 관련성을 필터링한다."""
    conn = get_db(user_id)
    init_tables(conn)
    all_triples = get_important_triples(conn, limit=30)
    conn.close()

    triple_dicts = [
        {"subject": t[0], "predicate": t[1], "object": t[2]}
        for t in all_triples
    ]
    return await search_relevant_memories(message, triple_dicts)


async def _fetch_knowledge(message: str) -> list[dict]:
    """지식 DB를 검색한다."""
    return await search_game_knowledge(message)


async def _fetch_schedules(user_id: str) -> list[dict]:
    """유저 일정을 조회한다."""
    try:
        from server.data.schedule_store import (
            get_schedule_db,
            get_user_schedules,
            init_schedule_tables,
        )
        conn = get_schedule_db()
        init_schedule_tables(conn)
        schedules = get_user_schedules(conn, user_id)
        conn.close()
        return schedules
    except Exception:
        return []


async def _fetch_tools() -> dict:
    """활성 도구/스킬 정보를 조회한다."""
    try:
        from server.data.skill_store import get_enabled_skills, init_skill_table
        from server.data.tool_registry import (
            get_enabled_tools,
            get_tools_db,
            init_tool_tables,
        )
        conn = get_tools_db()
        init_tool_tables(conn)
        init_skill_table(conn)
        tools = get_enabled_tools(conn)
        skills = get_enabled_skills(conn)
        conn.close()
        return {
            "count": len(tools),
            "skill_names": [s["name"] for s in skills],
        }
    except Exception:
        return {"count": 0, "skill_names": []}
