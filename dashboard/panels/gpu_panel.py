"""GPU/모델 패널. GPU 상태 및 로딩된 모델 정보 표시."""
import threading
import time

try:
    import dearpygui.dearpygui as dpg
except ImportError:
    raise ImportError("dearpygui 패키지가 필요합니다.")

GPU_TABLE_TAG = "gpu_table"
MODEL_TABLE_TAG = "model_table"
GPU_STATUS_TAG = "gpu_status_text"
POLL_INTERVAL_SEC = 5


def setup_gpu_panel(client) -> None:
    """GPU/모델 패널 UI 구성.

    Args:
        client: DashboardClient 인스턴스
    """
    dpg.add_text("GPU / 모델 상태", color=(255, 200, 0))
    dpg.add_separator()

    dpg.add_text("상태: 조회 중...", tag=GPU_STATUS_TAG)
    dpg.add_button(
        label="GPU 상태 새로고침",
        callback=lambda: _refresh_gpu(client),
    )

    dpg.add_spacing(count=3)
    dpg.add_text("GPU 정보", color=(200, 200, 255))

    with dpg.table(
        tag=GPU_TABLE_TAG,
        header_row=True,
        resizable=True,
        borders_innerH=True,
        borders_outerH=True,
        borders_innerV=True,
        borders_outerV=True,
    ):
        dpg.add_table_column(label="GPU ID")
        dpg.add_table_column(label="이름")
        dpg.add_table_column(label="VRAM 사용량")
        dpg.add_table_column(label="온도")

    dpg.add_spacing(count=3)
    dpg.add_text("로딩된 모델", color=(200, 200, 255))

    with dpg.table(
        tag=MODEL_TABLE_TAG,
        header_row=True,
        resizable=True,
        borders_innerH=True,
        borders_outerH=True,
        borders_innerV=True,
        borders_outerV=True,
    ):
        dpg.add_table_column(label="모델명")
        dpg.add_table_column(label="포트")
        dpg.add_table_column(label="상태")

    thread = threading.Thread(
        target=_auto_refresh_loop,
        args=(client,),
        daemon=True,
    )
    thread.start()


def _refresh_gpu(client) -> None:
    """서버에서 GPU/모델 정보를 가져와 테이블 갱신."""
    try:
        data = client.get_admin_gpu()
        dpg.set_value(GPU_STATUS_TAG, "상태: 정상 연결")
        _rebuild_gpu_rows(data.get("gpus", []))
        _rebuild_model_rows(data.get("models", []))
    except Exception as exc:
        dpg.set_value(GPU_STATUS_TAG, f"상태: 조회 실패 - {exc}")


def _rebuild_gpu_rows(gpus: list) -> None:
    """GPU 테이블 행 재구성."""
    children = dpg.get_item_children(GPU_TABLE_TAG, slot=1)
    if children:
        for row in children:
            dpg.delete_item(row)
    for g in gpus:
        with dpg.table_row(parent=GPU_TABLE_TAG):
            dpg.add_text(str(g.get("id", "-")))
            dpg.add_text(str(g.get("name", "-")))
            dpg.add_text(str(g.get("vram_usage", "-")))
            dpg.add_text(str(g.get("temperature", "-")))


def _rebuild_model_rows(models: list) -> None:
    """모델 테이블 행 재구성."""
    children = dpg.get_item_children(MODEL_TABLE_TAG, slot=1)
    if children:
        for row in children:
            dpg.delete_item(row)
    for m in models:
        with dpg.table_row(parent=MODEL_TABLE_TAG):
            dpg.add_text(str(m.get("name", "-")))
            dpg.add_text(str(m.get("port", "-")))
            dpg.add_text(str(m.get("health", "-")))


def _auto_refresh_loop(client) -> None:
    """백그라운드 폴링 루프."""
    while True:
        try:
            _refresh_gpu(client)
        except Exception:
            pass
        time.sleep(POLL_INTERVAL_SEC)
