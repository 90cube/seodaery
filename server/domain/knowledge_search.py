"""0.8B 시맨틱 검색. 자연어 → 키워드 추출 → FTS5 검색."""

from __future__ import annotations

import logging

from server.config.constants import ROUTER_MODEL_URL, ROUTER_TIMEOUT_SEC
from server.data.knowledge_store import (
    find_image,
    get_knowledge_db,
    init_knowledge_tables,
    search_knowledge,
)
from server.system.llama_client import request_completion

logger = logging.getLogger(__name__)

KEYWORD_EXTRACTION_PROMPT = (
    "Extract search keywords from the user message.\n"
    "Output ONLY the keywords separated by spaces, nothing else.\n"
    "Example input: '리퍼 캐릭터 스킬이 뭐야?'\n"
    "Example output: 리퍼 캐릭터 스킬"
)


async def extract_search_keywords(message: str) -> str:
    """0.8B 모델로 검색 키워드를 추출한다."""
    messages = [
        {"role": "system", "content": KEYWORD_EXTRACTION_PROMPT},
        {"role": "user", "content": message},
    ]

    raw = await request_completion(
        base_url=ROUTER_MODEL_URL,
        messages=messages,
        max_tokens=30,
        timeout=ROUTER_TIMEOUT_SEC,
        temperature=0.0,
    )
    return raw.strip()


async def search_game_knowledge(message: str) -> list[dict]:
    """자연어 메시지에서 키워드를 추출하고 지식 DB를 검색한다."""
    keywords = await extract_search_keywords(message)
    if not keywords:
        return []

    conn = get_knowledge_db()
    init_knowledge_tables(conn)

    try:
        results = search_knowledge(conn, keywords, limit=5)
    except Exception:
        logger.warning("FTS 검색 실패, 키워드: %s", keywords)
        results = []
    finally:
        conn.close()

    # 이미지 경로 자동 매칭
    for item in results:
        if not item.get("image_path"):
            item["image_path"] = find_image(item["title"])

    return results


def format_knowledge_context(results: list[dict]) -> str:
    """검색 결과를 9B 컨텍스트용 텍스트로 변환한다."""
    if not results:
        return ""

    lines = ["[지식 DB 검색 결과]"]
    for r in results:
        line = f"- [{r['category']}] {r['title']}: {r['description']}"
        if r.get("tags"):
            line += f" (태그: {r['tags']})"
        if r.get("image_path"):
            line += f" [이미지: {r['image_path']}]"
        lines.append(line)

    return "\n".join(lines)
