"""패치 일정 + 담당자 배정 CRUD. events.db 사용."""

import json
import sqlite3
import time
from pathlib import Path

from server.config.constants import DB_DIR, EVENT_DB_NAME

EVENT_DB_PATH = str(Path(DB_DIR) / EVENT_DB_NAME)


# ── 연결 ─────────────────────────────────────────────────


def get_event_db() -> sqlite3.Connection:
    """이벤트 전용 DB 연결을 반환한다."""
    Path(EVENT_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(EVENT_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


_PATCH_SCHEMA = """
CREATE TABLE IF NOT EXISTS patch_schedules (
    patch_id      TEXT PRIMARY KEY,
    title         TEXT NOT NULL,
    patch_date    TEXT NOT NULL,
    description   TEXT DEFAULT '',
    art_share_date        TEXT,
    concept_share_date    TEXT,
    illustration_done_date TEXT,
    modeling_start_date   TEXT,
    modeling_done_date    TEXT,
    extra_info    TEXT DEFAULT '{}',
    file_path     TEXT,
    created_by    TEXT NOT NULL,
    created_at    REAL,
    updated_at    REAL
);

CREATE TABLE IF NOT EXISTS patch_assignments (
    assignment_id    TEXT PRIMARY KEY,
    patch_id         TEXT NOT NULL,
    user_id          TEXT NOT NULL,
    user_name        TEXT NOT NULL,
    role             TEXT NOT NULL,
    task_description TEXT DEFAULT '',
    created_at       REAL,
    FOREIGN KEY (patch_id) REFERENCES patch_schedules(patch_id)
);
"""


def init_patch_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(_PATCH_SCHEMA)


# ── 패치 일정 CRUD ──────────────────────────────────────


def create_patch(conn: sqlite3.Connection, patch_id: str, **kw) -> None:
    now = time.time()
    conn.execute(
        """INSERT INTO patch_schedules
           (patch_id, title, patch_date, description,
            art_share_date, concept_share_date,
            illustration_done_date, modeling_start_date, modeling_done_date,
            extra_info, file_path, created_by, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            patch_id,
            kw["title"], kw["patch_date"], kw.get("description", ""),
            kw.get("art_share_date"), kw.get("concept_share_date"),
            kw.get("illustration_done_date"),
            kw.get("modeling_start_date"), kw.get("modeling_done_date"),
            json.dumps(kw.get("extra_info", {}), ensure_ascii=False),
            kw.get("file_path"), kw["created_by"], now, now,
        ),
    )
    conn.commit()


def get_patch(conn: sqlite3.Connection, patch_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM patch_schedules WHERE patch_id = ?", (patch_id,)
    ).fetchone()
    return _patch_to_dict(row) if row else None


def list_patches(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM patch_schedules ORDER BY patch_date DESC"
    ).fetchall()
    return [_patch_to_dict(r) for r in rows]


def delete_patch(conn: sqlite3.Connection, patch_id: str) -> bool:
    cur = conn.execute(
        "DELETE FROM patch_schedules WHERE patch_id = ?", (patch_id,)
    )
    conn.commit()
    return cur.rowcount > 0


# ── 담당자 배정 CRUD ────────────────────────────────────


def create_assignment(conn: sqlite3.Connection, assignment_id: str, **kw) -> None:
    conn.execute(
        """INSERT INTO patch_assignments
           (assignment_id, patch_id, user_id, user_name, role,
            task_description, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (
            assignment_id, kw["patch_id"], kw["user_id"],
            kw["user_name"], kw["role"],
            kw.get("task_description", ""), time.time(),
        ),
    )
    conn.commit()


def get_assignments_by_patch(conn: sqlite3.Connection, patch_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM patch_assignments WHERE patch_id = ? ORDER BY created_at",
        (patch_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_assignments_by_user(conn: sqlite3.Connection, user_id: str) -> list[dict]:
    rows = conn.execute(
        """SELECT a.*, p.title AS patch_title, p.patch_date
           FROM patch_assignments a
           JOIN patch_schedules p ON a.patch_id = p.patch_id
           WHERE a.user_id = ?
           ORDER BY p.patch_date""",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def search_assignment(
    conn: sqlite3.Connection,
    *,
    role: str | None = None,
    patch_date: str | None = None,
    task_keyword: str | None = None,
) -> list[dict]:
    """역할·패치일·작업 키워드로 담당자를 검색한다."""
    sql = """SELECT a.*, p.title AS patch_title, p.patch_date
             FROM patch_assignments a
             JOIN patch_schedules p ON a.patch_id = p.patch_id
             WHERE 1=1"""
    params: list = []
    if role:
        sql += " AND a.role = ?"
        params.append(role)
    if patch_date:
        sql += " AND p.patch_date = ?"
        params.append(patch_date)
    if task_keyword:
        sql += " AND a.task_description LIKE ?"
        params.append(f"%{task_keyword}%")
    sql += " ORDER BY p.patch_date"
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def delete_assignment(conn: sqlite3.Connection, assignment_id: str) -> bool:
    cur = conn.execute(
        "DELETE FROM patch_assignments WHERE assignment_id = ?",
        (assignment_id,),
    )
    conn.commit()
    return cur.rowcount > 0


# ── 헬퍼 ─────────────────────────────────────────────────


def _patch_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["extra_info"] = json.loads(d.get("extra_info", "{}"))
    return d
