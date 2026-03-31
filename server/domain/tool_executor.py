"""도구 실행 모듈.

화이트리스트 기반 실행기 등록 + L5 사후 검증 + 재시도 로직.
"""

import asyncio
import logging
from typing import Callable

from server.domain.tool_validator import ValidationError, validate_tool_call

logger = logging.getLogger(__name__)

MAX_RETRIES = 3

# 도구 실행 레지스트리: tool_id → async callable
_executors: dict[str, Callable] = {}


# ── 실행기 등록 ───────────────────────────────────────────


def register_executor(tool_id: str, func: Callable) -> None:
    """도구 실행 함수를 등록한다. 화이트리스트 방식."""
    _executors[tool_id] = func


def get_executor(tool_id: str) -> Callable | None:
    """등록된 실행 함수를 반환한다."""
    return _executors.get(tool_id)


def list_registered() -> list[str]:
    """등록된 도구 ID 목록을 반환한다."""
    return list(_executors.keys())


# ── 실행 ──────────────────────────────────────────────────


async def execute_tool_call(raw_json: str) -> dict:
    """도구 호출을 검증하고 실행한다. 최대 3회 재시도.

    Returns:
        {"success": bool, ...} 형태의 결과 딕셔너리.
    """
    last_error: str | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            validated = validate_tool_call(raw_json)
            tool_id = validated["tool"]
            params = validated["params"]

            executor = get_executor(tool_id)
            if executor is None:
                return {
                    "success": False,
                    "error": f"도구 '{tool_id}' 실행 함수 미등록",
                }

            result = await executor(**params)

            # L5: 실행 후 검증 (실행기가 _sanity_check 플래그 반환 시)
            _check_l5_sanity(result, tool_id)

            return {
                "success": True,
                "result": result,
                "tool": tool_id,
                "attempt": attempt,
            }

        except ValidationError as e:
            last_error = str(e)
            logger.warning(
                "도구 호출 실패 (시도 %d/%d): %s",
                attempt, MAX_RETRIES, e,
            )
            # L1~L2 오류는 재시도해도 해결 불가
            if e.level <= 2:
                break

        except Exception as e:
            last_error = str(e)
            logger.exception(
                "도구 실행 오류 (시도 %d/%d)", attempt, MAX_RETRIES
            )

    return {"success": False, "error": last_error, "attempts": MAX_RETRIES}


# ── L5: 사후 검증 ─────────────────────────────────────────


def _check_l5_sanity(result, tool_id: str) -> None:
    """실행 결과의 무결성을 검증한다."""
    if not isinstance(result, dict):
        return
    if result.get("_sanity_check") is False:
        msg = result.get("_sanity_message", "알 수 없는 오류")
        raise ValidationError(5, f"실행 후 검증 실패 ({tool_id}): {msg}")
