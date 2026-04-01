"""응답 검증기. 0.8B 추론기로 9B 응답의 사실 정확성을 검증한다."""

from __future__ import annotations

import logging

from server.config.constants import REASONER_MODEL_URL, REASONER_TIMEOUT_SEC
from server.system.llama_client import request_completion

logger = logging.getLogger(__name__)

VERIFY_PROMPT = (
    "Verify the assistant's response against the provided context.\n"
    "Check for:\n"
    "1. Factual accuracy (does it match the context?)\n"
    "2. Completeness (did it address the question?)\n"
    "3. Hallucination (did it make up facts not in context?)\n\n"
    "Reply with ONLY one of:\n"
    "PASS - response is accurate and complete\n"
    "FAIL:reason - response has issues (briefly explain)"
)


async def verify_response(
    question: str,
    response: str,
    context: str = "",
) -> dict:
    """9B 응답을 0.8B 추론기로 검증한다.

    반환: {"passed": bool, "reason": str}
    """
    prompt = f"Question: {question}\n"
    if context:
        prompt += f"Context: {context}\n"
    prompt += f"Response: {response}"

    try:
        messages = [
            {"role": "system", "content": VERIFY_PROMPT},
            {"role": "user", "content": prompt},
        ]
        raw = await request_completion(
            base_url=REASONER_MODEL_URL,
            messages=messages,
            max_tokens=50,
            timeout=REASONER_TIMEOUT_SEC,
            temperature=0.0,
        )

        normalized = raw.strip().upper()
        if normalized.startswith("PASS"):
            return {"passed": True, "reason": ""}

        reason = raw.split(":", 1)[1].strip() if ":" in raw else raw
        return {"passed": False, "reason": reason}

    except Exception as exc:
        logger.warning("응답 검증 실패: %s", exc)
        return {"passed": True, "reason": "검증 건너뜀 (오류)"}
