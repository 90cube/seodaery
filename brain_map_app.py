"""서대리 Brain Map 데스크톱 클라이언트. 웹뷰 래퍼."""

import ctypes
import json
import os
import sys
import time
import traceback
import urllib.request

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "서대리.json")
TITLE = "서대리"
WIDTH = 1000
HEIGHT = 700


def _msgbox(title: str, text: str) -> None:
    ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)


def _inputbox(title: str, prompt: str, default: str = "") -> str | None:
    """서버 주소 입력 다이얼로그."""
    import tkinter as tk
    result = [None]

    root = tk.Tk()
    root.title(title)
    root.geometry("400x150")
    root.resizable(False, False)

    tk.Label(root, text=prompt, anchor="w").pack(padx=16, pady=(16, 4), fill="x")
    entry = tk.Entry(root, font=("Consolas", 12))
    entry.insert(0, default)
    entry.pack(padx=16, fill="x")
    entry.select_range(0, tk.END)
    entry.focus()

    def on_ok(_=None):
        result[0] = entry.get().strip()
        root.destroy()

    entry.bind("<Return>", on_ok)
    tk.Button(root, text="연결", command=on_ok, width=10).pack(pady=12)

    root.mainloop()
    return result[0]


def _load_server() -> str | None:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("server")
    return None


def _save_server(server: str) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"server": server}, f)


def _wait_for_server(server: str, timeout: int = 10) -> bool:
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
        # 1. 인자 > 저장된 설정 > 입력 다이얼로그
        server = None
        if len(sys.argv) > 1:
            server = sys.argv[1]
        else:
            server = _load_server()

        if not server or not _wait_for_server(server, timeout=3):
            server = _inputbox(
                "서대리 — 서버 연결",
                "서대리 서버 주소를 입력하세요:",
                server or "http://192.168.0.0:8000",
            )
            if not server:
                return

        # 2. 연결 확인
        if not _wait_for_server(server, timeout=10):
            _msgbox(
                "서대리 — 연결 실패",
                f"서버에 연결할 수 없습니다.\n\n"
                f"주소: {server}\n\n"
                f"서대리 PC에서 서버가 실행 중인지 확인하세요.",
            )
            return

        # 3. 성공 → 주소 저장
        _save_server(server)

        # 4. 앱 실행
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
