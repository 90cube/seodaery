"""서대리 서버 대시보드. 운영자 전용 모니터링."""
import sys

try:
    import dearpygui.dearpygui as dpg
except ImportError:
    print("오류: dearpygui 패키지가 필요합니다.")
    print("설치: pip install dearpygui")
    sys.exit(1)

from panels.log_panel import setup_log_panel
from panels.client_panel import setup_client_panel
from panels.gpu_panel import setup_gpu_panel
from panels.queue_panel import setup_queue_panel
from panels.tool_panel import setup_tool_panel
from api_client import DashboardClient

SERVER_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"


def main():
    """대시보드 메인 진입점. GUI 초기화 및 패널 등록."""
    client = DashboardClient(SERVER_URL)

    dpg.create_context()
    dpg.create_viewport(title="서대리 대시보드", width=1200, height=800)

    with dpg.window(label="서대리 서버 대시보드", tag="main_window"):
        with dpg.tab_bar():
            with dpg.tab(label="로그"):
                setup_log_panel(client)
            with dpg.tab(label="클라이언트"):
                setup_client_panel(client)
            with dpg.tab(label="GPU/모델"):
                setup_gpu_panel(client)
            with dpg.tab(label="대기열"):
                setup_queue_panel(client)
            with dpg.tab(label="도구"):
                setup_tool_panel(client)

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main_window", True)
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
