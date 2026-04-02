"""스키마 컴파일 모듈.

DB의 도구·스킬 정의를 읽어 다음을 자동 생성한다:
- 9B 모델용 도구 프롬프트
- intent 목록
- 스킬 instruction 컨텍스트 블록
"""

import logging
import time

from server.data.skill_store import get_enabled_skills, get_skill, init_skill_table
from server.data.tool_registry import (
    get_enabled_tools,
    get_tool_params,
    get_tools_db,
    init_tool_tables,
)

logger = logging.getLogger(__name__)

_tool_prompt_cache: str | None = None
_tool_prompt_time: float = 0
_CACHE_TTL = 60.0


# ── 도구 프롬프트 ─────────────────────────────────────────


def compile_tool_prompt() -> str:
    """활성 도구 목록을 9B용 프롬프트로 컴파일한다. 60초 캐싱."""
    global _tool_prompt_cache, _tool_prompt_time
    if _tool_prompt_cache is not None and time.time() - _tool_prompt_time < _CACHE_TTL:
        return _tool_prompt_cache
    conn = get_tools_db()
    init_tool_tables(conn)
    tools = get_enabled_tools(conn)

    if not tools:
        conn.close()
        _tool_prompt_cache = ""
        _tool_prompt_time = time.time()
        return ""

    lines = ["사용 가능한 도구 목록:"]

    for tool in tools:
        params = get_tool_params(conn, tool["tool_id"])
        param_lines = _format_params(params)

        block = f"\n[{tool['tool_id']}] {tool['name']}: {tool['description']}"
        if param_lines:
            block += "\n" + "\n".join(param_lines)
        lines.append(block)

    conn.close()

    lines.append('\n도구 호출 형식: {"tool": "tool_id", "params": {...}}')
    result = "\n".join(lines)
    _tool_prompt_cache = result
    _tool_prompt_time = time.time()
    return result


def _format_params(params: list[dict]) -> list[str]:
    """파라미터 목록을 포맷된 문자열 리스트로 변환한다."""
    result = []
    for p in params:
        req = "필수" if p["required"] else "선택"
        desc = f"  - {p['name']} ({p['type']}, {req})"
        if p.get("description"):
            desc += f": {p['description']}"
        if p.get("allowed_values"):
            vals = ", ".join(str(v) for v in p["allowed_values"])
            desc += f" [허용: {vals}]"
        result.append(desc)
    return result


# ── Intent 목록 ───────────────────────────────────────────


def compile_intent_list() -> str:
    """intent 목록을 컴파일한다."""
    conn = get_tools_db()
    init_tool_tables(conn)
    init_skill_table(conn)
    tools = get_enabled_tools(conn)
    skills = get_enabled_skills(conn)
    conn.close()

    intents = ["chat (일반 대화)"]

    for t in tools:
        intents.append(f"{t['tool_id']} ({t['description']})")

    for s in skills:
        intents.append(f"skill:{s['skill_id']} ({s['description']})")

    return "가능한 intent: " + ", ".join(intents)


# ── 스킬 컨텍스트 ─────────────────────────────────────────


def compile_skill_context(skill_ids: list[str]) -> str:
    """활성 스킬 instruction을 컨텍스트 블록으로 컴파일한다."""
    conn = get_tools_db()
    init_tool_tables(conn)
    init_skill_table(conn)

    blocks = []
    for sid in skill_ids:
        skill = get_skill(conn, sid)
        if skill and skill.get("instruction"):
            blocks.append(f"[SKILL: {skill['name']}]\n{skill['instruction']}")

    conn.close()
    return "\n\n".join(blocks) if blocks else ""
