"""파일 다운로드 뷰. 서버의 파일 목록을 표시하고 다운로드한다."""
import os

try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout,
        QListWidget, QListWidgetItem, QPushButton,
        QLabel, QFileDialog, QMessageBox,
    )
except ImportError:
    pass


class DownloadView(QWidget):
    """파일 다운로드 위젯."""

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self._client = client

        self._status_label = QLabel("파일 목록을 불러오는 중...")

        self._refresh_btn = QPushButton("새로고침")
        self._refresh_btn.clicked.connect(self._refresh)

        self._download_btn = QPushButton("다운로드")
        self._download_btn.clicked.connect(self._download)
        self._download_btn.setEnabled(False)

        top_row = QHBoxLayout()
        top_row.addWidget(self._status_label)
        top_row.addStretch()
        top_row.addWidget(self._refresh_btn)
        top_row.addWidget(self._download_btn)

        self._file_list = QListWidget()
        self._file_list.currentItemChanged.connect(self._on_selection)

        layout = QVBoxLayout(self)
        layout.addLayout(top_row)
        layout.addWidget(self._file_list)

        self._refresh()

    def _on_selection(self, current, _previous):
        """파일 선택 상태에 따라 다운로드 버튼을 활성화한다."""
        self._download_btn.setEnabled(current is not None)

    def _refresh(self):
        """서버에서 파일 목록을 가져온다."""
        data = self._client.get_files()
        self._file_list.clear()

        if data is None:
            self._status_label.setText("서버 연결 실패")
            return

        files = data.get("files", [])
        self._status_label.setText(f"파일: {len(files)}개")

        for f in files:
            name = f.get("name", "알 수 없음")
            size = f.get("size", 0)
            label = f"{name}  ({_format_size(size)})"
            item = QListWidgetItem(label)
            item.setData(256, f)
            self._file_list.addItem(item)

    def _download(self):
        """선택된 파일을 다운로드한다."""
        item = self._file_list.currentItem()
        if not item:
            return

        file_info = item.data(256)
        file_id = file_info.get("id", "")
        file_name = file_info.get("name", "download")

        save_path, _ = QFileDialog.getSaveFileName(
            self, "저장 위치 선택", file_name,
        )
        if not save_path:
            return

        content = self._client.download_file(file_id)
        if content is None:
            QMessageBox.warning(self, "오류", "다운로드에 실패했습니다.")
            return

        with open(save_path, "wb") as f:
            f.write(content)

        QMessageBox.information(self, "완료", f"저장 완료: {save_path}")


def _format_size(size_bytes):
    """바이트 크기를 읽기 쉬운 문자열로 변환한다."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
