"""서대리 데스크톱 클라이언트 진입점."""
import sys
import json
import os

try:
    from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget
    from PySide6.QtCore import Qt
except ImportError:
    print("오류: PySide6 패키지가 필요합니다.")
    print("설치: pip install PySide6")
    sys.exit(1)

from views.chat_view import ChatView
from views.queue_view import QueueView
from views.schedule_view import ScheduleView
from views.download_view import DownloadView
from system.api_client import ApiClient

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")


def load_config():
    """설정 파일을 읽어 딕셔너리로 반환한다."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"server_url": "http://localhost:8000", "user_id": "anonymous"}


class MainWindow(QMainWindow):
    """메인 윈도우. 탭으로 각 뷰를 표시한다."""

    def __init__(self, config):
        super().__init__()
        self.setWindowTitle("서대리")
        self.resize(900, 650)

        client = ApiClient(
            config["server_url"],
            config.get("user_id", "anonymous"),
        )

        tabs = QTabWidget()
        tabs.addTab(ChatView(client), "채팅")
        tabs.addTab(QueueView(client), "대기열")
        tabs.addTab(ScheduleView(client), "일정")
        tabs.addTab(DownloadView(client), "파일")
        self.setCentralWidget(tabs)


def main():
    """애플리케이션을 실행한다."""
    config = load_config()
    app = QApplication(sys.argv)
    window = MainWindow(config)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
