"""벡터+태그 복합 검색. 시맨틱 검색과 태그 필터를 결합한다.

CLIP 벡터 유사도 검색과 기존 태그 기반 검색을 결합하여
멀티모달 에셋 검색을 수행한다. 외부 프레임워크 직접 호출 없음.
"""

from __future__ import annotations

import logging

from server.data.asset_store import get_all_assets, get_asset, get_assets_db
from server.domain.asset_search import search_by_tags
from server.system.embedding_client import (
    embed_text_clip,
    is_available,
)
from server.system.vector_store import (
    get_vector_db,
    init_vector_tables,
    is_vss_available,
    search_similar,
)

logger = logging.getLogger(__name__)

_UNAVAILABLE_MSG = "벡터 검색 현재 불가"
_EMBED_FAIL_MSG = "임베딩 생성 실패"


def search_by_vector(query: str, limit: int = 10) -> dict:
    """텍스트 쿼리로 벡터 유사도 검색을 수행한다.

    Args:
        query: 검색 텍스트 (CLIP 임베딩으로 변환).
        limit: 최대 결과 수.

    Returns:
        available, results, message 키를 포함하는 딕셔너리.
    """
    if not is_available("clip") or not is_vss_available():
        return {"available": False, "results": [], "message": _UNAVAILABLE_MSG}

    vec = embed_text_clip(query)
    if not vec:
        return {"available": False, "results": [], "message": _EMBED_FAIL_MSG}

    conn_vec = get_vector_db()
    init_vector_tables(conn_vec)
    raw = search_similar(conn_vec, vec, limit=limit, embed_type="clip")
    conn_vec.close()

    conn_asset = get_assets_db()
    results = _enrich_results(conn_asset, raw)
    conn_asset.close()

    return {"available": True, "results": results, "message": ""}


def search_combined(
    query: str,
    tag_filters: dict[str, str] | None = None,
    limit: int = 10,
) -> dict:
    """벡터 유사도 + 태그 필터 결합 검색을 수행한다.

    Args:
        query: 검색 텍스트.
        tag_filters: {type_name: value} 태그 필터. None이면 벡터만.
        limit: 최대 결과 수.

    Returns:
        available, results, message 키를 포함하는 딕셔너리.
    """
    vector_result = search_by_vector(query, limit=limit * 2)
    vector_ids = {r["asset_id"] for r in vector_result.get("results", [])}
    vector_map = {
        r["asset_id"]: r for r in vector_result.get("results", [])
    }

    if not tag_filters:
        return {
            "available": vector_result["available"],
            "results": vector_result["results"][:limit],
            "message": vector_result["message"],
        }

    conn_asset = get_assets_db()
    tag_results = search_by_tags(conn_asset, tag_filters)
    conn_asset.close()
    tag_ids = {a["asset_id"] for a in tag_results}

    if not vector_result["available"]:
        return {
            "available": False,
            "results": tag_results[:limit],
            "message": "태그 필터만 적용됨 (벡터 검색 불가)",
        }

    intersected = vector_ids & tag_ids
    combined = [
        vector_map[aid] for aid in intersected if aid in vector_map
    ]
    combined.sort(key=lambda x: x.get("distance", 999.0))

    return {
        "available": True,
        "results": combined[:limit],
        "message": "",
    }


def get_search_status() -> dict:
    """검색 시스템 상태를 반환한다."""
    return {
        "clip_available": is_available("clip"),
        "text_embedding_available": is_available("text"),
        "vss_available": is_vss_available(),
    }


def _enrich_results(
    conn_asset, raw_results: list[dict]
) -> list[dict]:
    """벡터 검색 결과에 에셋 정보를 추가한다."""
    enriched = []
    for item in raw_results:
        asset = get_asset(conn_asset, item["asset_id"])
        if asset is None:
            continue
        enriched.append({
            "asset_id": item["asset_id"],
            "distance": item["distance"],
            "file_path": item.get("file_path", ""),
            "file_name": asset.get("file_name", ""),
            "folder_path": asset.get("folder_path", ""),
            "tags": asset.get("tags", []),
        })
    return enriched
