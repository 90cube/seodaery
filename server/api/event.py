"""이벤트(일정) REST API. 로직 없음 — 도메인 레이어 호출만."""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from server.domain.birthday_manager import (
    get_all_birthdays,
    get_next_birthdays,
    register_birthday,
    remove_birthday,
)
from server.domain.meeting_manager import (
    get_all_meetings,
    get_meeting_detail,
    get_my_meetings,
    join_meeting,
    register_meeting,
    remove_meeting,
)
from server.domain.patch_manager import (
    assign_task,
    find_assignee,
    get_all_patches,
    get_my_tasks,
    get_patch_detail,
    register_patch,
    remove_assignment,
    remove_patch,
)

router = APIRouter(prefix="/api/event", tags=["event"])


# ── 패치 일정 ───────────────────────────────────────────


@router.post("/patch")
async def create_patch(body: dict, x_user_id: str = Header(default="anonymous")):
    title = body.get("title")
    patch_date = body.get("patch_date")
    if not title or not patch_date:
        raise HTTPException(400, "title, patch_date 필수")
    pid = register_patch(
        title=title, patch_date=patch_date, created_by=x_user_id,
        description=body.get("description", ""),
        art_share_date=body.get("art_share_date"),
        concept_share_date=body.get("concept_share_date"),
        illustration_done_date=body.get("illustration_done_date"),
        modeling_start_date=body.get("modeling_start_date"),
        modeling_done_date=body.get("modeling_done_date"),
        extra_info=body.get("extra_info"),
        extra_info=body.get("extra_info"),
    )
    return {"patch_id": pid}


@router.get("/patch")
async def list_patch():
    patches = get_all_patches()
    return {"patches": patches, "count": len(patches)}


@router.get("/patch/{patch_id}")
async def get_patch(patch_id: str):
    detail = get_patch_detail(patch_id)
    if not detail:
        raise HTTPException(404, "패치 일정 미존재")
    return detail


@router.delete("/patch/{patch_id}")
async def delete_patch(patch_id: str):
    if not remove_patch(patch_id):
        raise HTTPException(404, "패치 일정 미존재")
    return {"deleted": True}


# ── 담당자 배정 ─────────────────────────────────────────


@router.post("/patch/{patch_id}/assign")
async def assign(patch_id: str, body: dict):
    uid = body.get("user_id")
    uname = body.get("user_name")
    role = body.get("role")
    if not uid or not uname or not role:
        raise HTTPException(400, "user_id, user_name, role 필수")
    aid = assign_task(
        patch_id=patch_id, user_id=uid, user_name=uname,
        role=role, task_description=body.get("task_description", ""),
    )
    return {"assignment_id": aid}


@router.get("/my-tasks")
async def my_tasks(x_user_id: str = Header(default="anonymous")):
    tasks = get_my_tasks(x_user_id)
    return {"tasks": tasks, "count": len(tasks)}


@router.get("/assignee-search")
async def assignee_search(
    role: str | None = None,
    patch_date: str | None = None,
    task_keyword: str | None = None,
):
    results = find_assignee(
        role=role, patch_date=patch_date, task_keyword=task_keyword,
    )
    return {"assignments": results, "count": len(results)}


@router.delete("/assignment/{assignment_id}")
async def delete_assignment(assignment_id: str):
    if not remove_assignment(assignment_id):
        raise HTTPException(404, "배정 미존재")
    return {"deleted": True}


# ── 회의 ────────────────────────────────────────────────


@router.post("/meeting")
async def create_meeting_ep(body: dict, x_user_id: str = Header(default="anonymous")):
    title = body.get("title")
    meeting_date = body.get("meeting_date")
    if not title or not meeting_date:
        raise HTTPException(400, "title, meeting_date 필수")
    mid = register_meeting(
        title=title, meeting_date=meeting_date, created_by=x_user_id,
        location=body.get("location", ""),
        description=body.get("description", ""),
        related_patch_id=body.get("related_patch_id"),
        participants=body.get("participants"),
    )
    return {"meeting_id": mid}


@router.get("/meeting")
async def list_meeting():
    meetings = get_all_meetings()
    return {"meetings": meetings, "count": len(meetings)}


@router.get("/meeting/{meeting_id}")
async def get_meeting_ep(meeting_id: str):
    detail = get_meeting_detail(meeting_id)
    if not detail:
        raise HTTPException(404, "회의 미존재")
    return detail


@router.post("/meeting/{meeting_id}/join")
async def join(meeting_id: str, body: dict):
    uid = body.get("user_id")
    uname = body.get("user_name")
    if not uid or not uname:
        raise HTTPException(400, "user_id, user_name 필수")
    join_meeting(meeting_id, uid, uname)
    return {"joined": True}


@router.get("/my-meetings")
async def my_meetings(x_user_id: str = Header(default="anonymous")):
    meetings = get_my_meetings(x_user_id)
    return {"meetings": meetings, "count": len(meetings)}


@router.delete("/meeting/{meeting_id}")
async def delete_meeting_ep(meeting_id: str):
    if not remove_meeting(meeting_id):
        raise HTTPException(404, "회의 미존재")
    return {"deleted": True}


# ── 생일 ────────────────────────────────────────────────


@router.post("/birthday")
async def create_birthday(body: dict, x_user_id: str = Header(default="anonymous")):
    birthday = body.get("birthday")
    user_name = body.get("user_name", "")
    if not birthday:
        raise HTTPException(400, "birthday (MM-DD) 필수")
    register_birthday(x_user_id, user_name, birthday)
    return {"registered": True}


@router.get("/birthday")
async def list_birthday(upcoming: bool = False):
    if upcoming:
        return {"birthdays": get_next_birthdays()}
    return {"birthdays": get_all_birthdays()}


@router.delete("/birthday/{user_id}")
async def delete_birthday_ep(user_id: str):
    if not remove_birthday(user_id):
        raise HTTPException(404, "생일 미등록")
    return {"deleted": True}
