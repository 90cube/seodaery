"""서대리 Brain Map 데스크톱 클라이언트. 웹뷰 래퍼."""

import ctypes
import ctypes.wintypes
import json
import os
import sys
import time
import traceback
import urllib.request

CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(sys.argv[0])), "서대리.json",
)
TITLE = "서대리"
WIDTH = 1000
HEIGHT = 700


def _msgbox(title: str, text: str, icon: int = 0x10) -> int:
    return ctypes.windll.user32.MessageBoxW(0, text, title, icon)


def _ask_server(default: str = "http://192.168.0.0:8000") -> str | None:
    """서버 주소 입력 — Win32 InputBox (VBScript 경유)."""
    import subprocess
    import tempfile

    vbs = (
        f'result = InputBox("서대리 서버 주소를 입력하세요:", '
        f'"서대리 — 서버 연결", "{default}")\n'
        f'If result = "" Then\n'
        f'  WScript.Quit 1\n'
        f'End If\n'
        f'WScript.StdOut.Write result\n'
    )
    tmp = os.path.join(tempfile.gettempdir(), "sdr_input.vbs")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(vbs)

    try:
        r = subprocess.run(
            ["cscript", "//Nologo", tmp],
            capture_output=True, text=True, timeout=60,
        )
        os.remove(tmp)
        if r.returncode != 0 or not r.stdout.strip():
            return None
        return r.stdout.strip()
    except Exception:
        return None


def _load_server() -> str | None:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("server")
    return None


def _save_server(server: str) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"server": server}, f)


def _check_server(server: str, timeout: int = 10) -> bool:
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
            "pip install pywebview",
        )
        return

    try:
        # 1. 인자 > 저장된 설정 > 입력
        server = sys.argv[1] if len(sys.argv) > 1 else _load_server()

        if server and _check_server(server, timeout=3):
            pass  # 바로 연결
        else:
            server = _ask_server(server or "http://192.168.0.0:8000")
            if not server:
                return

            if not _check_server(server):
                _msgbox(
                    "서대리 — 연결 실패",
                    f"서버에 연결할 수 없습니다.\n\n"
                    f"주소: {server}\n\n"
                    f"서대리 PC에서 서버가 실행 중인지 확인하세요.",
                )
                return

        _save_server(server)

        window = webview.create_window(
            TITLE,
            f"{server}/static/brain_map.html",
            width=WIDTH, height=HEIGHT,
            resizable=True, text_select=True,
        )
        webview.start()

    except Exception:
        _msgbox("서대리 — 오류", traceback.format_exc())


if __name__ == "__main__":
    main()
