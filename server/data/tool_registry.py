"""도구 스키마 CRUD 모듈 (SQLite).

에이전트의 '세계 모델' 역할을 하는 도구 레지스트리.
각 도구는 이름, 설명, 파라미터(이름·타입·필수·기본값·허용값·범위)를 가진다.
"""

import json
import os
import sqlite3
import time
from pathlib import Path

TOOLS_DB_PATH = os.path.join(
    os.getenv("DB_DIR", os.path.join(os.path.dirname(__file__), os.pardir, "db")),
    "tools.db",
)


def get_tools_db() -> sqlite3.Connection:
    """tools.db 연결을 반환한다. 디렉터리가 없으면 생성한다."""
    Path(TOOLS_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(TOOLS_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_tool_tables(conn: sqlite3.Connection) -> None:
    """도구 관련 테이블을 생성한다. 이미 존재하면 무시한다."""
    conn.executescript(_TOOL_SCHEMA_SQL)


_TOOL_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tools (
    tool_id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    enabled INTEGER DEFAULT 1,
    created_at REAL
);
CREATE TABLE IF NOT EXISTS tool_params (
    param_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_id TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'string',
    required INTEGER DEFAULT 1,
    default_value TEXT DEFAULT NULL,
    allowed_values TEXT DEFAULT NULL,
    min_value REAL DEFAULT NULL,
    max_value REAL DEFAULT NULL,
    description TEXT DEFAULT '',
    FOREIGN KEY (tool_id) REFERENCES tools(tool_id)
);
"""


# ── Tool CRUD ──────────────────────────────────────────────


def register_tool(
    conn: sqlite3.Connection,
    tool_id: str,
    name: str,
    description: str = "",
) -> None:
    """새 도구를 등록한다."""
    conn.execute(
        "INSERT INTO tools (tool_id, name, description, created_at) "
        "VALUES (?, ?, ?, ?)",
        (tool_id, name, description, time.time()),
    )
    conn.commit()


def tool_exists(conn: sqlite3.Connection, tool_id: str) -> bool:
    """도구 존재 여부를 반환한다."""
    row = conn.execute(
        "SELECT 1 FROM tools WHERE tool_id = ?", (tool_id,)
    ).fetchone()
    return row is not None


def get_tool(conn: sqlite3.Connection, tool_id: str) -> dict | None:
    """도구 정보를 파라미터 목록과 함께 반환한다."""
    row = conn.execute(
        "SELECT * FROM tools WHERE tool_id = ?", (tool_id,)
    ).fetchone()
    if row is None:
        return None
    tool = dict(row)
    tool["params"] = get_tool_params(conn, tool_id)
    return tool


def get_all_tools(conn: sqlite3.Connection) -> list[dict]:
    """모든 도구 목록을 반환한다."""
    rows = conn.execute("SELECT * FROM tools ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_enabled_tools(conn: sqlite3.Connection) -> list[dict]:
    """활성화된 도구만 반환한다."""
    rows = conn.execute(
        "SELECT * FROM tools WHERE enabled = 1 ORDER BY name"
    ).fetchall()
    return [dict(r) for r in rows]


def toggle_tool(
    conn: sqlite3.Connection, tool_id: str, enabled: bool
) -> None:
    """도구 활성/비활성 상태를 전환한다."""
    conn.execute(
        "UPDATE tools SET enabled = ? WHERE tool_id = ?",
        (int(enabled), tool_id),
    )
    conn.commit()


# ── Param CRUD ─────────────────────────────────────────────


def add_param(
    conn: sqlite3.Connection,
    tool_id: str,
    name: str,
    type_: str = "string",
    required: bool = True,
    default_value: str | None = None,
    allowed_values: list | None = None,
    min_value: float | None = None,
    max_value: float | None = None,
    description: str = "",
) -> None:
    """도구에 파라미터를 추가한다. allowed_values는 JSON 문자열로 저장된다."""
    av_json = json.dumps(allowed_values) if allowed_values is not None else None
    conn.execute(
        "INSERT INTO tool_params "
        "(tool_id, name, type, required, default_value, "
        "allowed_values, min_value, max_value, description) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (tool_id, name, type_, int(required), default_value,
         av_json, min_value, max_value, description),
    )
    conn.commit()


def get_tool_params(conn: sqlite3.Connection, tool_id: str) -> list[dict]:
    """도구의 파라미터 목록을 반환한다. allowed_values는 리스트로 파싱된다."""
    rows = conn.execute(
        "SELECT * FROM tool_params WHERE tool_id = ? ORDER BY param_id",
        (tool_id,),
    ).fetchall()
    params = []
    for r in rows:
        p = dict(r)
        raw = p.get("allowed_values")
        p["allowed_values"] = json.loads(raw) if raw else None
        params.append(p)
    return params


# ── Schema export ──────────────────────────────────────────


def get_tool_schema(conn: sqlite3.Connection, tool_id: str) -> dict | None:
    """검증기에서 사용할 전체 스키마 딕셔너리를 반환한다.

    Returns:
        {"tool_id", "name", "description", "enabled", "params": [...]}
        도구가 없으면 None.
    """
    tool = get_tool(conn, tool_id)
    if tool is None:
        return None
    return {
        "tool_id": tool["tool_id"],
        "name": tool["name"],
        "description": tool["description"],
        "enabled": bool(tool["enabled"]),
        "params": [
            {
                "name": p["name"],
                "type": p["type"],
                "required": bool(p["required"]),
                "default_value": p["default_value"],
                "allowed_values": p["allowed_values"],
                "min_value": p["min_value"],
                "max_value": p["max_value"],
                "description": p["description"],
            }
            for p in tool["params"]
        ],
    }
