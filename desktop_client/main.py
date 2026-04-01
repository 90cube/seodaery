"""서대리 데스크톱 클라이언트 진입점."""

import json
import os
import sys
import urllib.error
import urllib.request

try:
    from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
except ImportError:
    print("오류: PySide6 패키지가 필요합니다.")
    print("설치: pip install PySide6")
    sys.exit(1)

from system.api_client import ApiClient
from views.chat_view import ChatView
from views.download_view import DownloadView
from views.queue_view import QueueView
from views.schedule_view import ScheduleView
from views.setup_dialog import SetupDialog

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")


def load_config() -> dict:
    """설정 파일을 읽어 반환한다."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"server_url": "http://localhost:8000", "user_id": "", "name": "", "position": "", "role": ""}


def save_config(config: dict) -> None:
    """설정을 파일에 저장한다."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def sync_from_server(config: dict) -> dict:
    """서버에서 유저 정보를 가져와 로컬에 캐싱한다."""
    if not config.get("user_id"):
        return config
    try:
        req = urllib.request.Request(
            f"{config['server_url']}/api/user/me",
            headers={"X-User-Id": config["user_id"]},
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("registered"):
            config["name"] = data.get("name", config.get("name", ""))
            config["position"] = data.get("position", config.get("position", ""))
            config["role"] = data.get("role", config.get("role", ""))
            save_config(config)
    except Exception:
        pass
    return config


class MainWindow(QMainWindow):
    """메인 윈도우."""

    def __init__(self, config: dict):
        super().__init__()
        name = config.get("name", "")
        title = f"서대리 — {name}님" if name else "서대리"
        self.setWindowTitle(title)
        self.resize(900, 650)

        client = ApiClient(config["server_url"], config.get("user_id", ""))

        tabs = QTabWidget()
        tabs.addTab(ChatView(client), "채팅")
        tabs.addTab(QueueView(client), "대기열")
        tabs.addTab(ScheduleView(client), "일정")
        tabs.addTab(DownloadView(client), "파일")
        self.setCentralWidget(tabs)


def main():
    config = load_config()
    app = QApplication(sys.argv)

    # 시나리오 1: user_id 없음 → 첫 실행 다이얼로그
    if not config.get("user_id"):
        dialog = SetupDialog(config)
        if dialog.exec() != dialog.Accepted:
            sys.exit(0)
        config = dialog.get_config()
        save_config(config)

    # 시나리오 2: user_id 있지만 name 없음 → 서버에서 동기화
    elif not config.get("name"):
        config = sync_from_server(config)
        if not config.get("name"):
            dialog = SetupDialog(config)
            if dialog.exec() != dialog.Accepted:
                sys.exit(0)
            config = dialog.get_config()
            save_config(config)

    # 시나리오 3: 캐시 있음 → 바로 시작

    window = MainWindow(config)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
