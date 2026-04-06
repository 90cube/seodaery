"""메시지 분류 및 라우팅. 0.8B로 분류, chat이면 0.8B가 즉답."""

from __future__ import annotations

import logging
import re

import httpx

from server.config.constants import (
    LIGHT_CHAT_SYSTEM_PROMPT,
    LIGHT_MAX_TOKENS,
    LIGHT_MODEL_URL,
    LIGHT_TIMEOUT_SEC,
    ROUTER_SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

VALID_CATEGORIES = {"chat", "read", "think", "tool"}
_DEFAULT_CATEGORY = "think"

# 0.8B가 분류 단어 대신 동의어를 쓸 수 있으므로 매핑
# "think" 제외 — <think> 태그 잔여물에 매칭되는 것 방지
# 분류 결과 직접 매칭용 — 사고과정에 흔히 나오는 일반 영단어 제외
_SYNONYM_MAP = {
    "chat": "chat", "greeting": "chat",
    "read": "read",
    "tool": "tool",
}
_SYNONYM_PATTERN = re.compile(
    r"\b(" + "|".join(_SYNONYM_MAP.keys()) + r")\b", re.IGNORECASE,
)


def _strip_think(text: str) -> str:
    """<think>...</think> 제거 후 실제 답변만 반환."""
    # 1. 완전한 <think>...</think> 쌍 제거
    cleaned = _THINK_RE.sub("", text).strip()
    if cleaned and cleaned != text.strip():
        return cleaned
    # 2. </think> 이후 텍스트 추출
    if "</think>" in text:
        return text.split("</think>", 1)[1].strip()
    # 3. <think>만 있고 닫히지 않은 경우 — 사고 중간에 잘림
    #    태그만 제거하고 사고과정 텍스트 반환 (분류 힌트용)
    return re.sub(r"</?think>", "", text).strip()


async def classify(message: str) -> str:
    """사용자 메시지를 0.8B로 분류한다. chat/read/think/tool 중 하나 반환."""
    try:
        category = await _classify_raw(message)
        if category:
            logger.info("분류: '%s' → %s", message[:30], category)
            return category
        logger.warning("분류 실패 → %s", _DEFAULT_CATEGORY)
    except Exception as exc:
        logger.warning("분류 오류: %s → %s", exc, _DEFAULT_CATEGORY)
    return _DEFAULT_CATEGORY


async def _classify_raw(message: str) -> str | None:
    """0.8B /completion으로 분류. think 태그 제거 후 키워드 매칭."""
    prompt = (
        f"<|system|>\n{ROUTER_SYSTEM_PROMPT}\n"
        f"<|user|>\n{message}\n<|assistant|>\n"
    )
    url = f"{LIGHT_MODEL_URL}/completion"
    payload = {
        "prompt": prompt,
        "n_predict": 256,
        "temperature": 0.0,
        "stop": ["<|", "</s>"],
    }
    async with httpx.AsyncClient(timeout=LIGHT_TIMEOUT_SEC) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()

    raw = resp.json().get("content", "")
    cleaned = _strip_think(raw)
    logger.info("0.8B 원문: [%s] → 정제: [%s]", raw[:120], cleaned[:120])

    # 정제된 텍스트에서 4대 카테고리 직접 검색 (마지막 매칭 우선)
    matches = _SYNONYM_PATTERN.findall(cleaned)
    if matches:
        return _SYNONYM_MAP.get(matches[-1].lower())

    # 사고과정 텍스트에서 최종 결론 추출 시도
    # "→ chat", "answer: chat", "classification: tool" 등
    cat_match = re.search(
        r"(?:→|->|:|category|classification|answer)\s*(chat|read|think|tool)",
        cleaned,
        re.IGNORECASE,
    )
    if cat_match:
        return cat_match.group(1).lower()
    return None


async def generate_chat_response(
    message: str,
    user_info: dict | None = None,
) -> str:
    """0.8B /completion으로 간단한 채팅 응답을 생성한다."""
    system = LIGHT_CHAT_SYSTEM_PROMPT
    if user_info:
        name = user_info.get("name", "")
        if name:
            system += f"\n대화 상대: {name}"

    prompt = f"<|system|>\n{system}\n<|user|>\n{message}\n<|assistant|>\n"
    url = f"{LIGHT_MODEL_URL}/completion"
    payload = {
        "prompt": prompt,
        "n_predict": LIGHT_MAX_TOKENS,
        "temperature": 0.6,
        "stop": ["<|", "</s>"],
    }
    try:
        async with httpx.AsyncClient(timeout=LIGHT_TIMEOUT_SEC) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        raw = resp.json().get("content", "")
        result = _strip_think(raw)
        logger.info("0.8B 채팅 응답: [%s]", result[:100])
        return result or "안녕하세요! 서대리입니다."
    except Exception as exc:
        logger.error("0.8B 채팅 응답 실패: %s", exc)
        return "죄송합니다, 잠시 후 다시 시도해주세요."
