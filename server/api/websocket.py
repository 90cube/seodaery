"""WebSocket 엔드포인트. 큐 상태를 실시간 푸시한다."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.system.queue_store import subscribe, unsubscribe

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/queue")
async def queue_websocket(ws: WebSocket):
    """인메모리 Pub/Sub를 구독하여 큐 상태 변경을 클라이언트에 푸시한다."""
    await ws.accept()
    sub = subscribe()

    try:
        while True:
            try:
                msg = await asyncio.wait_for(sub.get(), timeout=30.0)
                await ws.send_text(msg)
            except asyncio.TimeoutError:
                await ws.send_text('{"ping": true}')
    except WebSocketDisconnect:
        pass
    finally:
        unsubscribe(sub)
