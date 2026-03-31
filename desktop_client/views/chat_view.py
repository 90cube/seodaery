"""채팅 뷰. 메시지 전송 및 응답 표시를 담당한다."""
try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout,
        QTextEdit, QLineEdit, QPushButton,
    )
    from PySide6.QtCore import QTimer, Qt
except ImportError:
    pass


class ChatView(QWidget):
    """채팅 인터페이스 위젯."""

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self._client = client
        self._pending_id = None

        self._history = QTextEdit()
        self._history.setReadOnly(True)
        self._history.setPlaceholderText("서대리에게 질문하세요...")

        self._input = QLineEdit()
        self._input.setPlaceholderText("메시지를 입력하세요")
        self._input.returnPressed.connect(self._send)

        self._send_btn = QPushButton("전송")
        self._send_btn.clicked.connect(self._send)

        input_row = QHBoxLayout()
        input_row.addWidget(self._input)
        input_row.addWidget(self._send_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self._history)
        layout.addLayout(input_row)

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(1500)
        self._poll_timer.timeout.connect(self._poll_result)

    def _append(self, role, text):
        """채팅 기록에 메시지를 추가한다."""
        prefix = "나" if role == "user" else "서대리"
        self._history.append(f"<b>{prefix}:</b> {text}")

    def _send(self):
        """입력된 메시지를 서버로 전송한다."""
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self._append("user", text)
        self._send_btn.setEnabled(False)

        resp = self._client.send_message(text)
        if resp and resp.get("request_id"):
            self._pending_id = resp["request_id"]
            self._poll_timer.start()
        elif resp and resp.get("reply"):
            self._append("assistant", resp["reply"])
            self._send_btn.setEnabled(True)
        else:
            self._append("system", "전송 실패. 서버를 확인하세요.")
            self._send_btn.setEnabled(True)

    def _poll_result(self):
        """비동기 응답을 폴링한다."""
        if not self._pending_id:
            self._poll_timer.stop()
            return

        resp = self._client.get_result(self._pending_id)
        if resp is None:
            return

        status = resp.get("status", "")
        if status == "completed":
            self._poll_timer.stop()
            self._append("assistant", resp.get("reply", "(빈 응답)"))
            self._pending_id = None
            self._send_btn.setEnabled(True)
        elif status == "failed":
            self._poll_timer.stop()
            self._append("system", f"오류: {resp.get('error', '알 수 없는 오류')}")
            self._pending_id = None
            self._send_btn.setEnabled(True)
