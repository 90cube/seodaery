"""에셋 CRUD 및 태그 연결 모듈 (SQLite).

에셋 온톨로지 시스템의 핵심 저장소.
에셋 등록·조회·삭제와 태그 연결·해제를 담당한다.
"""

import os
import sqlite3
import time
from pathlib import Path

ASSETS_DB_PATH = os.path.join(
    os.getenv("DB_DIR", os.path.join(os.path.dirname(__file__), os.pardir, "db")),
    "assets.db",
)


def get_assets_db() -> sqlite3.Connection:
    """assets.db 연결을 반환한다. 디렉터리가 없으면 생성한다."""
    Path(ASSETS_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(ASSETS_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_asset_tables(conn: sqlite3.Connection) -> None:
    """에셋 관련 테이블을 생성한다. 이미 존재하면 무시한다."""
    conn.executescript(_ASSET_SCHEMA_SQL)


_ASSET_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS assets (
    asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_type TEXT NOT NULL,
    folder_number TEXT DEFAULT '',
    folder_path TEXT DEFAULT '',
    file_name TEXT DEFAULT '',
    created_at REAL
);
CREATE TABLE IF NOT EXISTS tag_types (
    type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS tags (
    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_id INTEGER NOT NULL,
    value TEXT NOT NULL,
    FOREIGN KEY (type_id) REFERENCES tag_types(type_id),
    UNIQUE(type_id, value)
);
CREATE TABLE IF NOT EXISTS asset_tags (
    asset_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (asset_id, tag_id),
    FOREIGN KEY (asset_id) REFERENCES assets(asset_id),
    FOREIGN KEY (tag_id) REFERENCES tags(tag_id)
);
"""


# ── Asset CRUD ────────────────────────────────────────────


def insert_asset(
    conn: sqlite3.Connection,
    search_type: str,
    folder_number: str = "",
    folder_path: str = "",
    file_name: str = "",
) -> int:
    """새 에셋을 등록하고 asset_id를 반환한다."""
    cur = conn.execute(
        "INSERT INTO assets (search_type, folder_number, folder_path, "
        "file_name, created_at) VALUES (?, ?, ?, ?, ?)",
        (search_type, folder_number, folder_path, file_name, time.time()),
    )
    conn.commit()
    return cur.lastrowid


def get_asset(conn: sqlite3.Connection, asset_id: int) -> dict | None:
    """에셋 정보를 태그 목록과 함께 반환한다. 없으면 None."""
    row = conn.execute(
        "SELECT * FROM assets WHERE asset_id = ?", (asset_id,)
    ).fetchone()
    if row is None:
        return None
    asset = dict(row)
    asset["tags"] = get_asset_tags(conn, asset_id)
    return asset


def get_all_assets(conn: sqlite3.Connection) -> list[dict]:
    """전체 에셋 목록을 반환한다."""
    rows = conn.execute(
        "SELECT * FROM assets ORDER BY asset_id"
    ).fetchall()
    return [dict(r) for r in rows]


def get_assets_by_type(
    conn: sqlite3.Connection, search_type: str
) -> list[dict]:
    """특정 search_type의 에셋 목록을 반환한다."""
    rows = conn.execute(
        "SELECT * FROM assets WHERE search_type = ? ORDER BY asset_id",
        (search_type,),
    ).fetchall()
    return [dict(r) for r in rows]


def delete_asset(conn: sqlite3.Connection, asset_id: int) -> None:
    """에셋과 연결된 태그 관계를 모두 삭제한다."""
    conn.execute("DELETE FROM asset_tags WHERE asset_id = ?", (asset_id,))
    conn.execute("DELETE FROM assets WHERE asset_id = ?", (asset_id,))
    conn.commit()


# ── Tag linking ───────────────────────────────────────────


def link_tag(
    conn: sqlite3.Connection, asset_id: int, tag_id: int
) -> None:
    """에셋에 태그를 연결한다. 이미 연결돼 있으면 무시한다."""
    conn.execute(
        "INSERT OR IGNORE INTO asset_tags (asset_id, tag_id) VALUES (?, ?)",
        (asset_id, tag_id),
    )
    conn.commit()


def unlink_tag(
    conn: sqlite3.Connection, asset_id: int, tag_id: int
) -> None:
    """에셋에서 태그 연결을 해제한다."""
    conn.execute(
        "DELETE FROM asset_tags WHERE asset_id = ? AND tag_id = ?",
        (asset_id, tag_id),
    )
    conn.commit()


def get_asset_tags(conn: sqlite3.Connection, asset_id: int) -> list[dict]:
    """에셋에 연결된 태그 목록을 {type_name, value} 형태로 반환한다."""
    rows = conn.execute(
        "SELECT tt.type_name, t.value "
        "FROM asset_tags at_ "
        "JOIN tags t ON at_.tag_id = t.tag_id "
        "JOIN tag_types tt ON t.type_id = tt.type_id "
        "WHERE at_.asset_id = ? ORDER BY tt.type_name, t.value",
        (asset_id,),
    ).fetchall()
    return [{"type_name": r["type_name"], "value": r["value"]} for r in rows]
