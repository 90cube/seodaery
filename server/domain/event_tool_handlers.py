"""LLM 도구 핸들러. create_schedule / list_schedules 자연어 경로."""

from __future__ import annotations

from server.domain.birthday_manager import (
    get_all_birthdays,
    get_next_birthdays,
    get_user_birthday,
    register_birthday,
)
from server.domain.meeting_manager import (
    get_all_meetings,
    get_my_meetings,
    join_meeting,
    register_meeting,
)
from server.domain.patch_manager import (
    assign_task,
    find_assignee,
    get_all_patches,
    get_my_tasks,
    get_patch_detail,
    register_patch,
)


# ── create_schedule 핸들러 ──────────────────────────────


async def handle_create_schedule(**params) -> dict:
    """카테고리별 일정을 등록한다.

    category: patch | personal | birthday | meeting | personal_meeting
    """
    category = params.get("category", "")
    user_id = params.get("user_id", "anonymous")
    user_name = params.get("user_name", "")

    if category == "patch":
        return _create_patch(params)

    if category == "personal":
        return _assign_personal(params)

    if category == "birthday":
        return _register_birthday(user_id, user_name, params)

    if category == "meeting":
        return _create_meeting(params)

    if category == "personal_meeting":
        return _join_meeting(params)

    return {"success": False, "error": f"알 수 없는 카테고리: {category}"}


def _create_patch(p: dict) -> dict:
    pid = register_patch(
        title=p.get("title", ""),
        patch_date=p.get("patch_date", ""),
        created_by=p.get("user_id", "anonymous"),
        description=p.get("description", ""),
        art_share_date=p.get("art_share_date"),
        concept_share_date=p.get("concept_share_date"),
        illustration_done_date=p.get("illustration_done_date"),
        modeling_start_date=p.get("modeling_start_date"),
        modeling_done_date=p.get("modeling_done_date"),
        extra_info=p.get("extra_info"),
        file_path=p.get("file_path"),
    )
    return {"success": True, "patch_id": pid}


def _assign_personal(p: dict) -> dict:
    aid = assign_task(
        patch_id=p.get("patch_id", ""),
        user_id=p.get("user_id", "anonymous"),
        user_name=p.get("user_name", ""),
        role=p.get("role", ""),
        task_description=p.get("task_description", ""),
    )
    return {"success": True, "assignment_id": aid}


def _register_birthday(uid: str, uname: str, p: dict) -> dict:
    register_birthday(uid, uname, p.get("birthday", ""))
    return {"success": True}


def _create_meeting(p: dict) -> dict:
    mid = register_meeting(
        title=p.get("title", ""),
        meeting_date=p.get("meeting_date", ""),
        created_by=p.get("user_id", "anonymous"),
        location=p.get("location", ""),
        description=p.get("description", ""),
        related_patch_id=p.get("related_patch_id"),
        participants=p.get("participants"),
    )
    return {"success": True, "meeting_id": mid}


def _join_meeting(p: dict) -> dict:
    join_meeting(
        p.get("meeting_id", ""),
        p.get("user_id", "anonymous"),
        p.get("user_name", ""),
    )
    return {"success": True}


# ── list_schedules 핸들러 ──────────────────────────────


async def handle_list_schedules(**params) -> dict:
    """카테고리별 일정을 조회한다.

    category: patch | personal | birthday | meeting | personal_meeting
              | assignee_search
    """
    category = params.get("category", "all")
    user_id = params.get("user_id", "anonymous")

    if category == "patch":
        patches = get_all_patches()
        return {"success": True, "patches": patches}

    if category == "patch_detail":
        detail = get_patch_detail(params.get("patch_id", ""))
        return {"success": True, "patch": detail}

    if category == "personal":
        tasks = get_my_tasks(user_id)
        return {"success": True, "tasks": tasks}

    if category == "birthday":
        if params.get("upcoming"):
            return {"success": True, "birthdays": get_next_birthdays()}
        if user_id != "anonymous":
            b = get_user_birthday(user_id)
            return {"success": True, "birthday": b}
        return {"success": True, "birthdays": get_all_birthdays()}

    if category == "meeting":
        return {"success": True, "meetings": get_all_meetings()}

    if category == "personal_meeting":
        return {"success": True, "meetings": get_my_meetings(user_id)}

    if category == "assignee_search":
        results = find_assignee(
            role=params.get("role"),
            patch_date=params.get("patch_date"),
            task_keyword=params.get("task_keyword"),
        )
        return {"success": True, "assignments": results}

    # all: 전체 요약
    return {
        "success": True,
        "patches": get_all_patches(),
        "meetings": get_all_meetings(),
        "birthdays": get_all_birthdays(),
    }
