"""클라이언트 CLI 진입점. 서버와 완전 독립 — HTTP/WS로만 통신."""

from __future__ import annotations

import asyncio
import sys

from chat_client import ChatClient
from ws_listener import QueueListener

POLL_INTERVAL = 0.5


def on_queue_update(data: dict) -> None:
    """큐 상태 변경 콜백."""
    request_id = data.get("request_id", "?")
    if "pending_count" in data:
        print(f"  [큐] {request_id} — 대기열: {data['pending_count']}건")
    if data.get("status") == "completed":
        print(f"  [큐] {request_id} — 처리 완료")


async def chat_loop(base_url: str) -> None:
    """대화형 채팅 루프."""
    client = ChatClient(base_url=base_url)
    listener = QueueListener(ws_url=base_url.replace("http", "ws") + "/ws/queue")

    ws_task = asyncio.create_task(listener.listen(on_queue_update))

    print("=== 듀얼 모델 채팅 클라이언트 ===")
    print(f"서버: {base_url}")
    print("종료: quit 또는 Ctrl+C\n")

    try:
        while True:
            message = await asyncio.to_thread(input, "나> ")
            if message.strip().lower() in ("quit", "exit", "q"):
                break
            if not message.strip():
                continue

            result = await client.send_message(message)
            request_id = result["request_id"]
            print(f"  [전송] request_id={request_id}, 대기열={result['position']}번째")

            response = await wait_for_result(client, request_id)
            model = response.get("model_used", "?")
            intent = response.get("intent", "?")
            content = response.get("content", "(응답 없음)")
            print(f"  [{model}|{intent}] {content}\n")

    except (KeyboardInterrupt, EOFError):
        print("\n종료합니다.")
    finally:
        listener.stop()
        ws_task.cancel()


async def wait_for_result(client: ChatClient, request_id: str) -> dict:
    """결과가 나올 때까지 폴링한다."""
    while True:
        result = await client.poll_result(request_id)
        status = result.get("status", "")
        if status in ("completed", "error"):
            return result
        await asyncio.sleep(POLL_INTERVAL)


def main() -> None:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    asyncio.run(chat_loop(base_url))


if __name__ == "__main__":
    main()
