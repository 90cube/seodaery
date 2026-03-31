"""도구 관리 패널. 등록된 도구의 활성화/비활성화 토글."""
import threading
import time

try:
    import dearpygui.dearpygui as dpg
except ImportError:
    raise ImportError("dearpygui 패키지가 필요합니다.")

TOOL_TABLE_TAG = "tool_table"
TOOL_STATUS_TAG = "tool_status_text"
POLL_INTERVAL_SEC = 5

_current_client = None


def setup_tool_panel(client) -> None:
    """도구 패널 UI 구성.

    Args:
        client: DashboardClient 인스턴스
    """
    global _current_client
    _current_client = client

    dpg.add_text("도구 관리", color=(255, 200, 0))
    dpg.add_separator()

    dpg.add_text("도구 목록 조회 중...", tag=TOOL_STATUS_TAG)
    dpg.add_button(
        label="도구 목록 새로고침",
        callback=lambda: _refresh_tools(client),
    )

    dpg.add_spacing(count=3)

    with dpg.table(
        tag=TOOL_TABLE_TAG,
        header_row=True,
        resizable=True,
        borders_innerH=True,
        borders_outerH=True,
        borders_innerV=True,
        borders_outerV=True,
    ):
        dpg.add_table_column(label="도구 ID")
        dpg.add_table_column(label="도구명")
        dpg.add_table_column(label="설명")
        dpg.add_table_column(label="활성화")

    thread = threading.Thread(
        target=_auto_refresh_loop,
        args=(client,),
        daemon=True,
    )
    thread.start()


def _on_toggle(sender, value, user_data) -> None:
    """체크박스 토글 콜백. 서버에 활성화 상태 전송."""
    tool_id = user_data
    if _current_client is None:
        return
    try:
        _current_client.toggle_tool(tool_id, value)
    except Exception as exc:
        dpg.set_value(TOOL_STATUS_TAG, f"토글 실패: {exc}")


def _refresh_tools(client) -> None:
    """서버에서 도구 목록을 가져와 테이블 갱신."""
    try:
        data = client.get_admin_tools()
        tools = data.get("tools", [])
        dpg.set_value(
            TOOL_STATUS_TAG,
            f"등록된 도구: {len(tools)}개",
        )
        _rebuild_tool_rows(tools)
    except Exception as exc:
        dpg.set_value(TOOL_STATUS_TAG, f"조회 실패: {exc}")


def _rebuild_tool_rows(tools: list) -> None:
    """도구 테이블 행 재구성."""
    children = dpg.get_item_children(TOOL_TABLE_TAG, slot=1)
    if children:
        for row in children:
            dpg.delete_item(row)

    for t in tools:
        tool_id = str(t.get("id", ""))
        with dpg.table_row(parent=TOOL_TABLE_TAG):
            dpg.add_text(tool_id)
            dpg.add_text(str(t.get("name", "-")))
            dpg.add_text(str(t.get("description", "-")))
            dpg.add_checkbox(
                default_value=bool(t.get("enabled", False)),
                callback=_on_toggle,
                user_data=tool_id,
            )


def _auto_refresh_loop(client) -> None:
    """백그라운드 폴링 루프."""
    while True:
        try:
            _refresh_tools(client)
        except Exception:
            pass
        time.sleep(POLL_INTERVAL_SEC)
