"""자가 개선 (Autoresearch). 프롬프트 최적화 + 도구 정답률 측정."""

from __future__ import annotations

import json
import logging
import time

from server.config.constants import ROUTER_MODEL_URL, ROUTER_TIMEOUT_SEC
from server.data.tool_registry import get_tools_db, init_tool_tables, get_enabled_tools
from server.domain.tool_validator import validate_tool_call, ValidationError
from server.system.llama_client import request_completion

logger = logging.getLogger(__name__)


async def run_experiment(
    prompt_template: str,
    test_cases: list[dict],
    model_url: str = ROUTER_MODEL_URL,
    timeout: float = ROUTER_TIMEOUT_SEC,
) -> dict:
    """프롬프트 변형을 테스트 케이스에 대해 실행하고 정답률을 측정한다.

    test_cases: [{"input": "...", "expected_tool": "...", "expected_params": {...}}]
    반환: {"accuracy": float, "total": int, "passed": int, "failed": list}
    """
    passed = 0
    failed = []

    for i, tc in enumerate(test_cases):
        messages = [
            {"role": "system", "content": prompt_template},
            {"role": "user", "content": tc["input"]},
        ]

        try:
            raw = await request_completion(
                base_url=model_url,
                messages=messages,
                max_tokens=200,
                timeout=timeout,
                temperature=0.0,
            )

            # JSON 추출
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start == -1 or end == 0:
                failed.append({"index": i, "reason": "JSON 미발견", "output": raw[:100]})
                continue

            call = json.loads(raw[start:end])

            # 도구명 비교
            if call.get("tool") != tc.get("expected_tool"):
                failed.append({
                    "index": i,
                    "reason": f"도구 불일치: {call.get('tool')} != {tc['expected_tool']}",
                })
                continue

            # L1~L4 검증
            try:
                validate_tool_call(raw[start:end])
            except ValidationError as ve:
                failed.append({"index": i, "reason": str(ve)})
                continue

            passed += 1

        except Exception as exc:
            failed.append({"index": i, "reason": str(exc)})

    total = len(test_cases)
    accuracy = passed / total if total > 0 else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "total": total,
        "passed": passed,
        "failed": failed,
    }


async def optimize_prompt(
    base_prompt: str,
    variations: list[str],
    test_cases: list[dict],
    model_url: str = ROUTER_MODEL_URL,
) -> dict:
    """여러 프롬프트 변형을 테스트하고 최적 프롬프트를 반환한다."""
    results = []

    for i, prompt in enumerate([base_prompt] + variations):
        logger.info("실험 %d/%d 실행 중...", i + 1, len(variations) + 1)
        start = time.time()
        result = await run_experiment(prompt, test_cases, model_url)
        elapsed = time.time() - start

        results.append({
            "prompt_index": i,
            "prompt_preview": prompt[:80],
            "accuracy": result["accuracy"],
            "passed": result["passed"],
            "total": result["total"],
            "elapsed_sec": round(elapsed, 1),
        })

    # 정답률 기준 정렬
    results.sort(key=lambda r: r["accuracy"], reverse=True)
    best = results[0]

    logger.info(
        "최적 프롬프트: #%d (정답률 %.1f%%)",
        best["prompt_index"],
        best["accuracy"] * 100,
    )

    return {"best": best, "all_results": results}
