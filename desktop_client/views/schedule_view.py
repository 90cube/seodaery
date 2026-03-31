"""일정 뷰. 사용자의 예약 작업 목록을 표시한다."""
try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout,
        QTableWidget, QTableWidgetItem, QPushButton,
        QHeaderView, QDialog, QFormLayout,
        QLineEdit, QDialogButtonBox, QLabel,
    )
    from PySide6.QtCore import QTimer
except ImportError:
    pass

COLUMNS = ["이름", "크론 표현식", "다음 실행", "상태"]


class NewScheduleDialog(QDialog):
    """새 일정 등록 다이얼로그."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("새 일정 등록")

        self.name_input = QLineEdit()
        self.cron_input = QLineEdit()
        self.cron_input.setPlaceholderText("예: 0 9 * * 1-5")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        form = QFormLayout(self)
        form.addRow("이름:", self.name_input)
        form.addRow("크론:", self.cron_input)
        form.addRow(buttons)

    def get_data(self):
        """입력된 일정 데이터를 반환한다."""
        return {
            "name": self.name_input.text().strip(),
            "cron": self.cron_input.text().strip(),
        }


class ScheduleView(QWidget):
    """일정 관리 위젯."""

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self._client = client

        self._add_btn = QPushButton("새 일정")
        self._add_btn.clicked.connect(self._add_schedule)

        self._refresh_btn = QPushButton("새로고침")
        self._refresh_btn.clicked.connect(self._refresh)

        top_row = QHBoxLayout()
        top_row.addWidget(self._add_btn)
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

        self._refresh()

    def _refresh(self):
        """서버에서 일정 목록을 가져와 테이블을 갱신한다."""
        data = self._client.get_schedules()
        if data is None:
            return

        items = data.get("schedules", [])
        self._table.setRowCount(len(items))

        for row, item in enumerate(items):
            values = [
                item.get("name", ""),
                item.get("cron", ""),
                item.get("next_run", ""),
                item.get("status", ""),
            ]
            for col, val in enumerate(values):
                self._table.setItem(row, col, QTableWidgetItem(val))

    def _add_schedule(self):
        """새 일정 등록 다이얼로그를 표시한다."""
        dialog = NewScheduleDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if data["name"] and data["cron"]:
                self._client.create_schedule(data)
                self._refresh()
