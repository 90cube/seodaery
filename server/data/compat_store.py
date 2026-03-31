"""캐릭터 호환성 규칙 및 오버라이드 모듈 (SQLite).

에셋 간 장착 호환성을 판정한다.
명시적 오버라이드(허용/차단)와 태그 기반 자동 판정을 제공한다.
"""

import sqlite3

from server.data.asset_store import get_asset_tags


def init_compat_tables(conn: sqlite3.Connection) -> None:
    """호환성 오버라이드 테이블을 생성한다. 이미 존재하면 무시한다."""
    conn.executescript(_COMPAT_SCHEMA_SQL)


_COMPAT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS compat_override (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_a INTEGER NOT NULL,
    asset_b INTEGER NOT NULL,
    override TEXT NOT NULL CHECK(override IN ('allow', 'block')),
    note TEXT DEFAULT '',
    FOREIGN KEY (asset_a) REFERENCES assets(asset_id),
    FOREIGN KEY (asset_b) REFERENCES assets(asset_id)
);
"""


# ── Override CRUD ─────────────────────────────────────────


def add_override(
    conn: sqlite3.Connection,
    asset_a: int,
    asset_b: int,
    override: str,
    note: str = "",
) -> int:
    """호환성 오버라이드를 추가하고 id를 반환한다."""
    cur = conn.execute(
        "INSERT INTO compat_override (asset_a, asset_b, override, note) "
        "VALUES (?, ?, ?, ?)",
        (asset_a, asset_b, override, note),
    )
    conn.commit()
    return cur.lastrowid


def get_overrides(conn: sqlite3.Connection, asset_id: int) -> list[dict]:
    """특정 에셋이 관련된 모든 오버라이드를 반환한다."""
    rows = conn.execute(
        "SELECT * FROM compat_override "
        "WHERE asset_a = ? OR asset_b = ? ORDER BY id",
        (asset_id, asset_id),
    ).fetchall()
    return [dict(r) for r in rows]


def remove_override(conn: sqlite3.Connection, override_id: int) -> None:
    """오버라이드를 삭제한다."""
    conn.execute(
        "DELETE FROM compat_override WHERE id = ?", (override_id,)
    )
    conn.commit()


# ── 호환성 판정 ───────────────────────────────────────────


def _tags_to_map(tags: list[dict]) -> dict[str, list[str]]:
    """태그 목록을 {type_name: [value, ...]} 맵으로 변환한다."""
    result: dict[str, list[str]] = {}
    for t in tags:
        result.setdefault(t["type_name"], []).append(t["value"])
    return result


def _check_override(
    conn: sqlite3.Connection, asset_a: int, asset_b: int
) -> dict | None:
    """명시적 오버라이드가 있으면 판정 결과를 반환한다. 없으면 None."""
    row = conn.execute(
        "SELECT override, note FROM compat_override "
        "WHERE (asset_a = ? AND asset_b = ?) "
        "OR (asset_a = ? AND asset_b = ?) LIMIT 1",
        (asset_a, asset_b, asset_b, asset_a),
    ).fetchone()
    if row is None:
        return None
    is_allow = row["override"] == "allow"
    reason = row["note"] if row["note"] else f"명시적 {'허용' if is_allow else '차단'}"
    return {"compatible": is_allow, "reason": reason}


def _check_combine_type(
    map_a: dict[str, list[str]], map_b: dict[str, list[str]]
) -> dict | None:
    """통짜 에셋이면 비호환 판정을 반환한다."""
    for label, tag_map in [("A", map_a), ("B", map_b)]:
        if "통짜" in tag_map.get("asset_combine_type", []):
            return {
                "compatible": False,
                "reason": f"에셋 {label}이(가) 통짜 타입으로 조합 불가",
            }
    return None


def _check_set_conflict(
    map_a: dict[str, list[str]], map_b: dict[str, list[str]]
) -> dict | None:
    """세트 에셋 간 parts_slot 충돌을 검사한다. 헤어만 교차 허용."""
    combine_a = map_a.get("asset_combine_type", [])
    combine_b = map_b.get("asset_combine_type", [])
    if "세트" not in combine_a or "세트" not in combine_b:
        return None
    slots_a = set(map_a.get("parts_slot", []))
    slots_b = set(map_b.get("parts_slot", []))
    overlap = slots_a & slots_b
    allowed_overlap = {"헤어"}
    conflict = overlap - allowed_overlap
    if conflict:
        return {
            "compatible": False,
            "reason": f"세트 간 슬롯 충돌: {', '.join(sorted(conflict))}",
        }
    return None


def _check_patch_season(
    map_a: dict[str, list[str]], map_b: dict[str, list[str]]
) -> dict | None:
    """패치 루틴·날짜 일치 또는 같은 시즌(서든패스)이면 호환 판정."""
    routine_a = set(map_a.get("patch_routine", []))
    routine_b = set(map_b.get("patch_routine", []))
    date_a = set(map_a.get("patch_date", []))
    date_b = set(map_b.get("patch_date", []))
    if routine_a & routine_b and date_a & date_b:
        return {
            "compatible": True,
            "reason": "동일 패치 루틴·날짜 일치",
        }
    season_a = set(map_a.get("season", []))
    season_b = set(map_b.get("season", []))
    if season_a & season_b:
        pass_a = "서든패스" in routine_a
        pass_b = "서든패스" in routine_b
        if pass_a or pass_b:
            return {
                "compatible": True,
                "reason": f"동일 시즌 서든패스: {', '.join(season_a & season_b)}",
            }
    return None


def check_compatibility(
    conn: sqlite3.Connection, asset_a_id: int, asset_b_id: int
) -> dict:
    """두 에셋의 호환성을 판정한다.

    판정 우선순위:
      1. 명시적 오버라이드 (allow/block)
      2. 통짜 타입 → 비호환
      3. 세트 간 parts_slot 충돌 (헤어만 교차 허용)
      4. 패치 루틴+날짜 일치 또는 같은 시즌 서든패스 → 호환
      5. 기본값 → 비호환
    """
    override = _check_override(conn, asset_a_id, asset_b_id)
    if override:
        return override

    tags_a = get_asset_tags(conn, asset_a_id)
    tags_b = get_asset_tags(conn, asset_b_id)
    map_a = _tags_to_map(tags_a)
    map_b = _tags_to_map(tags_b)

    for checker in (_check_combine_type, _check_set_conflict, _check_patch_season):
        result = checker(map_a, map_b)
        if result:
            return result

    return {"compatible": False, "reason": "기본 규칙: 명시적 허용 조건 미충족"}
