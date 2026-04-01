"""첫 실행 설정 다이얼로그. 이름/직급/직무 등록."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid

try:
    from PySide6.QtWidgets import (
        QDialog,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
    )
except ImportError:
    pass


class SetupDialog(QDialog):
    """최초 실행 시 유저 정보를 입력받는 다이얼로그."""

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("서대리 — 첫 실행 설정")
        self.setFixedSize(400, 280)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("서대리에 오신 것을 환영합니다!"))
        layout.addWidget(QLabel("원활한 소통을 위해 기본 정보를 입력해 주세요.\n"))

        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("필수")
        self.pos_edit = QLineEdit()
        self.pos_edit.setPlaceholderText("선택")
        self.role_edit = QLineEdit()
        self.role_edit.setPlaceholderText("선택")
        self.server_edit = QLineEdit(self.config.get("server_url", "http://localhost:8000"))

        form.addRow("이름:", self.name_edit)
        form.addRow("직급:", self.pos_edit)
        form.addRow("직무:", self.role_edit)
        form.addRow("서버:", self.server_edit)
        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        start_btn = QPushButton("시작")
        start_btn.clicked.connect(self._on_start)
        btn_layout.addStretch()
        btn_layout.addWidget(start_btn)
        layout.addLayout(btn_layout)

    def _on_start(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "입력 오류", "이름을 입력해 주세요.")
            return

        user_id = self.config.get("user_id") or uuid.uuid4().hex[:12]
        server = self.server_edit.text().strip()

        self.config.update({
            "user_id": user_id,
            "name": name,
            "position": self.pos_edit.text().strip(),
            "role": self.role_edit.text().strip(),
            "server_url": server,
        })

        # 서버 등록 시도
        try:
            data = json.dumps({
                "name": name,
                "position": self.config["position"],
                "role": self.config["role"],
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{server}/api/register",
                data=data,
                headers={"Content-Type": "application/json", "X-User-Id": user_id},
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass  # 서버 미연결 시에도 로컬 저장 진행

        self.accept()

    def get_config(self) -> dict:
        return self.config
