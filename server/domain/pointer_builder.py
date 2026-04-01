"""스키마 포인터 빌더. 검색 결과를 압축된 포인터 문자열로 조립한다."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

MAX_POINTER_LENGTH = 200


def build_user_pointer(user_id: str, user_info: dict | None, triple_count: int) -> str:
    """유저 정보 포인터를 생성한다."""
    if not user_info:
        return f"U:{user_id[:8]}[new]"
    name = user_info.get("name", "?")
    pos = user_info.get("position", "")
    role = user_info.get("role", "")
    return f"U:{user_id[:8]}({name}/{pos}/{role})[t{triple_count}]"


def build_knowledge_pointer(results: list[dict]) -> str:
    """지식 DB 검색 결과 포인터를 생성한다."""
    if not results:
        return ""
    items = []
    for r in results[:5]:
        kid = r.get("id", "?")
        title = r.get("title", "?")[:10]
        items.append(f"{title}[k#{kid}]")
    return "K:" + ",".join(items)


def build_schedule_pointer(schedules: list[dict]) -> str:
    """일정 포인터를 생성한다."""
    if not schedules:
        return ""
    items = []
    for s in schedules[:3]:
        sid = s.get("schedule_id", "?")[:6]
        name = s.get("name", "?")[:8]
        items.append(f"{name}[s#{sid}]")
    return "S:" + ",".join(items)


def build_tool_pointer(tool_count: int, skill_names: list[str]) -> str:
    """활성 도구/스킬 포인터를 생성한다."""
    parts = [f"T:{tool_count}tools"]
    if skill_names:
        parts.append(",".join(s[:6] for s in skill_names[:3]))
    return " ".join(parts)


def build_asset_pointer(results: list[dict]) -> str:
    """에셋 검색 결과 포인터를 생성한다."""
    if not results:
        return ""
    items = []
    for r in results[:5]:
        aid = r.get("asset_id", "?")
        stype = r.get("search_type", "?")[:2]
        fname = r.get("file_name", "?")[:12]
        items.append(f"{stype}#{aid}({fname})")
    return "A:" + ",".join(items)


def assemble_pointer(
    user_pointer: str,
    knowledge_pointer: str = "",
    schedule_pointer: str = "",
    tool_pointer: str = "",
    asset_pointer: str = "",
) -> str:
    """모든 피처 포인터를 하나의 스키마 포인터로 조립한다."""
    parts = [user_pointer]
    for p in [knowledge_pointer, schedule_pointer, tool_pointer, asset_pointer]:
        if p:
            parts.append(p)

    result = " | ".join(parts)

    if len(result) > MAX_POINTER_LENGTH:
        result = result[:MAX_POINTER_LENGTH - 3] + "..."
        logger.warning("포인터 길이 초과, 잘림: %d자", len(result))

    return result


def build_pointer_context(pointer: str) -> str:
    """스키마 포인터를 9B 시스템 프롬프트용 컨텍스트로 변환한다."""
    return (
        f"[스키마 포인터] {pointer}\n"
        "위 포인터는 데이터의 위치를 나타냅니다. "
        "상세 정보가 필요하면 도구를 호출하세요."
    )
