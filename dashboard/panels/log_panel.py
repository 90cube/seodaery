"""실시간 로그 패널. 서버 로그를 주기적으로 폴링하여 표시."""
import threading
import time

try:
    import dearpygui.dearpygui as dpg
except ImportError:
    raise ImportError("dearpygui 패키지가 필요합니다.")

LOG_OUTPUT_TAG = "log_output"
LOG_LIMIT_TAG = "log_limit_input"
POLL_INTERVAL_SEC = 2


def setup_log_panel(client) -> None:
    """로그 패널 UI 구성 및 자동 새로고침 스레드 시작.

    Args:
        client: DashboardClient 인스턴스
    """
    dpg.add_text("실시간 로그", color=(255, 200, 0))
    dpg.add_separator()

    with dpg.group(horizontal=True):
        dpg.add_text("표시 개수:")
        dpg.add_input_int(
            tag=LOG_LIMIT_TAG,
            default_value=100,
            width=100,
            min_value=10,
            max_value=1000,
        )
        dpg.add_button(
            label="로그 새로고침",
            callback=lambda: _refresh_logs(client),
        )

    dpg.add_input_text(
        tag=LOG_OUTPUT_TAG,
        multiline=True,
        readonly=True,
        height=500,
        width=-1,
        default_value="서버 연결 대기 중...",
    )

    thread = threading.Thread(
        target=_auto_refresh_loop,
        args=(client,),
        daemon=True,
    )
    thread.start()


def _refresh_logs(client) -> None:
    """서버에서 로그를 가져와 텍스트 위젯에 반영."""
    try:
        limit = dpg.get_value(LOG_LIMIT_TAG)
        data = client.get_admin_logs(limit=limit)
        logs = data.get("logs", [])
        text = "\n".join(str(line) for line in logs)
        dpg.set_value(LOG_OUTPUT_TAG, text if text else "(로그 없음)")
    except Exception as exc:
        dpg.set_value(LOG_OUTPUT_TAG, f"로그 조회 실패: {exc}")


def _auto_refresh_loop(client) -> None:
    """백그라운드 폴링 루프. 데몬 스레드로 실행."""
    while True:
        try:
            _refresh_logs(client)
        except Exception:
            pass
        time.sleep(POLL_INTERVAL_SEC)
