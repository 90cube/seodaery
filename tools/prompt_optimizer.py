"""프롬프트 최적화 도구. 테스트 케이스 기반으로 최적 프롬프트를 탐색한다."""

import asyncio
import json
import sys

sys.path.insert(0, ".")

from server.domain.autoresearch import optimize_prompt, run_experiment

EXAMPLE_TEST_CASES = [
    {
        "input": "내일 오전 10시에 회의 잡아줘",
        "expected_tool": "create_schedule",
        "expected_params": {},
    },
    {
        "input": "리퍼 캐릭터 정보 알려줘",
        "expected_tool": "search_knowledge",
        "expected_params": {},
    },
    {
        "input": "AK-47 스킨 목록 보여줘",
        "expected_tool": "search_asset",
        "expected_params": {},
    },
]

TEST_CASES_FILE = "test_cases.json"


def load_test_cases() -> list[dict]:
    """테스트 케이스를 파일에서 로드한다."""
    try:
        with open(TEST_CASES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"  '{TEST_CASES_FILE}' 없음 — 예시 케이스 사용")
        return EXAMPLE_TEST_CASES


def save_example():
    """예시 테스트 케이스를 파일로 저장한다."""
    with open(TEST_CASES_FILE, "w", encoding="utf-8") as f:
        json.dump(EXAMPLE_TEST_CASES, f, ensure_ascii=False, indent=2)
    print(f"  예시 저장됨: {TEST_CASES_FILE}")


async def main():
    print("=" * 50)
    print("  서대리 프롬프트 최적화 도구")
    print("=" * 50)

    if "--save-example" in sys.argv:
        save_example()
        return

    test_cases = load_test_cases()
    print(f"  테스트 케이스: {len(test_cases)}개")

    base_prompt = (
        "사용자의 요청을 분석하고 적절한 도구를 호출하세요.\n"
        '형식: {"tool": "tool_id", "params": {...}}\n'
        "도구 호출이 필요 없으면 일반 텍스트로 답변하세요."
    )

    variations = [
        base_prompt + "\n단계적으로 생각하세요.",
        base_prompt + "\n먼저 사용자 의도를 파악한 후 도구를 선택하세요.",
        base_prompt + "\n가장 적합한 도구 하나만 선택하세요. 확실하지 않으면 도구를 사용하지 마세요.",
    ]

    print("\n  실험 시작...\n")
    result = await optimize_prompt(base_prompt, variations, test_cases)

    print("\n  === 결과 ===")
    for r in result["all_results"]:
        marker = " ★" if r == result["best"] else ""
        print(
            f"  #{r['prompt_index']}: "
            f"정답률 {r['accuracy']*100:.1f}% "
            f"({r['passed']}/{r['total']}) "
            f"[{r['elapsed_sec']}초]{marker}"
        )

    best = result["best"]
    print(f"\n  최적 프롬프트: #{best['prompt_index']}")
    print(f"  정답률: {best['accuracy']*100:.1f}%")


if __name__ == "__main__":
    asyncio.run(main())
