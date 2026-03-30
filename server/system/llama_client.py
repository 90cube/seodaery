"""llama.cpp 서버 HTTP API 래퍼. 단일 책임: HTTP 통신만."""

from __future__ import annotations

import httpx

from server.config.constants import LLAMA_COMPLETION_PATH


async def request_completion(
    base_url: str,
    messages: list[dict[str, str]],
    max_tokens: int,
    timeout: float,
    temperature: float = 0.7,
) -> str:
    """llama.cpp 서버에 chat completion 요청을 보내고 응답 텍스트를 반환한다."""
    url = f"{base_url}{LLAMA_COMPLETION_PATH}"
    payload = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()

    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


async def health_check(base_url: str) -> bool:
    """llama.cpp 서버의 /health 엔드포인트를 확인한다."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{base_url}/health")
            return resp.status_code == 200
    except (httpx.RequestError, httpx.HTTPStatusError):
        return False
