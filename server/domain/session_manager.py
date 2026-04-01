"""세션 관리 모듈.

유저 세션의 생성, 대화 히스토리, 최초 접촉 감지, 세션 종료를 담당한다.
"""

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
from server.config.constants import PERSONA_SYSTEM_PROMPT, REGISTRATION_PROMPT

_sessions: dict[str, dict] = {}


def is_new_user(user_id: str) -> bool:
    """SQLite에서 유저 존재 여부를 확인한다."""
    conn = get_db(user_id)
    init_tables(conn)
    exists = user_exists(conn, user_id)
    conn.close()
    return not exists


def start_session(user_id: str) -> dict:
    """세션을 시작하고 유저 정보를 로드한다."""
    conn = get_db(user_id)
    init_tables(conn)
    update_last_seen(conn, user_id)

    user = get_user(conn, user_id)
    directives = get_directives(conn)
    skills = get_active_skills(conn)
    important_memories = get_important_triples(conn)
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
    init_tables(conn)
    create_user(conn, user_id, name, position, role)
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


def build_context(
    user_id: str,
    relevant_memories: list[dict] | None = None,
    knowledge_text: str = "",
    schema_pointer: str = "",
) -> list[dict]:
    """9B에게 보낼 메시지 컨텍스트를 구성한다.

    schema_pointer가 있으면 포인터 기반 경량 컨텍스트,
    없으면 기존 방식(전체 데이터 주입)으로 폴백.
    """
    session = _sessions.get(user_id)
    if not session:
        return []

    system_parts = [PERSONA_SYSTEM_PROMPT]

    if schema_pointer:
        # 포인터 모드: 데이터 위치만 전달, 실제 데이터는 도구로 fetch
        from server.domain.pointer_builder import build_pointer_context
        system_parts.append(f"\n{build_pointer_context(schema_pointer)}")
    else:
        # 폴백: 기존 전체 주입 방식
        if session.get("user"):
            user = session["user"]
            system_parts.append(
                f"\n현재 대화 상대: {user.get('name', '?')}"
                f" ({user.get('position', '?')}, {user.get('role', '?')})"
            )

        if relevant_memories:
            memory_text = "\n".join(
                f"- {m['subject']} {m['predicate']} {m['object']}"
                for m in relevant_memories
            )
            system_parts.append(f"\n관련 기억:\n{memory_text}")

        if knowledge_text:
            system_parts.append(f"\n{knowledge_text}")

    if session.get("directives"):
        dir_text = "\n".join(
            f"- [{d['type']}] {d['content']}"
            for d in session["directives"]
        )
        system_parts.append(f"\n유저 지침:\n{dir_text}")

    if session.get("skills"):
        skill_text = ", ".join(d["content"] for d in session["skills"])
        system_parts.append(f"\n활성 스킬: {skill_text}")

    messages = [{"role": "system", "content": "\n".join(system_parts)}]
    messages.extend(session["messages"])
    return messages


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

    triples = await extract_memories(conversation)
    if not triples:
        return 0

    conn = get_db(user_id)
    init_tables(conn)
    for t in triples:
        store_triple(conn, t["subject"], t["predicate"], t["object"])
    conn.close()

    end_session(user_id)
    return len(triples)
