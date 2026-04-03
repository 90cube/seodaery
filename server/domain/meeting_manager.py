"""회의 일정 도메인 로직. 외부 프레임워크 의존 금지."""

import uuid

from server.data.meeting_store import (
    add_participant,
    create_meeting,
    delete_meeting,
    get_event_db,
    get_meeting,
    get_participants,
    get_user_meetings,
    init_meeting_tables,
    list_meetings,
    list_meetings_by_patch,
    remove_participant,
)


def _conn():
    conn = get_event_db()
    init_meeting_tables(conn)
    return conn


# ── 회의 ────────────────────────────────────────────────


def register_meeting(
    *,
    title: str,
    meeting_date: str,
    created_by: str,
    location: str = "",
    description: str = "",
    related_patch_id: str | None = None,
    participants: list[dict] | None = None,
) -> str:
    """회의를 등록하고 meeting_id를 반환한다.

    participants: [{"user_id": "...", "user_name": "..."}]
    """
    mid = uuid.uuid4().hex[:12]
    conn = _conn()
    try:
        create_meeting(
            conn, mid,
            title=title, meeting_date=meeting_date,
            location=location, description=description,
            related_patch_id=related_patch_id,
            created_by=created_by,
        )
        for p in (participants or []):
            add_participant(conn, mid, p["user_id"], p["user_name"])
    finally:
        conn.close()
    return mid


def get_meeting_detail(meeting_id: str) -> dict | None:
    conn = _conn()
    try:
        m = get_meeting(conn, meeting_id)
        if not m:
            return None
        m["participants"] = get_participants(conn, meeting_id)
    finally:
        conn.close()
    return m


def get_all_meetings() -> list[dict]:
    conn = _conn()
    try:
        return list_meetings(conn)
    finally:
        conn.close()


def get_patch_meetings(patch_id: str) -> list[dict]:
    conn = _conn()
    try:
        return list_meetings_by_patch(conn, patch_id)
    finally:
        conn.close()


def join_meeting(meeting_id: str, user_id: str, user_name: str) -> None:
    conn = _conn()
    try:
        add_participant(conn, meeting_id, user_id, user_name)
    finally:
        conn.close()


def leave_meeting(meeting_id: str, user_id: str) -> bool:
    conn = _conn()
    try:
        return remove_participant(conn, meeting_id, user_id)
    finally:
        conn.close()


def get_my_meetings(user_id: str) -> list[dict]:
    conn = _conn()
    try:
        return get_user_meetings(conn, user_id)
    finally:
        conn.close()


def remove_meeting(meeting_id: str) -> bool:
    conn = _conn()
    try:
        return delete_meeting(conn, meeting_id)
    finally:
        conn.close()
