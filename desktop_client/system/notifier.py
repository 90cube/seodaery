"""토스트 알림. PySide6 QSystemTrayIcon 기반으로 알림을 표시한다."""
import logging

logger = logging.getLogger(__name__)

_tray = None


def init(app):
    """시스템 트레이 아이콘을 초기화한다. QApplication 이후에 호출해야 한다."""
    global _tray
    try:
        from PySide6.QtWidgets import QSystemTrayIcon
        from PySide6.QtGui import QIcon
    except ImportError:
        logger.info("PySide6 없음 — 알림 비활성")
        return

    if not QSystemTrayIcon.isSystemTrayAvailable():
        logger.info("시스템 트레이 사용 불가")
        return

    _tray = QSystemTrayIcon()
    _tray.setToolTip("서대리")
    _tray.show()


def notify(title: str, message: str):
    """토스트 알림을 표시한다. 트레이 미초기화 시 로그로 대체한다."""
    if _tray is not None:
        try:
            from PySide6.QtWidgets import QSystemTrayIcon
            _tray.showMessage(
                title, message,
                QSystemTrayIcon.MessageIcon.Information,
                5000,
            )
            return
        except Exception:
            pass

    logger.info("알림: %s — %s", title, message)


def cleanup():
    """트레이 아이콘을 정리한다."""
    global _tray
    if _tray is not None:
        _tray.hide()
        _tray = None
