"""스킬 정의 CRUD 모듈 (SQLite).

스킬은 9B 모델을 위한 지시 세트이며, tools.db에 저장된다.
각 스킬은 이름, 설명, 프롬프트 텍스트(instruction), 트리거 키워드를 가진다.
"""

import json
import sqlite3
import time

from server.data.tool_registry import get_tools_db, init_tool_tables

_SKILL_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS skills (
    skill_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    instruction TEXT NOT NULL DEFAULT '',
    trigger_keywords TEXT NOT NULL DEFAULT '[]',
    enabled INTEGER DEFAULT 1,
    created_at REAL
);
"""


def init_skill_table(conn: sqlite3.Connection) -> None:
    """스킬 테이블을 생성한다. 이미 존재하면 무시한다."""
    conn.executescript(_SKILL_SCHEMA_SQL)


def _parse_skill_row(row: sqlite3.Row) -> dict:
    """DB 행을 딕셔너리로 변환한다. trigger_keywords를 리스트로 파싱한다."""
    d = dict(row)
    raw = d.get("trigger_keywords", "[]")
    d["trigger_keywords"] = json.loads(raw) if raw else []
    return d


# ── Skill CRUD ─────────────────────────────────────────────


def add_skill(
    conn: sqlite3.Connection,
    skill_id: str,
    name: str,
    description: str = "",
    instruction: str = "",
    trigger_keywords: list[str] | None = None,
) -> None:
    """새 스킬을 등록한다."""
    kw_json = json.dumps(trigger_keywords or [], ensure_ascii=False)
    conn.execute(
        "INSERT INTO skills "
        "(skill_id, name, description, instruction, trigger_keywords, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (skill_id, name, description, instruction, kw_json, time.time()),
    )
    conn.commit()


def get_skill(conn: sqlite3.Connection, skill_id: str) -> dict | None:
    """스킬 정보를 반환한다. 없으면 None."""
    row = conn.execute(
        "SELECT * FROM skills WHERE skill_id = ?", (skill_id,)
    ).fetchone()
    if row is None:
        return None
    return _parse_skill_row(row)


def get_all_skills(conn: sqlite3.Connection) -> list[dict]:
    """모든 스킬 목록을 반환한다."""
    rows = conn.execute("SELECT * FROM skills ORDER BY name").fetchall()
    return [_parse_skill_row(r) for r in rows]


def get_enabled_skills(conn: sqlite3.Connection) -> list[dict]:
    """활성화된 스킬만 반환한다."""
    rows = conn.execute(
        "SELECT * FROM skills WHERE enabled = 1 ORDER BY name"
    ).fetchall()
    return [_parse_skill_row(r) for r in rows]


def find_skills_by_keyword(
    conn: sqlite3.Connection, keyword: str
) -> list[dict]:
    """trigger_keywords에 해당 키워드가 포함된 스킬을 검색한다.

    JSON 배열 내 문자열 매칭을 위해 LIKE 검색을 사용하고,
    파싱 후 정확한 포함 여부를 재확인한다.
    """
    rows = conn.execute(
        "SELECT * FROM skills WHERE enabled = 1 AND trigger_keywords LIKE ?",
        (f"%{keyword}%",),
    ).fetchall()
    results = []
    for row in rows:
        skill = _parse_skill_row(row)
        if keyword in skill["trigger_keywords"]:
            results.append(skill)
    return results


def update_skill(
    conn: sqlite3.Connection,
    skill_id: str,
    name: str | None = None,
    description: str | None = None,
    instruction: str | None = None,
    trigger_keywords: list[str] | None = None,
) -> None:
    """스킬 정보를 업데이트한다. None이 아닌 필드만 갱신한다."""
    fields: list[str] = []
    values: list = []
    if name is not None:
        fields.append("name = ?")
        values.append(name)
    if description is not None:
        fields.append("description = ?")
        values.append(description)
    if instruction is not None:
        fields.append("instruction = ?")
        values.append(instruction)
    if trigger_keywords is not None:
        fields.append("trigger_keywords = ?")
        values.append(json.dumps(trigger_keywords, ensure_ascii=False))
    if not fields:
        return
    values.append(skill_id)
    conn.execute(
        f"UPDATE skills SET {', '.join(fields)} WHERE skill_id = ?",
        values,
    )
    conn.commit()


def toggle_skill(
    conn: sqlite3.Connection, skill_id: str, enabled: bool
) -> None:
    """스킬 활성/비활성 상태를 전환한다."""
    conn.execute(
        "UPDATE skills SET enabled = ? WHERE skill_id = ?",
        (int(enabled), skill_id),
    )
    conn.commit()
