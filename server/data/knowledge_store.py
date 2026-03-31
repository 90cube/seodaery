"""글로벌 지식 DB 데이터 레이어 — 캐릭터·무기·아이템·패치 등 게임 데이터 저장/검색."""

import os
import sqlite3
import time
from pathlib import Path

DB_PATH = os.path.join(os.getenv("DB_DIR", "db"), "knowledge.db")
ASSETS_DIR = os.getenv("ASSETS_DIR", "assets")

_COLUMNS = ("id", "category", "title", "description", "tags", "image_path")

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '',
    image_path TEXT DEFAULT NULL,
    created_at REAL,
    updated_at REAL
);
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    title, description, tags,
    content='knowledge',
    content_rowid='id'
);
CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
    INSERT INTO knowledge_fts(rowid, title, description, tags)
    VALUES (new.id, new.title, new.description, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
    INSERT INTO knowledge_fts(knowledge_fts, rowid, title, description, tags)
    VALUES ('delete', old.id, old.title, old.description, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge BEGIN
    INSERT INTO knowledge_fts(knowledge_fts, rowid, title, description, tags)
    VALUES ('delete', old.id, old.title, old.description, old.tags);
    INSERT INTO knowledge_fts(rowid, title, description, tags)
    VALUES (new.id, new.title, new.description, new.tags);
END;
"""

_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def _row_to_dict(row: tuple) -> dict:
    """DB 행을 딕셔너리로 변환한다."""
    return dict(zip(_COLUMNS, row))


def _rows_to_dicts(rows: list[tuple]) -> list[dict]:
    """DB 행 목록을 딕셔너리 리스트로 변환한다."""
    return [_row_to_dict(r) for r in rows]


def get_knowledge_db() -> sqlite3.Connection:
    """글로벌 지식 DB 연결을 반환한다."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_knowledge_tables(conn: sqlite3.Connection) -> None:
    """지식 DB 테이블 + FTS5 인덱스를 생성한다."""
    conn.executescript(_SCHEMA_SQL)
    conn.commit()


def insert_knowledge(
    conn: sqlite3.Connection,
    category: str,
    title: str,
    description: str = "",
    tags: str = "",
    image_path: str | None = None,
) -> int:
    """지식 항목을 추가하고 id를 반환한다."""
    now = time.time()
    cur = conn.execute(
        "INSERT INTO knowledge "
        "(category, title, description, tags, image_path, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (category, title, description, tags, image_path, now, now),
    )
    conn.commit()
    return cur.lastrowid


def update_knowledge(
    conn: sqlite3.Connection,
    knowledge_id: int,
    category: str,
    title: str,
    description: str,
    tags: str,
    image_path: str | None = None,
) -> None:
    """지식 항목을 수정한다."""
    conn.execute(
        "UPDATE knowledge "
        "SET category=?, title=?, description=?, tags=?, image_path=?, updated_at=? "
        "WHERE id=?",
        (category, title, description, tags, image_path, time.time(), knowledge_id),
    )
    conn.commit()


def delete_knowledge(conn: sqlite3.Connection, knowledge_id: int) -> None:
    """지식 항목을 삭제한다."""
    conn.execute("DELETE FROM knowledge WHERE id=?", (knowledge_id,))
    conn.commit()


def search_knowledge(
    conn: sqlite3.Connection, query: str, limit: int = 20
) -> list[dict]:
    """FTS5 전문 검색으로 지식을 검색한다."""
    rows = conn.execute(
        "SELECT k.id, k.category, k.title, k.description, k.tags, k.image_path "
        "FROM knowledge_fts f JOIN knowledge k ON f.rowid = k.id "
        "WHERE knowledge_fts MATCH ? ORDER BY rank LIMIT ?",
        (query, limit),
    ).fetchall()
    return _rows_to_dicts(rows)


def get_all_knowledge(conn: sqlite3.Connection) -> list[dict]:
    """모든 지식 항목을 반환한다."""
    rows = conn.execute(
        "SELECT id, category, title, description, tags, image_path "
        "FROM knowledge ORDER BY category, title"
    ).fetchall()
    return _rows_to_dicts(rows)


def get_by_category(
    conn: sqlite3.Connection, category: str
) -> list[dict]:
    """카테고리별 지식 항목을 반환한다."""
    rows = conn.execute(
        "SELECT id, category, title, description, tags, image_path "
        "FROM knowledge WHERE category=? ORDER BY title",
        (category,),
    ).fetchall()
    return _rows_to_dicts(rows)


def get_categories(conn: sqlite3.Connection) -> list[str]:
    """등록된 카테고리 목록을 반환한다."""
    rows = conn.execute(
        "SELECT DISTINCT category FROM knowledge ORDER BY category"
    ).fetchall()
    return [r[0] for r in rows]


def find_image(title: str) -> str | None:
    """title과 일치하는 이미지 파일을 assets 디렉터리에서 찾는다."""
    assets = Path(ASSETS_DIR)
    if not assets.exists():
        return None
    for ext in _IMAGE_EXTENSIONS:
        path = assets / f"{title}{ext}"
        if path.exists():
            return str(path)
    return None
