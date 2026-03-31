"""태그 기반 에셋 검색 도메인 로직.

에셋 온톨로지의 검색 기능을 담당한다.
태그 조합 검색, 별칭 검색, 스킨 그룹, 호환 파츠, 세트 구성을 제공한다.
"""

from __future__ import annotations

import logging
import sqlite3

from server.data.asset_store import get_asset, get_asset_tags
from server.data.tag_store import get_tag_id, search_tags

logger = logging.getLogger(__name__)


def search_by_tags(
    conn: sqlite3.Connection, tag_filters: dict[str, str]
) -> list[dict]:
    """태그 조합으로 에셋을 검색한다.

    Args:
        conn: SQLite 연결 객체.
        tag_filters: {type_name: value} 형태의 태그 필터.

    Returns:
        매칭된 에셋 딕셔너리 목록. 각 에셋에 tags 키가 포함된다.
    """
    if not tag_filters:
        return []

    joins: list[str] = []
    conditions: list[str] = []
    params: list[str] = []

    for idx, (type_name, value) in enumerate(tag_filters.items()):
        alias_at = f"at{idx}"
        alias_t = f"t{idx}"
        alias_tt = f"tt{idx}"

        joins.append(
            f"JOIN asset_tags {alias_at} ON a.asset_id = {alias_at}.asset_id "
            f"JOIN tags {alias_t} ON {alias_at}.tag_id = {alias_t}.tag_id "
            f"JOIN tag_types {alias_tt} ON {alias_t}.type_id = {alias_tt}.type_id"
        )
        conditions.append(f"{alias_tt}.type_name = ? AND {alias_t}.value = ?")
        params.extend([type_name, value])

    sql = (
        "SELECT DISTINCT a.* FROM assets a "
        + " ".join(joins)
        + " WHERE "
        + " AND ".join(conditions)
        + " ORDER BY a.asset_id"
    )

    rows = conn.execute(sql, params).fetchall()
    results = []
    for row in rows:
        asset = dict(row)
        asset["tags"] = get_asset_tags(conn, asset["asset_id"])
        results.append(asset)
    return results


def search_by_alias(
    conn: sqlite3.Connection, alias: str
) -> list[dict]:
    """별칭으로 에셋을 검색한다.

    Args:
        conn: SQLite 연결 객체.
        alias: 검색할 별칭 문자열 (부분 일치).

    Returns:
        매칭된 에셋 딕셔너리 목록.
    """
    rows = conn.execute(
        "SELECT DISTINCT a.* FROM assets a "
        "JOIN asset_tags at_ ON a.asset_id = at_.asset_id "
        "JOIN tags t ON at_.tag_id = t.tag_id "
        "JOIN tag_types tt ON t.type_id = tt.type_id "
        "WHERE tt.type_name = 'alias' AND t.value LIKE ? "
        "ORDER BY a.asset_id",
        (f"%{alias}%",),
    ).fetchall()

    results = []
    for row in rows:
        asset = dict(row)
        asset["tags"] = get_asset_tags(conn, asset["asset_id"])
        results.append(asset)
    return results


def get_weapon_skins(
    conn: sqlite3.Connection, weapon_base: str
) -> list[dict]:
    """weapon_base 기준 스킨 그룹을 반환한다.

    Args:
        conn: SQLite 연결 객체.
        weapon_base: 무기 베이스 이름 (예: 'AK47').

    Returns:
        스킨 태그별로 그룹화된 에셋 목록.
    """
    assets = search_by_tags(conn, {"weapon_base": weapon_base})
    groups: dict[str, list[dict]] = {}

    for asset in assets:
        skin_value = ""
        for tag in asset.get("tags", []):
            if tag["type_name"] == "skin":
                skin_value = tag["value"]
                break
        groups.setdefault(skin_value or "(기본)", []).append(asset)

    result = []
    for skin_name, members in groups.items():
        result.append({"skin": skin_name, "assets": members})
    return result


def get_compatible_parts(
    conn: sqlite3.Connection, asset_id: int
) -> list[dict]:
    """호환 가능한 파츠 목록을 반환한다.

    기준 에셋의 patch_routine + patch_date 태그가 동일한 에셋을 찾고,
    compat_override 테이블이 존재하면 추가 필터링한다.

    Args:
        conn: SQLite 연결 객체.
        asset_id: 기준 에셋 ID.

    Returns:
        호환 가능한 에셋 딕셔너리 목록.
    """
    source = get_asset(conn, asset_id)
    if source is None:
        return []

    tags = source.get("tags", [])
    tag_map = {t["type_name"]: t["value"] for t in tags}

    patch_routine = tag_map.get("patch_routine")
    patch_date = tag_map.get("patch_date")

    if not patch_routine or not patch_date:
        return []

    candidates = search_by_tags(
        conn, {"patch_routine": patch_routine, "patch_date": patch_date}
    )

    # compat_override 테이블 존재 시 제외 목록 적용
    excluded: set[int] = set()
    try:
        rows = conn.execute(
            "SELECT blocked_asset_id FROM compat_override "
            "WHERE asset_id = ?",
            (asset_id,),
        ).fetchall()
        excluded = {r[0] for r in rows}
    except Exception:
        pass  # 테이블 미존재 시 무시

    return [
        c for c in candidates
        if c["asset_id"] != asset_id and c["asset_id"] not in excluded
    ]


def get_character_set(
    conn: sqlite3.Connection, set_group_id: str
) -> list[dict]:
    """세트 그룹 ID로 세트 구성원을 반환한다.

    Args:
        conn: SQLite 연결 객체.
        set_group_id: 세트 그룹 식별자.

    Returns:
        세트에 속한 에셋 딕셔너리 목록.
    """
    return search_by_tags(conn, {"set_group_id": set_group_id})
