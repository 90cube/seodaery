"""벡터 저장소. sqlite-vss 기반 벡터 검색.

에셋 임베딩 벡터를 저장하고 유사도 검색을 수행한다.
sqlite-vss 미설치 시 벡터 검색 기능만 비활성화된다.
"""

import json
import logging
import os
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger(__name__)

VECTOR_DB_PATH = os.path.join(
    os.getenv("DB_DIR", os.path.join(os.path.dirname(__file__), os.pardir, "db")),
    "vectors.db",
)

_vss_available = False


def get_vector_db() -> sqlite3.Connection:
    """vectors.db 연결을 반환한다. sqlite-vss 로드를 시도한다."""
    global _vss_available
    Path(VECTOR_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(VECTOR_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.enable_load_extension(True)
        import sqlite_vss

        sqlite_vss.load(conn)
        _vss_available = True
    except Exception as e:
        logger.warning("sqlite-vss 로드 실패 (벡터 검색 비활성): %s", e)
    return conn


def init_vector_tables(conn: sqlite3.Connection) -> None:
    """벡터 관련 테이블을 생성한다. 이미 존재하면 무시한다."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id INTEGER NOT NULL,
            embed_type TEXT NOT NULL,
            vector_json TEXT NOT NULL DEFAULT '[]',
            file_path TEXT DEFAULT '',
            created_at REAL
        );
        CREATE INDEX IF NOT EXISTS idx_emb_asset
            ON embeddings(asset_id, embed_type);
    """)
    if _vss_available:
        try:
            conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS "
                "vss_embeddings USING vss0(embedding(512))"
            )
        except Exception:
            pass
    conn.commit()


def store_embedding(
    conn: sqlite3.Connection,
    asset_id: int,
    embed_type: str,
    vector: list[float],
    file_path: str = "",
) -> int:
    """임베딩 벡터를 저장한다. embeddings + vss 테이블 모두 기록."""
    vec_json = json.dumps(vector)
    cur = conn.execute(
        "INSERT INTO embeddings (asset_id, embed_type, vector_json, "
        "file_path, created_at) VALUES (?, ?, ?, ?, ?)",
        (asset_id, embed_type, vec_json, file_path, time.time()),
    )
    row_id = cur.lastrowid
    if _vss_available:
        try:
            conn.execute(
                "INSERT INTO vss_embeddings (rowid, embedding) VALUES (?, ?)",
                (row_id, vec_json),
            )
        except Exception as e:
            logger.warning("vss 삽입 실패 (rowid=%d): %s", row_id, e)
    conn.commit()
    return row_id


def search_similar(
    conn: sqlite3.Connection,
    query_vector: list[float],
    limit: int = 10,
    embed_type: str | None = None,
) -> list[dict]:
    """벡터 유사도 검색. asset_id, distance, file_path를 반환한다."""
    if not _vss_available:
        return []
    vec_json = json.dumps(query_vector)
    try:
        vss_rows = conn.execute(
            "SELECT rowid, distance FROM vss_embeddings "
            "WHERE vss_search(embedding, ?) LIMIT ?",
            (vec_json, limit * 3),
        ).fetchall()
    except Exception as e:
        logger.warning("vss 검색 실패: %s", e)
        return []

    row_ids = [r["rowid"] for r in vss_rows]
    dist_map = {r["rowid"]: r["distance"] for r in vss_rows}
    if not row_ids:
        return []

    placeholders = ",".join("?" * len(row_ids))
    type_clause = "AND embed_type = ?" if embed_type else ""
    params = row_ids + ([embed_type] if embed_type else [])

    rows = conn.execute(
        f"SELECT id, asset_id, file_path, embed_type FROM embeddings "
        f"WHERE id IN ({placeholders}) {type_clause}",
        params,
    ).fetchall()

    results = []
    for r in rows:
        results.append({
            "asset_id": r["asset_id"],
            "distance": dist_map.get(r["id"], 999.0),
            "file_path": r["file_path"],
            "embed_type": r["embed_type"],
        })
    results.sort(key=lambda x: x["distance"])
    return results[:limit]


def delete_embedding(conn: sqlite3.Connection, asset_id: int) -> None:
    """특정 에셋의 임베딩을 모두 삭제한다."""
    rows = conn.execute(
        "SELECT id FROM embeddings WHERE asset_id = ?", (asset_id,)
    ).fetchall()
    for r in rows:
        if _vss_available:
            try:
                conn.execute(
                    "DELETE FROM vss_embeddings WHERE rowid = ?", (r["id"],)
                )
            except Exception:
                pass
    conn.execute("DELETE FROM embeddings WHERE asset_id = ?", (asset_id,))
    conn.commit()


def is_indexed(
    conn: sqlite3.Connection, asset_id: int, embed_type: str
) -> bool:
    """해당 에셋이 이미 인덱싱되었는지 확인한다."""
    row = conn.execute(
        "SELECT 1 FROM embeddings WHERE asset_id = ? AND embed_type = ? LIMIT 1",
        (asset_id, embed_type),
    ).fetchone()
    return row is not None


def is_vss_available() -> bool:
    """sqlite-vss 사용 가능 여부를 반환한다."""
    return _vss_available
