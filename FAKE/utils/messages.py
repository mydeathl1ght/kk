"""
Диалоговые окна обратной связи.
Четыре типа: ошибка, предупреждение, информация, подтверждение.
"""

from PyQt6.QtWidgets import QMessageBox


# ---------- Константы ----------
TITLE_ERROR = 'Ошибка'
TITLE_WARNING = 'Предупреждение'
TITLE_INFO = 'Информация'
TITLE_CONFIRM = 'Подтверждение'


# ============================================================
# Публичные функции
# ============================================================
def show_error(parent, text, title: str = TITLE_ERROR):
    """Критическая ошибка."""
    _show_message(parent, text, title, QMessageBox.Icon.Critical)


def show_warning(parent, text, title: str = TITLE_WARNING):
    """Предупреждение."""
    _show_message(parent, text, title, QMessageBox.Icon.Warning)


def show_info(parent, text, title: str = TITLE_INFO):
    """Информационное сообщение."""
    _show_message(parent, text, title, QMessageBox.Icon.Information)


def confirm(parent, text, title: str = TITLE_CONFIRM) -> bool:
    """Запрос подтверждения (Да/Нет)."""
    reply = QMessageBox.question(
        parent, title, text,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes


# ============================================================
# Вспомогательные
# ============================================================
def _show_message(parent, text: str, title: str, icon):
    """Общий метод для показа диалогов с иконкой."""
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.exec()