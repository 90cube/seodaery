"""복잡도 판정기. 0.8B 라우터로 입력의 복잡도를 1~5로 점수화한다."""

from __future__ import annotations

import logging

from server.config.constants import ROUTER_MODEL_URL, ROUTER_TIMEOUT_SEC
from server.system.llama_client import request_completion

logger = logging.getLogger(__name__)

COMPLEXITY_PROMPT = (
    "Rate the complexity of this user message from 1 to 5.\n"
    "1: greeting, yes/no, single fact\n"
    "2: simple question, one lookup needed\n"
    "3: multi-step question, needs context\n"
    "4: analysis, comparison, reasoning\n"
    "5: creative task, multi-tool, complex reasoning\n"
    "Reply with ONLY one number: 1, 2, 3, 4, or 5"
)


async def score_complexity(message: str) -> int:
    """메시지의 복잡도를 1~5로 판정한다."""
    try:
        messages = [
            {"role": "system", "content": COMPLEXITY_PROMPT},
            {"role": "user", "content": message},
        ]
        raw = await request_completion(
            base_url=ROUTER_MODEL_URL,
            messages=messages,
            max_tokens=5,
            timeout=ROUTER_TIMEOUT_SEC,
            temperature=0.0,
        )
        # 숫자만 추출
        for ch in raw.strip():
            if ch.isdigit() and 1 <= int(ch) <= 5:
                return int(ch)
        return 3  # 파싱 실패 시 기본값
    except Exception as exc:
        logger.warning("복잡도 판정 실패: %s", exc)
        return 3
