"""WebSocket 리스너. 서버 큐 상태를 실시간 수신한다."""

from __future__ import annotations

import asyncio
import json

import websockets

DEFAULT_WS_URL = "ws://localhost:8000/ws/queue"


class QueueListener:
    def __init__(self, ws_url: str = DEFAULT_WS_URL):
        self._ws_url = ws_url
        self._running = False

    async def listen(self, on_message: callable) -> None:
        """WebSocket에 연결하여 큐 상태 메시지를 수신한다."""
        self._running = True

        while self._running:
            try:
                async with websockets.connect(self._ws_url) as ws:
                    while self._running:
                        raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
                        data = json.loads(raw)
                        on_message(data)
            except (
                websockets.ConnectionClosed,
                ConnectionRefusedError,
                asyncio.TimeoutError,
            ):
                if self._running:
                    await asyncio.sleep(2.0)

    def stop(self) -> None:
        """리스너를 정지시킨다."""
        self._running = False
