"""세션 관리 모듈.

유저 세션의 생성, 대화 히스토리, 최초 접촉 감지, 세션 종료를 담당한다.
"""

import logging
import time

from server.data.database import get_db, init_tables
from server.data.user_store import (
    user_exists,
    create_user,
    get_user,
    update_last_seen,
)
from server.data.memory_store import get_important_triples, search_triples, store_triple
from server.data.directive_store import get_directives, get_active_skills
from server.config.constants import REGISTRATION_PROMPT

_sessions: dict[str, dict] = {}


def is_new_user(user_id: str) -> bool:
    """SQLite에서 유저 존재 여부를 확인한다."""
    conn = get_db(user_id)
    try:
        init_tables(conn)
        exists = user_exists(conn, user_id)
        return not exists
    finally:
        conn.close()


def start_session(user_id: str) -> dict:
    """세션을 시작하고 유저 정보를 로드한다."""
    conn = get_db(user_id)
    try:
        init_tables(conn)
        update_last_seen(conn, user_id)
        user = get_user(conn, user_id)
        directives = get_directives(conn)
        skills = get_active_skills(conn)
        important_memories = get_important_triples(conn)
    finally:
        conn.close()

    session = {
        "user_id": user_id,
        "user": user,
        "directives": directives,
        "skills": skills,
        "messages": [],
        "started_at": time.time(),
    }
    _sessions[user_id] = session
    return session


def register_user(
    user_id: str, name: str, position: str, role: str
) -> None:
    """신규 유저를 등록한다."""
    conn = get_db(user_id)
    try:
        init_tables(conn)
        create_user(conn, user_id, name, position, role)
    finally:
        conn.close()


def add_message(user_id: str, role: str, content: str) -> None:
    """대화 히스토리에 메시지를 추가한다."""
    if user_id in _sessions:
        _sessions[user_id]["messages"].append(
            {"role": role, "content": content}
        )


def get_session(user_id: str) -> dict | None:
    """현재 세션을 반환한다."""
    return _sessions.get(user_id)



def get_conversation_text(user_id: str) -> str:
    """세션의 전체 대화를 텍스트로 반환한다 (기억 추출용)."""
    session = _sessions.get(user_id)
    if not session:
        return ""
    lines = []
    for msg in session["messages"]:
        speaker = "사용자" if msg["role"] == "user" else "서대리"
        lines.append(f"{speaker}: {msg['content']}")
    return "\n".join(lines)


def end_session(user_id: str) -> list[dict]:
    """세션을 종료하고 대화 히스토리를 반환한다."""
    session = _sessions.pop(user_id, None)
    if session:
        return session["messages"]
    return []


async def save_session_memories(user_id: str) -> int:
    """세션 종료 시 대화에서 기억을 추출하여 저장한다."""
    from server.domain.memory_extractor import extract_memories

    conversation = get_conversation_text(user_id)
    if not conversation:
        return 0

    try:
        triples = await extract_memories(conversation)
    except Exception:
        logging.getLogger(__name__).exception("기억 추출 실패: %s", user_id)
        return 0

    if not triples:
        return 0

    conn = get_db(user_id)
    try:
        init_tables(conn)
        for t in triples:
            store_triple(conn, t["subject"], t["predicate"], t["object"])
    finally:
        conn.close()

    end_session(user_id)
    return len(triples)
