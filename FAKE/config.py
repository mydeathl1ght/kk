"""
Конфигурация приложения «Чудо Обувь»:
– пути к папкам проекта
– параметры подключения к PostgreSQL
– палитра и общий стиль интерфейса (по Приложению 3)
"""

import os


# ============================================================
# Пути проекта
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
RESOURCES_DIR = os.path.join(BASE_DIR, 'resources')
PRODUCTS_IMG_DIR = os.path.join(RESOURCES_DIR, 'products')


# ============================================================
# Параметры подключения к БД
# ============================================================
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'chudo_obuv',
    'user': 'postgres',
    'password': '12345678',   # ← замени на свой
}


# ============================================================
# Палитра (Приложение 3)
# ============================================================
COLOR_BG_MAIN = '#FFFFFF'         # основной фон
COLOR_BG_SECONDARY = '#D2F6E7'    # дополнительный фон
COLOR_ACCENT = '#70B2AF'          # акцент
COLOR_LOW_STOCK = '#ff8080'       # подсветка низкого остатка
COLOR_HOVER = '#5a9a97'           # при наведении на кнопку
COLOR_PRESSED = '#4A8582'         # при нажатии
COLOR_DISABLED = '#cccccc'        # неактивная кнопка
COLOR_DISABLED_TEXT = '#666'
COLOR_BORDER = '#a0d0c0'          # рамка полей ввода
COLOR_GRIDLINE = '#dddddd'
COLOR_TEXT = '#333'

FONT_FAMILY = 'Calibri'
FONT_SIZE = 13


# ============================================================
# Общий стиль (для setStyleSheet)
# ============================================================
STYLESHEET = f"""
QWidget {{
    background-color: {COLOR_BG_MAIN};
    font-family: '{FONT_FAMILY}';
    font-size: {FONT_SIZE}px;
    color: {COLOR_TEXT};
}}

QMainWindow, QDialog {{
    background-color: {COLOR_BG_MAIN};
}}

/* ---------- Кнопки ---------- */
QPushButton {{
    background-color: {COLOR_ACCENT};
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 8px;
    font-weight: bold;
    font-size: 13px;
    min-height: 20px;
}}
QPushButton:hover {{ background-color: {COLOR_HOVER}; }}
QPushButton:pressed {{ background-color: {COLOR_PRESSED}; }}
QPushButton:disabled {{
    background-color: {COLOR_DISABLED};
    color: {COLOR_DISABLED_TEXT};
}}

/* ---------- Поля ввода ---------- */
QLineEdit, QComboBox, QSpinBox, QTextEdit, QDateEdit {{
    background-color: {COLOR_BG_SECONDARY};
    border: 2px solid transparent;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    min-height: 20px;
    selection-background-color: {COLOR_ACCENT};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus, QDateEdit:focus {{
    border: 2px solid {COLOR_ACCENT};
    background-color: #EAFCF4;
}}

/* ---------- Выпадающие списки ---------- */
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: white;
    border: 1px solid {COLOR_ACCENT};
    border-radius: 6px;
    selection-background-color: {COLOR_BG_SECONDARY};
    selection-color: {COLOR_TEXT};
    padding: 4px;
}}

/* ---------- Таблицы ---------- */
QTableWidget {{
    background-color: white;
    gridline-color: {COLOR_GRIDLINE};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    alternate-background-color: {COLOR_BG_SECONDARY};
    selection-background-color: {COLOR_ACCENT};
    selection-color: white;
}}
QHeaderView::section {{
    background-color: {COLOR_ACCENT};
    color: white;
    padding: 10px 8px;
    border: none;
    font-weight: bold;
    font-size: 13px;
}}

/* ---------- Метки ---------- */
QLabel {{
    color: {COLOR_TEXT};
    background-color: transparent;
}}

/* ---------- Скроллбары ---------- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {COLOR_BORDER};
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLOR_ACCENT};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0;
}}
"""