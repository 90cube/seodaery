"""LLM 응답 파서. <talk> 추출 + 도구 호출 JSON 추출."""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)

_TALK_PATTERN = re.compile(r"<talk>(.*?)</talk>", re.DOTALL)
_TOOL_PATTERN = re.compile(
    r'\{[^{}]*"tool"\s*:[^{}]*(?:\{[^{}]*\}[^{}]*)?\}', re.DOTALL
)


def extract_talk(response: str) -> str:
    """응답에서 <talk> 영역을 추출한다. 없으면 전체 텍스트 반환."""
    match = _TALK_PATTERN.search(response)
    if match:
        return match.group(1).strip()
    cleaned = _TOOL_PATTERN.sub("", response).strip()
    return cleaned or response.strip()


def extract_tool_call(response: str) -> str | None:
    """응답에서 도구 호출 JSON을 추출한다."""
    match = _TOOL_PATTERN.search(response)
    if match is None:
        return None
    try:
        parsed = json.loads(match.group(0))
        if "tool" in parsed:
            return match.group(0)
    except json.JSONDecodeError as exc:
        logger.debug("도구 JSON 파싱 실패: %s (raw: %.200s)", exc, match.group(0))
    return None
