"""<talk> + tool JSON 포맷 테스트.

서버가 실행 중인 상태에서 직접 llama.cpp에 요청을 보내
모델이 <talk>/tool JSON 포맷을 따르는지 확인한다.

사용법:
  python tools/test_talk_format.py
  EXECUTOR_MODEL_URL=http://localhost:8082 python tools/test_talk_format.py
"""

import asyncio
import json
import os
import sys
import re

sys.path.insert(0, ".")

SYSTEM_PROMPT = """\
당신은 '서대리'로 불리는 AI 어시스턴트입니다.

## 응답 규칙
모든 응답은 반드시 아래 두 영역으로 구분하세요:

1. <talk>유저에게 보여줄 대화</talk>
2. 도구가 필요하면 JSON: {"tool": "도구id", "params": {...}}

## 예시

일반 대화 (도구 불필요):
<talk>안녕하세요! 서대리입니다. 무엇을 도와드릴까요?</talk>

도구 호출 (대화 + 도구):
<talk>네, 내일 오전 10시에 회의 일정 잡아드릴게요.</talk>
{"tool": "create_schedule", "params": {"title": "회의", "time": "2024-01-01 10:00"}}

## 중요
- 대화는 반드시 <talk></talk> 안에 넣으세요.
- 도구 불필요 시 <talk>만 출력하세요.
- 항상 한국어로 답변하세요.

사용 가능한 도구:
[create_schedule] 일정 생성: 일정을 만든다
  - title (string, 필수): 일정 제목
  - time (string, 필수): 날짜/시간
[search_knowledge] 지식 검색: 게임 정보를 검색한다
  - query (string, 필수): 검색어
"""

TEST_CASES = [
    {"label": "일반 인사", "message": "하이"},
    {"label": "일반 질문", "message": "오늘 뭐 해?"},
    {"label": "도구 필요", "message": "내일 오전 10시에 팀 회의 잡아줘"},
    {"label": "지식 검색", "message": "AK-47 스킨 목록 알려줘"},
    {"label": "도구 불필요", "message": "고마워, 잘 됐어"},
]

_TALK_PATTERN = re.compile(r"<talk>(.*?)</talk>", re.DOTALL)
_TOOL_PATTERN = re.compile(r'\{[^{}]*"tool"\s*:.*?\}', re.DOTALL)


def parse_response(raw: str) -> dict:
    """응답에서 <talk>과 tool JSON을 분리한다."""
    talk_match = _TALK_PATTERN.search(raw)
    tool_match = _TOOL_PATTERN.search(raw)

    talk = talk_match.group(1).strip() if talk_match else None
    tool = None
    if tool_match:
        try:
            parsed = json.loads(tool_match.group(0))
            if "tool" in parsed:
                tool = parsed
        except json.JSONDecodeError:
            pass

    return {"talk": talk, "tool": tool, "raw": raw}


async def test_one(case: dict, base_url: str) -> dict:
    """단일 테스트 케이스 실행."""
    import httpx

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": case["message"]},
    ]
    payload = {
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0.3,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{base_url}/v1/chat/completions", json=payload)
        resp.raise_for_status()

    data = resp.json()
    raw = data["choices"][0]["message"]["content"]
    return parse_response(raw)


async def main():
    base_url = os.getenv("EXECUTOR_MODEL_URL", "http://localhost:8082")
    model_name = os.getenv("EXECUTOR_MODEL_NAME", "unknown")

    print(f"모델: {model_name}")
    print(f"서버: {base_url}")
    print("=" * 60)

    for case in TEST_CASES:
        print(f"\n[{case['label']}] 입력: \"{case['message']}\"")
        try:
            result = await test_one(case, base_url)

            has_talk = result["talk"] is not None
            has_tool = result["tool"] is not None

            print(f"  <talk>: {'O' if has_talk else 'X'} — {(result['talk'] or '(없음)')[:80]}")
            if has_tool:
                print(f"  tool  : {result['tool']['tool']} — {json.dumps(result['tool'].get('params', {}), ensure_ascii=False)[:60]}")
            else:
                print(f"  tool  : (없음)")

            # 판정
            expects_tool = case["label"] in ("도구 필요", "지식 검색")
            if has_talk and (has_tool == expects_tool):
                print(f"  결과  : PASS")
            elif has_talk and not expects_tool and not has_tool:
                print(f"  결과  : PASS")
            else:
                print(f"  결과  : FAIL")
                print(f"  raw   : {result['raw'][:200]}")

        except Exception as exc:
            print(f"  오류  : {exc}")

    print("\n" + "=" * 60)
    print("테스트 완료")


if __name__ == "__main__":
    asyncio.run(main())
