"""대기열 뷰. 현재 큐 상태를 테이블로 표시한다."""
try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout,
        QTableWidget, QTableWidgetItem, QPushButton, QLabel,
        QHeaderView,
    )
    from PySide6.QtCore import QTimer
except ImportError:
    pass

COLUMNS = ["ID", "유형", "상태", "생성 시각", "사용자"]


class QueueView(QWidget):
    """대기열 상태 위젯. 2초마다 자동 갱신한다."""

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self._client = client

        self._status_label = QLabel("대기열 상태를 불러오는 중...")

        self._refresh_btn = QPushButton("새로고침")
        self._refresh_btn.clicked.connect(self._refresh)

        top_row = QHBoxLayout()
        top_row.addWidget(self._status_label)
        top_row.addStretch()
        top_row.addWidget(self._refresh_btn)

        self._table = QTableWidget(0, len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch,
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        layout = QVBoxLayout(self)
        layout.addLayout(top_row)
        layout.addWidget(self._table)

        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self._refresh)
        self._timer.start()

        self._refresh()

    def _refresh(self):
        """서버에서 대기열 데이터를 가져와 테이블을 갱신한다."""
        data = self._client.get_queue_status()
        if data is None:
            self._status_label.setText("서버 연결 실패")
            return

        items = data.get("items", [])
        self._status_label.setText(f"대기열: {len(items)}건")
        self._table.setRowCount(len(items))

        for row, item in enumerate(items):
            values = [
                str(item.get("id", "")),
                item.get("type", ""),
                item.get("status", ""),
                item.get("created_at", ""),
                item.get("user_id", ""),
            ]
            for col, val in enumerate(values):
                self._table.setItem(row, col, QTableWidgetItem(val))
