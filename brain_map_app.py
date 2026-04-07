"""서대리 Brain Map 데스크톱 클라이언트. 웹뷰 래퍼."""

import sys
import time
import urllib.request

import webview

SERVER = "http://localhost:8000"
URL = f"{SERVER}/static/brain_map.html"
TITLE = "서대리"
WIDTH = 1000
HEIGHT = 700


def _wait_for_server(timeout: int = 60) -> bool:
    """서버가 준비될 때까지 대기한다."""
    for _ in range(timeout):
        try:
            urllib.request.urlopen(f"{SERVER}/api/queue/status", timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


def main():
    server = sys.argv[1] if len(sys.argv) > 1 else SERVER
    url = f"{server}/static/brain_map.html"

    print("서버 연결 대기 중...")
    if not _wait_for_server():
        print("서버 연결 실패. start_server.bat를 먼저 실행하세요.")
        input("Enter로 종료...")
        return

    window = webview.create_window(
        TITLE,
        url,
        width=WIDTH,
        height=HEIGHT,
        resizable=True,
        text_select=True,
    )
    webview.start()


if __name__ == "__main__":
    main()
