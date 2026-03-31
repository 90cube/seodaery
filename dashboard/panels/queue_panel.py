"""대기열/스케줄 패널. 작업 대기열 및 예약 작업 표시."""
import threading
import time

try:
    import dearpygui.dearpygui as dpg
except ImportError:
    raise ImportError("dearpygui 패키지가 필요합니다.")

QUEUE_STATUS_TAG = "queue_status_text"
QUEUE_TABLE_TAG = "queue_schedule_table"
POLL_INTERVAL_SEC = 3


def setup_queue_panel(client) -> None:
    """대기열 패널 UI 구성.

    Args:
        client: DashboardClient 인스턴스
    """
    dpg.add_text("대기열 / 스케줄", color=(255, 200, 0))
    dpg.add_separator()

    dpg.add_text("대기열 상태 조회 중...", tag=QUEUE_STATUS_TAG)
    dpg.add_button(
        label="대기열 새로고침",
        callback=lambda: _refresh_queue(client),
    )

    dpg.add_spacing(count=3)
    dpg.add_text("예약 작업 목록", color=(200, 200, 255))

    with dpg.table(
        tag=QUEUE_TABLE_TAG,
        header_row=True,
        resizable=True,
        borders_innerH=True,
        borders_outerH=True,
        borders_innerV=True,
        borders_outerV=True,
    ):
        dpg.add_table_column(label="작업 ID")
        dpg.add_table_column(label="크론 표현식")
        dpg.add_table_column(label="다음 실행")
        dpg.add_table_column(label="상태")

    thread = threading.Thread(
        target=_auto_refresh_loop,
        args=(client,),
        daemon=True,
    )
    thread.start()


def _refresh_queue(client) -> None:
    """대기열 상태 및 스케줄 목록 갱신."""
    try:
        status = client.get_admin_status()
        queue = status.get("queue", {})
        pending = queue.get("pending", 0)
        processing = queue.get("processing", 0)
        dpg.set_value(
            QUEUE_STATUS_TAG,
            f"대기: {pending}건 | 처리 중: {processing}건",
        )
    except Exception as exc:
        dpg.set_value(QUEUE_STATUS_TAG, f"대기열 조회 실패: {exc}")

    try:
        data = client.get_schedules()
        _rebuild_schedule_rows(data.get("schedules", []))
    except Exception:
        pass


def _rebuild_schedule_rows(schedules: list) -> None:
    """스케줄 테이블 행 재구성."""
    children = dpg.get_item_children(QUEUE_TABLE_TAG, slot=1)
    if children:
        for row in children:
            dpg.delete_item(row)

    for s in schedules:
        with dpg.table_row(parent=QUEUE_TABLE_TAG):
            dpg.add_text(str(s.get("id", "-")))
            dpg.add_text(str(s.get("cron", "-")))
            dpg.add_text(str(s.get("next_run", "-")))
            dpg.add_text(str(s.get("status", "-")))


def _auto_refresh_loop(client) -> None:
    """백그라운드 폴링 루프."""
    while True:
        try:
            _refresh_queue(client)
        except Exception:
            pass
        time.sleep(POLL_INTERVAL_SEC)
