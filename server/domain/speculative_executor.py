"""투기적 실행. 라우터 예측과 9B 생성을 동시에 시작한다."""

from __future__ import annotations

import asyncio
import logging

from server.config.constants import (
    EXECUTOR_MAX_TOKENS,
    EXECUTOR_MODEL_URL,
    EXECUTOR_TIMEOUT_SEC,
    PERSONA_SYSTEM_PROMPT,
)
from server.domain.complexity_scorer import score_complexity
from server.domain.parallel_fetcher import fetch_all_parallel
from server.domain.pointer_builder import build_pointer_context
from server.domain.react_loop import run_react_loop
from server.system.llama_client import request_completion

logger = logging.getLogger(__name__)


async def speculative_generate(
    user_id: str,
    message: str,
    session_messages: list[dict],
    user_info: dict | None = None,
) -> dict:
    """투기적 실행: 병렬 조회와 9B 직답을 동시에 시작한다.

    1. 복잡도 판정 + 병렬 데이터 조회 (동시)
    2. 복잡도 1~2: 9B 직답 (투기적 결과 사용)
    3. 복잡도 3~5: 포인터 기반 ReAct (투기적 결과 폐기)
    """
    # 1단계: 복잡도 판정 + 병렬 조회 + 투기적 9B 직답 동시 시작
    complexity_task = score_complexity(message)
    fetch_task = fetch_all_parallel(user_id, message, user_info)
    speculative_task = _speculative_direct(message, session_messages)

    complexity, fetch_result, speculative_response = await asyncio.gather(
        complexity_task,
        fetch_task,
        speculative_task,
        return_exceptions=True,
    )

    # 예외 처리
    if isinstance(complexity, Exception):
        complexity = 3
    if isinstance(fetch_result, Exception):
        fetch_result = {"pointer": "", "elapsed": 0}
    if isinstance(speculative_response, Exception):
        speculative_response = None

    logger.info("복잡도: %d, 투기적 응답: %s", complexity, "있음" if speculative_response else "없음")

    # 2단계: 복잡도 기반 분기
    if complexity <= 2 and speculative_response:
        # 투기적 결과 채택 (빠른 경로)
        logger.info("투기적 실행 채택 (복잡도 %d)", complexity)
        return {
            "content": speculative_response,
            "pointer": fetch_result.get("pointer", ""),
            "speculative": True,
            "complexity": complexity,
        }

    # 포인터 기반 ReAct (정밀 경로)
    pointer = fetch_result.get("pointer", "")
    pointer_ctx = build_pointer_context(pointer) if pointer else ""

    messages = [{"role": "system", "content": f"{PERSONA_SYSTEM_PROMPT}\n\n{pointer_ctx}"}]
    messages.extend(session_messages)
    messages.append({"role": "user", "content": message})

    content = await run_react_loop(messages)

    return {
        "content": content,
        "pointer": pointer,
        "speculative": False,
        "complexity": complexity,
    }


async def _speculative_direct(
    message: str, session_messages: list[dict]
) -> str | None:
    """투기적 9B 직답. 컨텍스트 없이 대화 히스토리만으로 빠르게 생성."""
    try:
        messages = [{"role": "system", "content": PERSONA_SYSTEM_PROMPT}]
        messages.extend(session_messages[-4:])  # 최근 4턴만
        messages.append({"role": "user", "content": message})

        return await request_completion(
            base_url=EXECUTOR_MODEL_URL,
            messages=messages,
            max_tokens=EXECUTOR_MAX_TOKENS,
            timeout=EXECUTOR_TIMEOUT_SEC,
            temperature=0.7,
        )
    except Exception:
        return None
