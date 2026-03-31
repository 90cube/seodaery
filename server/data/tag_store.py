"""태그 및 태그 타입 CRUD 모듈 (SQLite).

에셋 온톨로지의 분류 체계를 관리한다.
태그 타입 생성, 태그 생성·검색, 별칭 등록을 담당한다.
"""

import sqlite3

from server.data.asset_store import link_tag

# ── 프리셋 태그 타입 ─────────────────────────────────────

PRESET_TAG_TYPES = [
    "patch_routine",
    "patch_date",
    "work_stage",
    "variant",
    "alias",
    "weapon_class",
    "weapon_group",
    "weapon_base",
    "skin",
    "grade",
    "character_class",
    "style",
    "season",
    "concept",
    "set",
    "asset_combine_type",
    "parts_slot",
    "set_group_id",
    "item_type",
]


def seed_tag_types(conn: sqlite3.Connection) -> None:
    """프리셋 태그 타입을 모두 등록한다. 이미 존재하면 무시한다."""
    for name in PRESET_TAG_TYPES:
        ensure_tag_type(conn, name)


# ── TagType CRUD ──────────────────────────────────────────


def ensure_tag_type(conn: sqlite3.Connection, type_name: str) -> int:
    """태그 타입을 보장하고 type_id를 반환한다. 없으면 생성한다."""
    conn.execute(
        "INSERT OR IGNORE INTO tag_types (type_name) VALUES (?)",
        (type_name,),
    )
    conn.commit()
    row = conn.execute(
        "SELECT type_id FROM tag_types WHERE type_name = ?",
        (type_name,),
    ).fetchone()
    return row["type_id"]


def get_all_tag_types(conn: sqlite3.Connection) -> list[dict]:
    """전체 태그 타입 목록을 반환한다."""
    rows = conn.execute(
        "SELECT * FROM tag_types ORDER BY type_name"
    ).fetchall()
    return [dict(r) for r in rows]


# ── Tag CRUD ──────────────────────────────────────────────


def ensure_tag(
    conn: sqlite3.Connection, type_name: str, value: str
) -> int:
    """태그를 보장하고 tag_id를 반환한다. 타입과 태그 모두 없으면 생성한다."""
    type_id = ensure_tag_type(conn, type_name)
    conn.execute(
        "INSERT OR IGNORE INTO tags (type_id, value) VALUES (?, ?)",
        (type_id, value),
    )
    conn.commit()
    row = conn.execute(
        "SELECT tag_id FROM tags WHERE type_id = ? AND value = ?",
        (type_id, value),
    ).fetchone()
    return row["tag_id"]


def get_tags_by_type(
    conn: sqlite3.Connection, type_name: str
) -> list[str]:
    """특정 태그 타입에 속한 모든 태그 값 목록을 반환한다."""
    rows = conn.execute(
        "SELECT t.value FROM tags t "
        "JOIN tag_types tt ON t.type_id = tt.type_id "
        "WHERE tt.type_name = ? ORDER BY t.value",
        (type_name,),
    ).fetchall()
    return [r["value"] for r in rows]


def search_tags(conn: sqlite3.Connection, query: str) -> list[dict]:
    """값에 query가 포함된 태그를 검색한다. LIKE %query% 사용."""
    rows = conn.execute(
        "SELECT tt.type_name, t.tag_id, t.value FROM tags t "
        "JOIN tag_types tt ON t.type_id = tt.type_id "
        "WHERE t.value LIKE ? ORDER BY tt.type_name, t.value",
        (f"%{query}%",),
    ).fetchall()
    return [
        {"tag_id": r["tag_id"], "type_name": r["type_name"], "value": r["value"]}
        for r in rows
    ]


def get_tag_id(
    conn: sqlite3.Connection, type_name: str, value: str
) -> int | None:
    """태그 ID를 반환한다. 존재하지 않으면 None."""
    row = conn.execute(
        "SELECT t.tag_id FROM tags t "
        "JOIN tag_types tt ON t.type_id = tt.type_id "
        "WHERE tt.type_name = ? AND t.value = ?",
        (type_name, value),
    ).fetchone()
    return row["tag_id"] if row else None


# ── 별칭 등록 ─────────────────────────────────────────────


def add_alias(
    conn: sqlite3.Connection, asset_id: int, alias: str
) -> None:
    """에셋에 별칭 태그를 등록한다. alias 태그 타입 + link_tag 단축 함수."""
    tag_id = ensure_tag(conn, "alias", alias)
    link_tag(conn, asset_id, tag_id)
