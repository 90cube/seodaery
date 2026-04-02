"""기억 추출·검색 도메인 모듈."""

import json
import logging
import re

from server.config.constants import (
    EXECUTOR_MODEL_URL,
    LIGHT_TIMEOUT_SEC,
    MEMORY_EXTRACTION_PROMPT,
    MEMORY_SEARCH_PROMPT,
    REGISTRATION_VALIDATION_PROMPT,
)
from server.system.llama_client import request_completion

logger = logging.getLogger(__name__)


def _extract_json_fragment(raw: str, open_char: str, close_char: str) -> str | None:
    """응답 문자열에서 JSON 조각(객체 또는 배열)을 추출한다."""
    start = raw.find(open_char)
    end = raw.rfind(close_char) + 1
    if start == -1 or end == 0:
        return None
    return raw[start:end]


def _fallback_parse_registration(text: str) -> dict | None:
    """Python 레벨 폴백 파서. LLM 실패 시 기본 패턴 매칭으로 추출."""
    # "저는 홍길동. 과장, 개발입니다" / "홍길동 과장 개발" 등
    text = text.strip().rstrip(".")

    # 패턴들: "이름. 직급, 직무" / "이름, 직급, 직무" / "이름 직급 직무"
    # "저는/제 이름은" 접두사 제거
    cleaned = re.sub(r"^(저는|제\s*이름은|전)\s*", "", text)
    cleaned = re.sub(r"(입니다|이에요|이요|예요|요)\.?\s*$", "", cleaned)
    cleaned = cleaned.strip().rstrip(".")

    # 구분자로 분리: . , 공백
    parts = re.split(r"[.,]\s*|\s+", cleaned)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) >= 3:
        return {"name": parts[0], "position": parts[1], "role": parts[2]}
    if len(parts) == 2:
        return {"name": parts[0], "position": parts[1], "role": ""}
    if len(parts) == 1 and len(parts[0]) >= 2:
        return {"name": parts[0], "position": "", "role": ""}
    return None


async def validate_registration(user_input: str) -> dict | None:
    """유저 등록 입력을 검증하고 구조화된 데이터를 반환한다.

    1차: LLM으로 JSON 추출
    2차: Python 폴백 파서
    """
    # 1차: LLM 시도
    try:
        messages = [
            {"role": "system", "content": REGISTRATION_VALIDATION_PROMPT},
            {"role": "user", "content": user_input},
        ]
        raw = await request_completion(
            base_url=EXECUTOR_MODEL_URL,
            messages=messages,
            max_tokens=100,
            timeout=LIGHT_TIMEOUT_SEC,
            temperature=0.0,
        )
        fragment = _extract_json_fragment(raw, "{", "}")
        if fragment:
            data = json.loads(fragment)
            if data.get("name"):
                return data
    except Exception as exc:
        logger.warning("LLM 등록 검증 실패: %s", exc)

    # 2차: Python 폴백
    fallback = _fallback_parse_registration(user_input)
    if fallback:
        logger.info("폴백 파서로 등록 정보 추출: %s", fallback)
    return fallback


async def extract_memories(conversation_text: str) -> list[dict]:
    """대화 텍스트에서 핵심 사실을 (주어-술어-목적어) 트리플로 추출한다.

    Returns:
        subject, predicate, object 키를 가진 dict 리스트.
    """
    if not conversation_text.strip():
        return []

    messages = [
        {"role": "system", "content": MEMORY_EXTRACTION_PROMPT},
        {"role": "user", "content": conversation_text},
    ]

    raw = await request_completion(
        base_url=EXECUTOR_MODEL_URL,
        messages=messages,
        max_tokens=500,
        timeout=LIGHT_TIMEOUT_SEC,
        temperature=0.0,
    )

    fragment = _extract_json_fragment(raw, "[", "]")
    if fragment is None:
        return []

    try:
        triples = json.loads(fragment)
        required_keys = ("subject", "predicate", "object")
        return [t for t in triples if all(k in t for k in required_keys)]
    except (json.JSONDecodeError, KeyError):
        logger.warning("기억 추출 파싱 실패: %s", raw)
        return []


async def search_relevant_memories(
    message: str,
    triples: list[dict],
) -> list[dict]:
    """현재 메시지와 관련된 기억 트리플을 필터링한다.

    Args:
        message: 사용자의 현재 메시지.
        triples: 검색 대상 기억 트리플 목록.

    Returns:
        관련성 있는 트리플만 추린 리스트.
    """
    if not triples:
        return []

    triple_text = "\n".join(
        f"[{i}] {t['subject']} - {t['predicate']} - {t['object']}"
        for i, t in enumerate(triples)
    )

    prompt = f"User message: {message}\n\nAvailable triples:\n{triple_text}"

    messages = [
        {"role": "system", "content": MEMORY_SEARCH_PROMPT},
        {"role": "user", "content": prompt},
    ]

    raw = await request_completion(
        base_url=EXECUTOR_MODEL_URL,
        messages=messages,
        max_tokens=50,
        timeout=LIGHT_TIMEOUT_SEC,
        temperature=0.0,
    )

    fragment = _extract_json_fragment(raw, "[", "]")
    if fragment is None:
        return []

    try:
        indices = json.loads(fragment)
        return [triples[i] for i in indices if 0 <= i < len(triples)]
    except (json.JSONDecodeError, IndexError, TypeError):
        logger.warning("기억 검색 파싱 실패: %s", raw)
        return []
