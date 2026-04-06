"""패치 일정 도메인 로직. 외부 프레임워크 의존 금지."""

import uuid

from server.data.patch_store import (
    create_assignment,
    create_patch,
    delete_assignment,
    delete_patch,
    get_assignments_by_patch,
    get_assignments_by_user,
    get_event_db,
    get_patch,
    init_patch_tables,
    list_patches,
    search_assignment,
)


def _conn():
    conn = get_event_db()
    init_patch_tables(conn)
    return conn


# ── 패치 일정 ───────────────────────────────────────────


def register_patch(
    *,
    title: str,
    patch_date: str,
    created_by: str,
    description: str = "",
    art_share_date: str | None = None,
    concept_share_date: str | None = None,
    illustration_done_date: str | None = None,
    modeling_start_date: str | None = None,
    modeling_done_date: str | None = None,
    extra_info: dict | None = None,
) -> str:
    """패치 일정을 등록하고 patch_id를 반환한다."""
    patch_id = uuid.uuid4().hex[:12]
    conn = _conn()
    try:
        create_patch(
            conn, patch_id,
            title=title, patch_date=patch_date,
            description=description, created_by=created_by,
            art_share_date=art_share_date,
            concept_share_date=concept_share_date,
            illustration_done_date=illustration_done_date,
            modeling_start_date=modeling_start_date,
            modeling_done_date=modeling_done_date,
            extra_info=extra_info or {},
        )
    finally:
        conn.close()
    return patch_id


def get_patch_detail(patch_id: str) -> dict | None:
    """패치 일정 + 담당자 목록을 반환한다."""
    conn = _conn()
    try:
        patch = get_patch(conn, patch_id)
        if not patch:
            return None
        patch["assignments"] = get_assignments_by_patch(conn, patch_id)
    finally:
        conn.close()
    return patch


def get_all_patches() -> list[dict]:
    conn = _conn()
    try:
        return list_patches(conn)
    finally:
        conn.close()


def remove_patch(patch_id: str) -> bool:
    conn = _conn()
    try:
        return delete_patch(conn, patch_id)
    finally:
        conn.close()


# ── 담당자 배정 ─────────────────────────────────────────


def assign_task(
    *,
    patch_id: str,
    user_id: str,
    user_name: str,
    role: str,
    task_description: str = "",
) -> str:
    """패치에 담당자를 배정하고 assignment_id를 반환한다."""
    aid = uuid.uuid4().hex[:12]
    conn = _conn()
    try:
        create_assignment(
            conn, aid,
            patch_id=patch_id, user_id=user_id,
            user_name=user_name, role=role,
            task_description=task_description,
        )
    finally:
        conn.close()
    return aid


def get_my_tasks(user_id: str) -> list[dict]:
    conn = _conn()
    try:
        return get_assignments_by_user(conn, user_id)
    finally:
        conn.close()


def find_assignee(
    *,
    role: str | None = None,
    patch_date: str | None = None,
    task_keyword: str | None = None,
) -> list[dict]:
    """역할·패치일·키워드로 담당자를 검색한다."""
    conn = _conn()
    try:
        return search_assignment(
            conn, role=role, patch_date=patch_date,
            task_keyword=task_keyword,
        )
    finally:
        conn.close()


def remove_assignment(assignment_id: str) -> bool:
    conn = _conn()
    try:
        return delete_assignment(conn, assignment_id)
    finally:
        conn.close()
