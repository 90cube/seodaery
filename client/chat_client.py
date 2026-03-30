"""HTTP API 클라이언트. 서버와의 통신만 담당한다."""

from __future__ import annotations

import httpx

DEFAULT_BASE_URL = "http://localhost:8000"


class ChatClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self._base_url = base_url

    async def send_message(self, message: str) -> dict:
        """채팅 메시지를 서버에 전송하고 큐 등록 결과를 반환한다."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self._base_url}/api/chat",
                json={"message": message},
            )
            resp.raise_for_status()
            return resp.json()

    async def poll_result(self, request_id: str) -> dict:
        """request_id로 결과를 폴링한다."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self._base_url}/api/chat/{request_id}",
            )
            resp.raise_for_status()
            return resp.json()

    async def get_queue_status(self) -> dict:
        """현재 대기열 상태를 조회한다."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{self._base_url}/api/queue/status")
            resp.raise_for_status()
            return resp.json()
