"""
듀얼 모델 LLM 채팅 클라이언트 (단일 파일, 외부 의존성 없음)
사용법: python client.py [서버주소]
예시:   python client.py http://192.168.1.100:8000
"""

import json
import sys
import time
import urllib.error
import urllib.request

DEFAULT_SERVER = "http://localhost:8000"
POLL_INTERVAL = 0.5


def post_chat(server: str, message: str) -> dict:
    """채팅 메시지를 서버에 전송한다."""
    url = f"{server}/api/chat"
    data = json.dumps({"message": message}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_result(server: str, request_id: str) -> dict:
    """처리 결과를 조회한다."""
    url = f"{server}/api/chat/{request_id}"
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_queue_status(server: str) -> dict:
    """대기열 상태를 조회한다."""
    url = f"{server}/api/queue/status"
    with urllib.request.urlopen(url, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_for_result(server: str, request_id: str) -> dict:
    """결과가 나올 때까지 폴링한다."""
    spinner = ["|", "/", "-", "\\"]
    idx = 0
    while True:
        result = get_result(server, request_id)
        status = result.get("status", "")
        if status in ("completed", "error"):
            print("\r" + " " * 40 + "\r", end="")
            return result
        pending = result.get("pending_count", "?")
        print(f"\r  {spinner[idx]} 처리 중... (대기열: {pending}건)", end="", flush=True)
        idx = (idx + 1) % len(spinner)
        time.sleep(POLL_INTERVAL)


def main() -> None:
    server = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERVER

    print("=" * 40)
    print("  듀얼 모델 채팅 클라이언트")
    print(f"  서버: {server}")
    print("  종료: quit 또는 Ctrl+C")
    print("=" * 40)

    try:
        status = get_queue_status(server)
        print(f"  서버 연결 성공 (대기열: {status['pending_count']}건)\n")
    except (urllib.error.URLError, ConnectionError):
        print("  [경고] 서버에 연결할 수 없습니다. 서버 실행 여부를 확인하세요.\n")

    try:
        while True:
            try:
                message = input("나> ").strip()
            except EOFError:
                break

            if message.lower() in ("quit", "exit", "q"):
                break
            if not message:
                continue

            try:
                queued = post_chat(server, message)
                request_id = queued["request_id"]
                position = queued.get("position", "?")
                print(f"  [전송] id={request_id}, 대기열={position}번째")

                result = wait_for_result(server, request_id)
                model = result.get("model_used", "?")
                intent = result.get("intent", "?")
                content = result.get("content", "(응답 없음)")
                print(f"  [{model}|{intent}] {content}\n")

            except urllib.error.URLError as e:
                print(f"  [오류] 서버 통신 실패: {e}\n")
            except KeyError as e:
                print(f"  [오류] 응답 파싱 실패: {e}\n")

    except KeyboardInterrupt:
        pass

    print("\n종료합니다.")


if __name__ == "__main__":
    main()
