"""
Окно авторизации по логину.
Пароль не используется — только логин из списка пользователей.
"""

import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton,
)
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt

from config import RESOURCES_DIR, STYLESHEET
from db import fetch_one
from utils.messages import show_error


# ---------- Константы ----------
WINDOW_TITLE = 'Чудо Обувь — Вход'
TITLE_TEXT = 'Вход в систему'
TITLE_STYLE = "font-size: 24px; font-weight: bold; color: #70B2AF;"

STYLE_SECONDARY = """
    QPushButton {
        background-color: #D2F6E7;
        color: #333;
        border: 2px solid #70B2AF;
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: bold;
    }
    QPushButton:hover { background-color: #BBEBD7; }
"""

SQL_FIND_USER = """
    SELECT u.id, u.last_name, u.first_name, u.middle_name,
           u.login, r.name AS role_name
    FROM users u
    JOIN roles r ON r.id = u.role_id
    WHERE u.login = %s
"""


class LoginWindow(QDialog):
    """Окно входа. Возвращает user_data при успехе."""

    def __init__(self):
        super().__init__()
        self.user = None
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(480, 520)
        self.setStyleSheet(STYLESHEET)
        self._set_icon()
        self._build_ui()

    # ============================================================
    # Построение интерфейса
    # ============================================================
    def _set_icon(self):
        """Устанавливает иконку приложения, если файл есть."""
        icon_path = os.path.join(RESOURCES_DIR, 'icon.png')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(50, 40, 50, 40)
        root.setSpacing(15)

        self._add_logo(root)

        root.addSpacing(10)
        root.addWidget(self._make_title())
        root.addSpacing(20)

        root.addWidget(self._make_login_label())
        root.addWidget(self._make_login_input())

        root.addSpacing(25)
        root.addLayout(self._make_buttons())
        root.addStretch()

    def _add_logo(self, parent_layout):
        logo_path = os.path.join(RESOURCES_DIR, 'logo.png')
        if not os.path.exists(logo_path):
            return
        logo = QLabel()
        logo.setPixmap(QPixmap(logo_path).scaledToHeight(
            150, Qt.TransformationMode.SmoothTransformation
        ))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        parent_layout.addWidget(logo)

    def _make_title(self) -> QLabel:
        label = QLabel(TITLE_TEXT)
        label.setStyleSheet(TITLE_STYLE)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    def _make_login_label(self) -> QLabel:
        return QLabel('Логин:')

    def _make_login_input(self) -> QLineEdit:
        field = QLineEdit()
        field.setPlaceholderText('Введите логин')
        field.returnPressed.connect(self._try_login)
        self.login_input = field
        return field

    def _make_buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(15)

        login_btn = QPushButton('Войти')
        login_btn.setMinimumHeight(45)
        login_btn.clicked.connect(self._try_login)
        row.addWidget(login_btn)

        guest_btn = QPushButton('Вход для гостя')
        guest_btn.setMinimumHeight(45)
        guest_btn.setStyleSheet(STYLE_SECONDARY)
        guest_btn.clicked.connect(self._guest_login)
        row.addWidget(guest_btn)

        return row

    # ============================================================
    # Авторизация
    # ============================================================
    def _try_login(self):
        login = self.login_input.text().strip()
        if not login:
            show_error(self, 'Введите логин')
            return

        row = fetch_one(SQL_FIND_USER, (login,))
        if not row:
            show_error(self, f'Пользователь с логином «{login}» не найден')
            return

        self.user = self._build_user_dict(row)
        self.accept()

    def _build_user_dict(self, row: dict) -> dict:
        """Собирает словарь пользователя из строки БД."""
        return {
            'id': row['id'],
            'login': row['login'],
            'role_name': row['role_name'],
            'full_name': ' '.join(filter(None, [
                row['last_name'],
                row['first_name'],
                row['middle_name'],
            ])),
        }

    def _guest_login(self):
        """Вход без авторизации."""
        self.user = {
            'id': None,
            'login': None,
            'role_name': 'Неавторизованный',
            'full_name': 'Гость',
        }
        self.accept()

    # ============================================================
    # Публичный API
    # ============================================================
    def get_user(self):
        return self.user