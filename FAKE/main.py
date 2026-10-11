"""
Точка входа приложения «Чудо Обувь».
Сначала показываем окно авторизации, затем — каталог.
"""

import sys
from PyQt6.QtWidgets import QApplication

from config import STYLESHEET
from ui.login_window import LoginWindow
from ui.main_window import MainWindow


# ============================================================
# Публичные функции
# ============================================================
def main():
    app = _create_app()

    user = _run_login()
    if user is None:
        sys.exit(0)

    _show_main_window(user)
    sys.exit(app.exec())


# ============================================================
# Вспомогательные
# ============================================================
def _create_app() -> QApplication:
    """Создаёт QApplication и применяет общий стиль."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(STYLESHEET)
    return app


def _run_login():
    """
    Показывает окно авторизации.
    Возвращает dict пользователя или None, если окно закрыто.
    """
    login = LoginWindow()
    if login.exec() != login.DialogCode.Accepted:
        return None
    return login.get_user()


def _show_main_window(user: dict):
    """Открывает главное окно (каталог)."""
    window = MainWindow(user=user)
    window.show()
    # Сохраняем ссылку, чтобы окно не удалил сборщик мусора
    _show_main_window.window = window


# ============================================================
# Точка входа
# ============================================================
if __name__ == '__main__':
    main()