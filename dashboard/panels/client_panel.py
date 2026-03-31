"""클라이언트 패널. 접속 중인 사용자 목록을 테이블로 표시."""
import threading
import time

try:
    import dearpygui.dearpygui as dpg
except ImportError:
    raise ImportError("dearpygui 패키지가 필요합니다.")

CLIENT_TABLE_TAG = "client_table"
CLIENT_COUNT_TAG = "client_count_text"
POLL_INTERVAL_SEC = 3


def setup_client_panel(client) -> None:
    """클라이언트 패널 UI 구성.

    Args:
        client: DashboardClient 인스턴스
    """
    dpg.add_text("접속 중인 클라이언트", color=(255, 200, 0))
    dpg.add_separator()

    with dpg.group(horizontal=True):
        dpg.add_text("접속자 수:", tag=CLIENT_COUNT_TAG)
        dpg.add_button(
            label="목록 새로고침",
            callback=lambda: _refresh_clients(client),
        )

    with dpg.table(
        tag=CLIENT_TABLE_TAG,
        header_row=True,
        resizable=True,
        borders_innerH=True,
        borders_outerH=True,
        borders_innerV=True,
        borders_outerV=True,
    ):
        dpg.add_table_column(label="사용자 ID")
        dpg.add_table_column(label="접속 시각")
        dpg.add_table_column(label="마지막 활동")

    thread = threading.Thread(
        target=_auto_refresh_loop,
        args=(client,),
        daemon=True,
    )
    thread.start()


def _refresh_clients(client) -> None:
    """서버에서 클라이언트 목록을 가져와 테이블 갱신."""
    try:
        data = client.get_admin_clients()
        clients = data.get("clients", [])
        dpg.set_value(
            CLIENT_COUNT_TAG,
            f"접속자 수: {len(clients)}",
        )
        _rebuild_table_rows(clients)
    except Exception as exc:
        dpg.set_value(CLIENT_COUNT_TAG, f"조회 실패: {exc}")


def _rebuild_table_rows(clients: list) -> None:
    """테이블 행 전체 재구성."""
    # 기존 행 삭제
    children = dpg.get_item_children(CLIENT_TABLE_TAG, slot=1)
    if children:
        for row in children:
            dpg.delete_item(row)

    # 새 행 추가
    for c in clients:
        with dpg.table_row(parent=CLIENT_TABLE_TAG):
            dpg.add_text(str(c.get("user_id", "-")))
            dpg.add_text(str(c.get("connected_at", "-")))
            dpg.add_text(str(c.get("last_activity", "-")))


def _auto_refresh_loop(client) -> None:
    """백그라운드 폴링 루프."""
    while True:
        try:
            _refresh_clients(client)
        except Exception:
            pass
        time.sleep(POLL_INTERVAL_SEC)
