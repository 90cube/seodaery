"""서대리 Brain Map 데스크톱 클라이언트. 웹뷰 래퍼."""

import ctypes
import sys
import time
import traceback
import urllib.request

SERVER = "http://localhost:8000"
TITLE = "서대리"
WIDTH = 1000
HEIGHT = 700


def _msgbox(title: str, text: str) -> None:
    """Windows 메시지 박스를 표시한다."""
    ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)


def _wait_for_server(server: str, timeout: int = 30) -> bool:
    """서버가 준비될 때까지 대기한다."""
    for _ in range(timeout):
        try:
            urllib.request.urlopen(f"{server}/api/queue/status", timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


def main():
    try:
        import webview
    except ImportError:
        _msgbox(
            "서대리 — 설치 필요",
            "pywebview가 설치되어 있지 않습니다.\n\n"
            "설치 방법:\n"
            "  pip install pywebview\n\n"
            "또는 setup.bat를 다시 실행하세요.",
        )
        return

    try:
        server = sys.argv[1] if len(sys.argv) > 1 else SERVER
        url = f"{server}/static/brain_map.html"

        if not _wait_for_server(server):
            _msgbox(
                "서대리 — 연결 실패",
                f"서버에 연결할 수 없습니다.\n\n"
                f"주소: {server}\n\n"
                f"확인 사항:\n"
                f"1. 서대리 PC에서 start_server.bat 실행 중인지\n"
                f"2. 서버 주소가 맞는지\n"
                f"3. 같은 네트워크에 있는지",
            )
            return

        window = webview.create_window(
            TITLE, url,
            width=WIDTH, height=HEIGHT,
            resizable=True, text_select=True,
        )
        webview.start()

    except Exception:
        _msgbox("서대리 — 오류", traceback.format_exc())


if __name__ == "__main__":
    main()
