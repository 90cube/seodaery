"""도구 호출 검증 모듈 (L1~L4).

5단계 검증 체계 중 스키마 기반 4단계를 수행한다.
- L1: JSON 구문 유효성
- L2: 도구 이름 존재 여부
- L3: 필수 파라미터 누락 검사
- L4: 파라미터 타입·범위·허용값 검사
"""

import json
import logging

from server.data.tool_registry import (
    get_tools_db,
    get_tool_schema,
    init_tool_tables,
    tool_exists,
)

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """검증 실패 시 레벨과 메시지를 포함하는 예외."""

    def __init__(self, level: int, message: str):
        self.level = level
        self.message = message
        super().__init__(f"L{level}: {message}")


# ── 타입 매핑 ─────────────────────────────────────────────

_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "float": (int, float),
    "boolean": bool,
}


# ── 공개 API ──────────────────────────────────────────────


def validate_tool_call(raw_json: str) -> dict:
    """L1~L4 검증을 수행하고 파싱된 도구 호출을 반환한다.

    Returns:
        {"tool": str, "params": dict, "schema": dict}

    Raises:
        ValidationError: 검증 실패 시 레벨 정보 포함.
    """
    call = _validate_l1(raw_json)
    tool_id = call["tool"]
    params = call.get("params", {})

    schema = _validate_l2(tool_id)
    _validate_l3(schema, params)
    _validate_l4(schema, params)

    return {"tool": tool_id, "params": params, "schema": schema}


# ── L1: JSON 파싱 ─────────────────────────────────────────


def _validate_l1(raw_json: str) -> dict:
    """JSON 구문 유효성을 검사한다."""
    try:
        call = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ValidationError(1, f"JSON 파싱 실패: {e}")

    if not isinstance(call, dict) or "tool" not in call:
        raise ValidationError(1, "JSON에 'tool' 필드 필요")

    return call


# ── L2: 도구 존재 확인 ────────────────────────────────────


def _validate_l2(tool_id: str) -> dict:
    """도구 존재 여부와 활성 상태를 검증한다."""
    conn = get_tools_db()
    init_tool_tables(conn)

    try:
        if not tool_exists(conn, tool_id):
            raise ValidationError(2, f"도구 '{tool_id}' 미등록")

        schema = get_tool_schema(conn, tool_id)
    finally:
        conn.close()

    if not schema or not schema.get("enabled"):
        raise ValidationError(2, f"도구 '{tool_id}' 비활성 상태")

    return schema


# ── L3: 필수 파라미터 ─────────────────────────────────────


def _validate_l3(schema: dict, params: dict) -> None:
    """필수 파라미터 누락 여부를 검사한다."""
    for p in schema.get("params", []):
        if p["required"] and p["name"] not in params:
            if p.get("default_value") is None:
                raise ValidationError(
                    3, f"필수 파라미터 누락: {p['name']}"
                )


# ── L4: 타입·범위 ─────────────────────────────────────────


def _validate_l4(schema: dict, params: dict) -> None:
    """각 파라미터의 타입과 범위를 검증한다."""
    for p in schema.get("params", []):
        if p["name"] not in params:
            continue
        _validate_param(p, params[p["name"]])


def _validate_param(param_schema: dict, value) -> None:
    """개별 파라미터의 타입과 범위를 검증한다."""
    ptype = param_schema.get("type", "string")
    name = param_schema["name"]

    # 타입 검사
    expected = _TYPE_MAP.get(ptype)
    if expected and not isinstance(value, expected):
        raise ValidationError(
            4,
            f"'{name}' 타입 불일치: {ptype} 필요, "
            f"{type(value).__name__} 받음",
        )

    # 허용값 검사
    allowed = param_schema.get("allowed_values")
    if allowed and value not in allowed:
        raise ValidationError(
            4, f"'{name}' 허용 값: {allowed}, 받은 값: {value}"
        )

    # 최소·최대 범위 검사
    if isinstance(value, (int, float)):
        min_val = param_schema.get("min_value")
        if min_val is not None and value < min_val:
            raise ValidationError(
                4, f"'{name}' 최소값 {min_val}, 받은 값: {value}"
            )
        max_val = param_schema.get("max_value")
        if max_val is not None and value > max_val:
            raise ValidationError(
                4, f"'{name}' 최대값 {max_val}, 받은 값: {value}"
            )
